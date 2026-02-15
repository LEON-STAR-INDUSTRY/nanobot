# TTS Voice Reply Feature Design

## Overview
Add text-to-speech (TTS) voice reply capability to the Feishu channel. When a user sends a voice message or explicitly requests voice reply, the bot will respond with both text (card) and audio.

## Architecture

### Decision: Voice Reply Trigger
Voice reply is triggered when:
1. User sent an audio message (`msg_type == "audio"`)
2. User explicitly requests voice reply (e.g. contains keywords like "语音回复")

This state is tracked per-chat in `FeishuChannel._voice_reply_chats` (a set of chat_ids that should get voice reply on the next outbound message).

### Flow
```
User sends voice in Feishu
  -> _on_message: download + transcribe -> mark chat for voice reply
  -> Agent processes transcribed text, produces response
  -> send(): send text card as usual
  -> send(): detect voice reply needed -> TTS -> upload -> reply with audio
  -> clear voice reply flag for this chat
```

### Components

#### 1. TTS Skill (`nanobot/skills/tts/`)
- Script: `scripts/tts.py` using edge-tts library
- Voice: `zh-CN-XiaoxiaoNeural` (Chinese female, natural)
- Input: text string, output: MP3 file path
- Text length handling: if text > 300 chars, summarize before TTS to avoid edge-tts limits

#### 2. Feishu Channel Methods
- `_tts_sync(text) -> str|None`: Convert text to MP3 using TTS skill script
- `_upload_audio_sync(file_path, duration) -> str|None`: Upload MP3 to Feishu, get file_key
- `_reply_audio_sync(message_id, file_key) -> bool`: Reply to message with audio

#### 3. State Tracking
- `_voice_reply_chats: dict[str, str]`: Maps chat_id -> original message_id (for reply)
- Set in `_on_message` when audio is received
- Consumed in `send()` after sending text reply

### API Details

#### Feishu Upload File
```
POST /open-apis/im/v1/files
Body (form-data):
  file_type: "opus"  (audio type)
  file_name: "reply.opus"
  file: <binary>
Response: { file_key: "file_v2_xxx" }
```

#### Feishu Reply Message
```
POST /open-apis/im/v1/messages/{message_id}/reply
Body:
  msg_type: "audio"
  content: "{\"file_key\":\"file_v2_xxx\"}"
```

### Edge-tts Notes
- edge-tts uses Microsoft Edge's online TTS service
- No API key required, but requires internet
- Output format: MP3
- Feishu audio accepts opus format, but MP3 should work via file upload
- For long text (>300 chars), summarize first to keep audio reasonable length
