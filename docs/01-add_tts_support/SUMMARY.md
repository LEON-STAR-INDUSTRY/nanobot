# TTS Voice Reply Feature - Development Summary

## Date
2026-02-08

## Feature Overview
Added text-to-speech voice reply capability to the Feishu channel. When a user sends a voice message, the bot responds with both a text card and an audio reply.

## Files Changed

### New Files
- `nanobot/skills/tts/SKILL.md` - TTS skill documentation
- `nanobot/skills/tts/scripts/tts.py` - TTS script using edge-tts library
- `docs/01-add_tts_support/DESIGN.md` - Design document
- `docs/01-add_tts_support/SUMMARY.md` - This file

### Modified Files
- `nanobot/channels/feishu.py` - Added voice reply support

## Implementation Details

### 1. TTS Skill (`nanobot/skills/tts/`)
- Uses **edge-tts** (Microsoft Edge online TTS, no API key needed)
- Default voice: `zh-CN-XiaoxiaoNeural` (Chinese female)
- Output: MP3 format
- Text truncated at 500 chars to keep audio reasonable
- Standalone CLI: `python scripts/tts.py -j "text"`

### 2. Feishu Channel Changes (`nanobot/channels/feishu.py`)

#### New imports
- `CreateFileRequest`, `CreateFileRequestBody` - for uploading audio to Feishu
- `ReplyMessageRequest`, `ReplyMessageRequestBody` - for replying with audio

#### New state
- `_voice_reply_chats: dict[str, str]` - Maps `chat_id -> message_id` to track which chats need voice reply

#### New methods
- `_tts_sync(text)` - Calls TTS script, returns MP3 path
- `_upload_audio_sync(file_path)` - Uploads MP3 to Feishu via `POST /im/v1/files`, returns `file_key`
- `_reply_audio_sync(message_id, file_key)` - Replies to message with audio via `POST /im/v1/messages/{id}/reply`
- `_send_voice_reply(text, message_id)` - Async orchestrator: TTS -> upload -> reply

#### Modified methods
- `_on_message`: When audio message received and transcribed, marks chat in `_voice_reply_chats`
- `send`: After sending text card, checks `_voice_reply_chats`; if marked, triggers voice reply flow

### 3. Voice Reply Trigger Logic
Currently triggered when user sends a voice message (`msg_type == "audio"`). The flow:
1. User sends voice -> transcribe -> mark chat for voice reply
2. Agent processes transcribed text, produces text response
3. `send()` sends text card as usual
4. `send()` detects voice reply flag -> TTS -> upload -> reply with audio
5. Voice reply flag cleared for this chat

## Testing
- TTS script standalone: `python nanobot\skills\tts\scripts\tts.py -j "你好世界"` -> OK
- `feishu.py` compiles: `python -m py_compile nanobot\channels\feishu.py` -> OK
- Integration test: Send voice message in Feishu -> pending user test

## Notes
- Voice reply is non-fatal: if TTS/upload/reply fails, text card is still sent
- edge-tts requires internet (uses Microsoft Edge online service)
- No API key needed for edge-tts
- Feishu upload uses `file_type="opus"` as required by the audio message API
