# Speech Recognition Skill for Nanobot

This skill enables nanobot to process audio messages by transcribing speech to text and responding accordingly.

## Features

- **Audio Transcription**: Convert speech in audio files to text
- **Multi-format Support**: WAV, MP3, M4A, OGG, FLAC formats
- **Multi-language**: Support for many languages via Google Web Speech API
- **Easy Integration**: Simple API for use in nanobot agents
- **Error Handling**: Robust error handling for various failure scenarios

## Installation

### 1. Install Python Dependencies

```bash
pip install SpeechRecognition pydub
```

### 2. Install FFmpeg (Required for non-WAV formats)

**Windows:**
- Download from: https://ffmpeg.org/download.html
- Add to PATH or place ffmpeg.exe in working directory

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg
```

### 3. Quick Install Script

Run the installation script:
```bash
python scripts/install_deps.py
```

## Usage

### Basic Transcription

```python
from scripts.transcribe import transcribe_audio

# Transcribe audio file
text = transcribe_audio("audio.wav", language="en-US")
print(f"Transcribed: {text}")
```

### Command Line Interface

```bash
# Basic transcription
python scripts/transcribe.py audio.wav

# Chinese transcription
python scripts/transcribe.py audio.mp3 -l zh-CN

# JSON output
python scripts/transcribe.py audio.m4a -j -o result.json

# List supported languages
python scripts/transcribe.py --list-languages
```

### Integration with Nanobot

In your nanobot agent, add audio message handling:

```python
def handle_message(message):
    if has_audio_attachment(message):
        audio_file = save_audio_attachment(message)
        transcribed_text = transcribe_audio(audio_file)
        
        if "error" not in transcribed_text.lower():
            # Process transcribed text as user input
            response = generate_response(transcribed_text)
            send_response(response)
        else:
            send_response(f"Could not transcribe audio: {transcribed_text}")
```

## Supported Languages

Common language codes:
- `en-US`: English (US)
- `en-GB`: English (UK)
- `zh-CN`: Chinese (Simplified)
- `zh-TW`: Chinese (Traditional)
- `ja-JP`: Japanese
- `ko-KR`: Korean
- `fr-FR`: French
- `de-DE`: German
- `es-ES`: Spanish
- `ru-RU`: Russian

See full list with: `python scripts/transcribe.py --list-languages`

## File Structure

```
speech-recognition/
├── SKILL.md              # Skill documentation
├── scripts/
│   ├── transcribe.py     # Main transcription module
│   ├── install_deps.py   # Dependency installer
│   ├── example_usage.py  # Usage examples
│   └── create_test_audio.py # Test file creator
└── README.md            # This file
```

## Testing

1. Create test audio files:
   ```bash
   python scripts/create_test_audio.py
   ```

2. Test transcription:
   ```bash
   python scripts/transcribe.py test_audio/silent_test.wav
   ```

3. Test with real speech:
   - Record a WAV file with your voice
   - Test with: `python scripts/transcribe.py your_recording.wav`

## Limitations

1. **Internet Required**: Uses Google Web Speech API (requires internet)
2. **Audio Quality**: Works best with clear speech, minimal background noise
3. **File Size**: Large files may take time to process
4. **Privacy**: Audio is sent to Google's servers for processing

## Troubleshooting

### "No module named 'speech_recognition'"
```bash
pip install SpeechRecognition
```

### "FFmpeg not found"
Install FFmpeg and ensure it's in PATH.

### "Could not understand audio"
- Check audio quality
- Reduce background noise
- Speak more clearly
- Try different language setting

### "Speech recognition service error"
- Check internet connection
- Google API may be temporarily unavailable
- Try again later

## Advanced Usage

### Custom Language Detection
```python
def detect_language_from_context(user_context):
    # Implement based on user preferences, location, or message history
    return 'zh-CN'  # Example: default to Chinese
```

### Batch Processing
```python
import glob

audio_files = glob.glob("audio/*.wav")
for audio_file in audio_files:
    text = transcribe_audio(audio_file)
    print(f"{audio_file}: {text}")
```

### Error Recovery
```python
def transcribe_with_fallback(audio_file, languages=['en-US', 'zh-CN']):
    for lang in languages:
        result = transcribe_audio(audio_file, language=lang)
        if "could not understand" not in result.lower():
            return result, lang
    return "Could not transcribe with any language", None
```

## License

This skill is provided as part of the nanobot project.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review SKILL.md for detailed documentation
3. Create an issue in the repository