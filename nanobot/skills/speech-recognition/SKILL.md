---
name: speech-recognition
description: Recognize speech from audio files and respond based on content. Use when users send audio messages that need to be transcribed and processed. Supports common audio formats like WAV, MP3, M4A, and OGG.
---

# Speech Recognition Skill

This skill enables the agent to process audio files, transcribe speech to text, and respond accordingly. It's designed to handle user audio messages across various formats.

## Overview

The speech recognition skill allows the agent to:
1. Receive audio files from users
2. Transcribe speech content to text
3. Process the transcribed text as regular user input
4. Provide appropriate responses

## Prerequisites

To use this skill effectively, the following dependencies should be installed:

### Required Python Packages
```bash
pip install speechrecognition pydub
```

### Additional System Dependencies (Windows)
- FFmpeg: Required for audio format conversion
- Download from: https://ffmpeg.org/download.html
- Add to PATH or place in working directory

## How It Works

### Basic Workflow
1. **Audio Reception**: User sends an audio file (common formats: .wav, .mp3, .m4a, .ogg)
2. **Format Conversion**: Convert to WAV format if necessary using pydub
3. **Speech Recognition**: Use SpeechRecognition library with Google Web Speech API
4. **Text Processing**: Process transcribed text as regular user input
5. **Response**: Generate appropriate response based on content

### Supported Audio Formats
- WAV (preferred, no conversion needed)
- MP3 (requires ffmpeg)
- M4A/AAC (requires ffmpeg)
- OGG (requires ffmpeg)
- FLAC (requires ffmpeg)

## Usage Examples

### Example 1: Basic Transcription
User sends: `[audio]` (audio file attachment)
Agent: Transcribes audio and responds to the spoken content

### Example 2: Audio Processing
User: "Can you listen to this audio and tell me what it says?"
Agent: Processes the audio, transcribes it, and provides the text

### Example 3: Multi-language Support
User sends audio in different languages
Agent: Can specify language for better recognition accuracy

## Implementation Details

### Core Functions

```python
import speech_recognition as sr
from pydub import AudioSegment
import os
import tempfile

def transcribe_audio(audio_path, language='en-US'):
    """
    Transcribe audio file to text.
    
    Args:
        audio_path: Path to audio file
        language: Language code (default: 'en-US')
    
    Returns:
        str: Transcribed text
    """
    recognizer = sr.Recognizer()
    
    # Convert to WAV if needed
    if not audio_path.lower().endswith('.wav'):
        audio = AudioSegment.from_file(audio_path)
        wav_path = tempfile.mktemp(suffix='.wav')
        audio.export(wav_path, format='wav')
        audio_path = wav_path
    
    # Load audio file
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
        
        try:
            # Use Google Web Speech API
            text = recognizer.recognize_google(audio_data, language=language)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError as e:
            return f"Speech recognition service error: {e}"
        finally:
            # Clean up temporary WAV file if created
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
```

### Language Support

The skill supports multiple languages through Google Web Speech API:
- English (US): 'en-US'
- English (UK): 'en-GB'
- Chinese (Simplified): 'zh-CN'
- Chinese (Traditional): 'zh-TW'
- Japanese: 'ja-JP'
- Korean: 'ko-KR'
- French: 'fr-FR'
- German: 'de-DE'
- Spanish: 'es-ES'

## Integration with Agent

### Audio Detection
When the agent receives a message containing `[audio]` or detects audio file attachments, it should:
1. Check if the speech recognition skill is available
2. Process the audio file if present
3. Use transcribed text as user input

### Error Handling
- **No audio file**: Prompt user to send an audio file
- **Unsupported format**: Inform user and suggest conversion
- **Poor audio quality**: Request clearer audio
- **API limitations**: Fall back to alternative methods if available

## Best Practices

1. **Audio Quality**: Encourage users to send clear audio for better transcription
2. **File Size**: Handle large files by converting to appropriate formats
3. **Privacy**: Inform users that audio is processed through external services
4. **Fallbacks**: Provide manual text input option if speech recognition fails

## Troubleshooting

### Common Issues

1. **"No module named 'speech_recognition'"**
   - Install: `pip install SpeechRecognition`

2. **FFmpeg not found**
   - Download FFmpeg and add to PATH
   - Or place ffmpeg.exe in working directory

3. **"Could not understand audio"**
   - Check audio quality and background noise
   - Try different language settings
   - Ask user to speak more clearly

4. **Large file processing**
   - Consider splitting long audio files
   - Use compression for better performance

## Advanced Features

### Custom Recognition Engines
The skill can be extended to support:
- Offline recognition (CMU Sphinx)
- Alternative APIs (Microsoft Azure, IBM Watson)
- Real-time streaming recognition

### Audio Analysis
Potential extensions:
- Speaker identification
- Emotion detection from voice
- Background noise analysis
- Audio quality assessment

## References

### External Resources
- [SpeechRecognition Library Documentation](https://github.com/Uberi/speech_recognition)
- [pydub Documentation](http://pydub.com/)
- [FFmpeg Official Website](https://ffmpeg.org/)
- [Google Web Speech API](https://cloud.google.com/speech-to-text)

### Related Skills
- `summarize`: Can be used to summarize transcribed text
- `cron`: Can schedule audio processing tasks
- Other skills can use transcribed text as input

---

**Note**: This skill requires internet connection for Google Web Speech API. For offline usage, consider implementing CMU Sphinx as an alternative.