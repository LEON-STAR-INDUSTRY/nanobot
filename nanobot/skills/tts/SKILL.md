---
name: tts
description: Convert text to speech audio files using edge-tts (Microsoft Edge TTS). Supports multiple languages and voices. Use when users need audio responses.
---

# Text-to-Speech (TTS) Skill

This skill converts text to speech audio files using the edge-tts library (Microsoft Edge's online TTS service).

## Prerequisites

```bash
pip install edge-tts
```

## Usage

### CLI Script

```bash
# Basic usage (Chinese, default voice)
python scripts/tts.py "你好世界" -o output.mp3

# Specify voice
python scripts/tts.py "Hello world" -v en-US-AriaNeural -o output.mp3

# JSON output with metadata
python scripts/tts.py -j "你好世界"

# List available voices for a language
python scripts/tts.py --list-voices zh-CN
```

### Supported Voices (Common)

- `zh-CN-XiaoxiaoNeural` - Chinese female (default)
- `zh-CN-YunxiNeural` - Chinese male
- `en-US-AriaNeural` - English female
- `en-US-GuyNeural` - English male
- `ja-JP-NanamiNeural` - Japanese female

## Notes

- Requires internet connection (uses Microsoft Edge online service)
- No API key required
- Output format: MP3
- For long text (>300 characters), consider summarizing before TTS
