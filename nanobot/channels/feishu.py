"""Feishu/Lark channel implementation using lark-oapi SDK with WebSocket long connection."""

import asyncio
import json
import re
import subprocess
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import FeishuConfig

try:
    import lark_oapi as lark
    from lark_oapi.api.im.v1 import (
        CreateFileRequest,
        CreateFileRequestBody,
        CreateMessageRequest,
        CreateMessageRequestBody,
        CreateMessageReactionRequest,
        CreateMessageReactionRequestBody,
        Emoji,
        GetMessageResourceRequest,
        P2ImMessageReceiveV1,
        ReplyMessageRequest,
        ReplyMessageRequestBody,
    )
    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False
    lark = None
    Emoji = None

# Message type display mapping
MSG_TYPE_MAP = {
    "image": "[image]",
    "audio": "[audio]",
    "file": "[file]",
    "sticker": "[sticker]",
}


class FeishuChannel(BaseChannel):
    """
    Feishu/Lark channel using WebSocket long connection.
    
    Uses WebSocket to receive events - no public IP or webhook required.
    
    Requires:
    - App ID and App Secret from Feishu Open Platform
    - Bot capability enabled
    - Event subscription enabled (im.message.receive_v1)
    """
    
    name = "feishu"
    
    def __init__(self, config: FeishuConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: FeishuConfig = config
        self._client: Any = None
        self._ws_client: Any = None
        self._ws_thread: threading.Thread | None = None
        self._processed_message_ids: OrderedDict[str, None] = OrderedDict()  # Ordered dedup cache
        self._loop: asyncio.AbstractEventLoop | None = None
        self._voice_reply_chats: dict[str, str] = {}  # chat_id -> message_id for voice reply
    
    async def start(self) -> None:
        """Start the Feishu bot with WebSocket long connection."""
        if not FEISHU_AVAILABLE:
            logger.error("Feishu SDK not installed. Run: pip install lark-oapi")
            return
        
        if not self.config.app_id or not self.config.app_secret:
            logger.error("Feishu app_id and app_secret not configured")
            return
        
        self._running = True
        self._loop = asyncio.get_running_loop()
        
        # Create Lark client for sending messages
        self._client = lark.Client.builder() \
            .app_id(self.config.app_id) \
            .app_secret(self.config.app_secret) \
            .log_level(lark.LogLevel.INFO) \
            .build()
        
        # Create event handler (only register message receive, ignore other events)
        event_handler = lark.EventDispatcherHandler.builder(
            self.config.encrypt_key or "",
            self.config.verification_token or "",
        ).register_p2_im_message_receive_v1(
            self._on_message_sync
        ).build()
        
        # Create WebSocket client for long connection
        self._ws_client = lark.ws.Client(
            self.config.app_id,
            self.config.app_secret,
            event_handler=event_handler,
            log_level=lark.LogLevel.INFO
        )
        
        # Start WebSocket client in a separate thread
        def run_ws():
            try:
                self._ws_client.start()
            except Exception as e:
                logger.error(f"Feishu WebSocket error: {e}")
        
        self._ws_thread = threading.Thread(target=run_ws, daemon=True)
        self._ws_thread.start()
        
        logger.info("Feishu bot started with WebSocket long connection")
        logger.info("No public IP required - using WebSocket to receive events")
        
        # Keep running until stopped
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self) -> None:
        """Stop the Feishu bot."""
        self._running = False
        if self._ws_client:
            try:
                self._ws_client.stop()
            except Exception as e:
                logger.warning(f"Error stopping WebSocket client: {e}")
        logger.info("Feishu bot stopped")
    
    def _add_reaction_sync(self, message_id: str, emoji_type: str) -> None:
        """Sync helper for adding reaction (runs in thread pool)."""
        try:
            request = CreateMessageReactionRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    CreateMessageReactionRequestBody.builder()
                    .reaction_type(Emoji.builder().emoji_type(emoji_type).build())
                    .build()
                ).build()
            
            response = self._client.im.v1.message_reaction.create(request)
            
            if not response.success():
                logger.warning(f"Failed to add reaction: code={response.code}, msg={response.msg}")
            else:
                logger.debug(f"Added {emoji_type} reaction to message {message_id}")
        except Exception as e:
            logger.warning(f"Error adding reaction: {e}")

    async def _add_reaction(self, message_id: str, emoji_type: str = "THUMBSUP") -> None:
        """
        Add a reaction emoji to a message (non-blocking).
        
        Common emoji types: THUMBSUP, OK, EYES, DONE, OnIt, HEART
        """
        if not self._client or not Emoji:
            return
        
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._add_reaction_sync, message_id, emoji_type)
    
    def _download_file_sync(self, file_key: str, message_id: str) -> str | None:
        """
        Download a message resource from Feishu using message_id and file_key (sync).
        
        Uses the 'get message resource' API:
        GET /open-apis/im/v1/messages/{message_id}/resources/{file_key}?type=file
        
        Returns:
            Path to the downloaded file, or None on failure.
        """
        try:
            request = GetMessageResourceRequest.builder() \
                .message_id(message_id) \
                .file_key(file_key) \
                .type("file") \
                .build()
            response = self._client.im.v1.message_resource.get(request)
            
            if not response.success():
                logger.error(
                    f"Failed to download Feishu file: code={response.code}, "
                    f"msg={response.msg}"
                )
                return None
            
            # Save to temp file
            media_dir = Path.home() / ".nanobot" / "media"
            media_dir.mkdir(parents=True, exist_ok=True)
            
            file_name = response.file_name or f"{file_key}.opus"
            file_path = media_dir / file_name
            
            with open(file_path, "wb") as f:
                f.write(response.file.read())
            
            logger.info(f"Downloaded Feishu audio file to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Error downloading Feishu file: {e}")
            return None
    
    def _transcribe_audio_sync(self, audio_path: str) -> str | None:
        """
        Transcribe audio file using the speech-recognition skill script (sync).
        
        Returns:
            Transcribed text, or None on failure.
        """
        try:
            script_path = Path(__file__).parent.parent / "skills" / "speech-recognition" / "scripts" / "transcribe.py"
            if not script_path.exists():
                logger.warning(f"Transcribe script not found: {script_path}")
                return None
            
            result = subprocess.run(
                ["python", str(script_path), "-j", audio_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                logger.error(f"Transcription failed: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            if data.get("success") and data.get("text"):
                logger.info(f"Transcribed audio: {data['text'][:50]}...")
                return data["text"]
            elif data.get("error"):
                logger.warning(f"Transcription error: {data['error']}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    async def _download_and_transcribe(self, file_key: str, message_id: str) -> str | None:
        """
        Download audio from Feishu and transcribe it (async wrapper).
        
        Returns:
            Transcribed text, or None on failure.
        """
        loop = asyncio.get_running_loop()
        
        # Download file
        audio_path = await loop.run_in_executor(
            None, self._download_file_sync, file_key, message_id
        )
        if not audio_path:
            return None
        
        # Transcribe
        text = await loop.run_in_executor(
            None, self._transcribe_audio_sync, audio_path
        )
        return text
    
    def _tts_sync(self, text: str) -> str | None:
        """
        Convert text to speech using the TTS skill script (sync).
        
        Returns:
            Path to the generated MP3 file, or None on failure.
        """
        try:
            script_path = Path(__file__).parent.parent / "skills" / "tts" / "scripts" / "tts.py"
            if not script_path.exists():
                logger.warning(f"TTS script not found: {script_path}")
                return None
            
            # Create output path
            media_dir = Path.home() / ".nanobot" / "media"
            media_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = str(media_dir / f"tts_{next(tempfile._get_candidate_names())}.mp3")
            
            result = subprocess.run(
                ["python", str(script_path), "-j", "-o", output_path, text],
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                logger.error(f"TTS failed: {result.stderr}")
                return None
            
            data = json.loads(result.stdout)
            if data.get("success") and data.get("file"):
                logger.info(f"TTS generated: {data['file']} ({data.get('size', 0)} bytes)")
                return data["file"]
            elif data.get("error"):
                logger.warning(f"TTS error: {data['error']}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error in TTS: {e}")
            return None
    
    def _upload_audio_sync(self, file_path: str) -> str | None:
        """
        Upload an audio file to Feishu and get file_key (sync).
        
        Uses: POST /open-apis/im/v1/files
        
        Returns:
            file_key string, or None on failure.
        """
        try:
            with open(file_path, "rb") as f:
                request = CreateFileRequest.builder() \
                    .request_body(
                        CreateFileRequestBody.builder()
                        .file_type("opus")
                        .file_name("voice_reply.mp3")
                        .file(f)
                        .build()
                    ).build()
                
                response = self._client.im.v1.file.create(request)
            
            if not response.success():
                logger.error(
                    f"Failed to upload audio to Feishu: code={response.code}, "
                    f"msg={response.msg}"
                )
                return None
            
            file_key = response.data.file_key
            logger.info(f"Uploaded audio to Feishu: file_key={file_key}")
            return file_key
            
        except Exception as e:
            logger.error(f"Error uploading audio to Feishu: {e}")
            return None
    
    def _reply_audio_sync(self, message_id: str, file_key: str) -> bool:
        """
        Reply to a message with an audio file (sync).
        
        Uses: POST /open-apis/im/v1/messages/{message_id}/reply
        
        Returns:
            True on success, False on failure.
        """
        try:
            content = json.dumps({"file_key": file_key})
            request = ReplyMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    ReplyMessageRequestBody.builder()
                    .msg_type("audio")
                    .content(content)
                    .build()
                ).build()
            
            response = self._client.im.v1.message.reply(request)
            
            if not response.success():
                logger.error(
                    f"Failed to reply with audio: code={response.code}, "
                    f"msg={response.msg}"
                )
                return False
            
            logger.info(f"Replied with audio to message {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error replying with audio: {e}")
            return False
    
    async def _send_voice_reply(self, text: str, message_id: str) -> None:
        """
        Generate TTS audio and send as voice reply to a Feishu message.
        
        Full flow: TTS -> upload -> reply with audio.
        """
        loop = asyncio.get_running_loop()
        
        # Step 1: TTS
        audio_path = await loop.run_in_executor(None, self._tts_sync, text)
        if not audio_path:
            logger.warning("Voice reply skipped: TTS failed")
            return
        
        # Step 2: Upload to Feishu
        file_key = await loop.run_in_executor(None, self._upload_audio_sync, audio_path)
        if not file_key:
            logger.warning("Voice reply skipped: upload failed")
            return
        
        # Step 3: Reply with audio
        await loop.run_in_executor(None, self._reply_audio_sync, message_id, file_key)
    
    # Regex to match markdown tables (header + separator + data rows)
    _TABLE_RE = re.compile(
        r"((?:^[ \t]*\|.+\|[ \t]*\n)(?:^[ \t]*\|[-:\s|]+\|[ \t]*\n)(?:^[ \t]*\|.+\|[ \t]*\n?)+)",
        re.MULTILINE,
    )

    @staticmethod
    def _parse_md_table(table_text: str) -> dict | None:
        """Parse a markdown table into a Feishu table element."""
        lines = [l.strip() for l in table_text.strip().split("\n") if l.strip()]
        if len(lines) < 3:
            return None
        split = lambda l: [c.strip() for c in l.strip("|").split("|")]
        headers = split(lines[0])
        rows = [split(l) for l in lines[2:]]
        columns = [{"tag": "column", "name": f"c{i}", "display_name": h, "width": "auto"}
                   for i, h in enumerate(headers)]
        return {
            "tag": "table",
            "page_size": len(rows) + 1,
            "columns": columns,
            "rows": [{f"c{i}": r[i] if i < len(r) else "" for i in range(len(headers))} for r in rows],
        }

    def _build_card_elements(self, content: str) -> list[dict]:
        """Split content into markdown + table elements for Feishu card."""
        elements, last_end = [], 0
        for m in self._TABLE_RE.finditer(content):
            before = content[last_end:m.start()].strip()
            if before:
                elements.append({"tag": "markdown", "content": before})
            elements.append(self._parse_md_table(m.group(1)) or {"tag": "markdown", "content": m.group(1)})
            last_end = m.end()
        remaining = content[last_end:].strip()
        if remaining:
            elements.append({"tag": "markdown", "content": remaining})
        return elements or [{"tag": "markdown", "content": content}]

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through Feishu."""
        if not self._client:
            logger.warning("Feishu client not initialized")
            return
        
        try:
            # Determine receive_id_type based on chat_id format
            # open_id starts with "ou_", chat_id starts with "oc_"
            if msg.chat_id.startswith("oc_"):
                receive_id_type = "chat_id"
            else:
                receive_id_type = "open_id"
            
            # Build card with markdown + table support
            elements = self._build_card_elements(msg.content)
            card = {
                "config": {"wide_screen_mode": True},
                "elements": elements,
            }
            content = json.dumps(card, ensure_ascii=False)
            
            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(msg.chat_id)
                    .msg_type("interactive")
                    .content(content)
                    .build()
                ).build()
            
            response = self._client.im.v1.message.create(request)
            
            if not response.success():
                logger.error(
                    f"Failed to send Feishu message: code={response.code}, "
                    f"msg={response.msg}, log_id={response.get_log_id()}"
                )
            else:
                logger.debug(f"Feishu message sent to {msg.chat_id}")
                
                # Check if voice reply is needed for this chat
                original_message_id = self._voice_reply_chats.pop(msg.chat_id, None)
                if original_message_id:
                    logger.info(f"Sending voice reply for chat {msg.chat_id}")
                    try:
                        await self._send_voice_reply(msg.content, original_message_id)
                    except Exception as ve:
                        logger.warning(f"Voice reply failed (non-fatal): {ve}")
                
        except Exception as e:
            logger.error(f"Error sending Feishu message: {e}")
    
    def _on_message_sync(self, data: "P2ImMessageReceiveV1") -> None:
        """
        Sync handler for incoming messages (called from WebSocket thread).
        Schedules async handling in the main event loop.
        """
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._on_message(data), self._loop)
    
    async def _on_message(self, data: "P2ImMessageReceiveV1") -> None:
        """Handle incoming message from Feishu."""
        try:
            event = data.event
            message = event.message
            sender = event.sender
            
            # Deduplication check
            message_id = message.message_id
            if message_id in self._processed_message_ids:
                return
            self._processed_message_ids[message_id] = None
            
            # Trim cache: keep most recent 500 when exceeds 1000
            while len(self._processed_message_ids) > 1000:
                self._processed_message_ids.popitem(last=False)
            
            # Skip bot messages
            sender_type = sender.sender_type
            if sender_type == "bot":
                return
            
            sender_id = sender.sender_id.open_id if sender.sender_id else "unknown"
            chat_id = message.chat_id
            chat_type = message.chat_type  # "p2p" or "group"
            msg_type = message.message_type
            
            # Add reaction to indicate "seen"
            await self._add_reaction(message_id, "THUMBSUP")
            
            # Parse message content
            if msg_type == "text":
                try:
                    content = json.loads(message.content).get("text", "")
                except json.JSONDecodeError:
                    content = message.content or ""
            elif msg_type == "audio":
                # Handle audio messages: download and transcribe
                try:
                    audio_content = json.loads(message.content)
                    file_key = audio_content.get("file_key")
                    duration = audio_content.get("duration", 0)
                    logger.info(f"Received audio message: file_key={file_key}, duration={duration}ms")
                    
                    if file_key:
                        transcription = await self._download_and_transcribe(file_key, message_id)
                        if transcription:
                            content = transcription
                            # Mark this chat for voice reply
                            reply_to_id = chat_id if chat_type == "group" else sender_id
                            self._voice_reply_chats[reply_to_id] = message_id
                        else:
                            content = "[audio: transcription failed]"
                    else:
                        content = "[audio: no file_key]"
                except json.JSONDecodeError:
                    content = "[audio: invalid content]"
            else:
                content = MSG_TYPE_MAP.get(msg_type, f"[{msg_type}]")
            
            if not content:
                return
            
            # Forward to message bus
            reply_to = chat_id if chat_type == "group" else sender_id
            await self._handle_message(
                sender_id=sender_id,
                chat_id=reply_to,
                content=content,
                metadata={
                    "message_id": message_id,
                    "chat_type": chat_type,
                    "msg_type": msg_type,
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing Feishu message: {e}")
