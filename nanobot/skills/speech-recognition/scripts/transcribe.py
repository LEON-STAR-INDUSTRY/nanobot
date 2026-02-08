#!/usr/bin/env python3
"""
Speech recognition utility for nanobot.
Transcribes audio files to text using Google Web Speech API.
"""

import argparse
import os
import sys
import tempfile
import json

# === 修复开始：配置 FFmpeg 路径 ===
# 1. 定义 FFmpeg 的 bin 目录路径 (使用 r"" 原始字符串避免转义问题)
ffmpeg_bin_dir = r"E:\runtimes\ffmpeg-8.0.1-essentials_build\bin"

# 2. 检查路径是否存在，避免路径写错导致瞎折腾
if not os.path.exists(os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")):
    print(f"Error: 找不到 FFmpeg，请检查路径是否正确: {ffmpeg_bin_dir}")
    sys.exit(1)

# 3. 核心修复：将 FFmpeg 目录临时加入到系统 PATH 环境变量中
# 这样 subprocess 调用时就能直接找到 ffmpeg 命令
os.environ["PATH"] += os.pathsep + ffmpeg_bin_dir

try:
    import speech_recognition as sr
    from pydub import AudioSegment
    
    # 4. 双重保险：显式指定 pydub 的转换器路径
    AudioSegment.converter = os.path.join(ffmpeg_bin_dir, "ffmpeg.exe")
    AudioSegment.ffprobe   = os.path.join(ffmpeg_bin_dir, "ffprobe.exe")
    
except ImportError as e:
    print(f"Error: Missing required packages. Install with: pip install SpeechRecognition pydub")
    sys.exit(1)
# === 修复结束 ===


def transcribe_audio(audio_path, language='zh-CN', output_format='text'):
    """
    Transcribe audio file to text.
    
    Args:
        audio_path: Path to audio file
        language: Language code (default: 'zh-CN')
        output_format: Output format ('text' or 'json')
    
    Returns:
        str or dict: Transcribed text or JSON with metadata
    """
    recognizer = sr.Recognizer()
    wav_path = None
    
    try:
        # Check if file exists
        if not os.path.exists(audio_path):
            return {"error": f"File not found: {audio_path}"}
        
        # Convert to WAV if needed
        file_ext = os.path.splitext(audio_path)[1].lower()
        if file_ext != '.wav':
            try:
                audio = AudioSegment.from_file(audio_path)
                wav_path = tempfile.mktemp(suffix='.wav')
                audio.export(wav_path, format='wav')
                audio_path = wav_path
            except Exception as e:
                return {"error": f"Failed to convert audio: {str(e)}. Make sure ffmpeg is installed."}
        
        # Load audio file
        with sr.AudioFile(audio_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
            
            try:
                # Use Google Web Speech API
                text = recognizer.recognize_google(audio_data, language=language)
                
                if output_format == 'json':
                    return {
                        "success": True,
                        "text": text,
                        "language": language,
                        "file": audio_path,
                        "confidence": "unknown"  # Google API doesn't provide confidence scores
                    }
                else:
                    return text
                    
            except sr.UnknownValueError:
                error_msg = "Could not understand audio. The audio may be unclear or contain no speech."
                if output_format == 'json':
                    return {"error": error_msg}
                else:
                    return error_msg
                    
            except sr.RequestError as e:
                error_msg = f"Speech recognition service error: {e}"
                if output_format == 'json':
                    return {"error": error_msg}
                else:
                    return error_msg
                    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        if output_format == 'json':
            return {"error": error_msg}
        else:
            return error_msg
            
    finally:
        # Clean up temporary WAV file if created
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass


def list_supported_languages():
    """List supported language codes."""
    languages = {
        'en-US': 'English (United States)',
        'en-GB': 'English (United Kingdom)',
        'zh-CN': 'Chinese (Simplified)',
        'zh-TW': 'Chinese (Traditional)',
        'ja-JP': 'Japanese',
        'ko-KR': 'Korean',
        'fr-FR': 'French',
        'de-DE': 'German',
        'es-ES': 'Spanish',
        'ru-RU': 'Russian',
        'ar-SA': 'Arabic',
        'hi-IN': 'Hindi',
        'pt-BR': 'Portuguese (Brazil)',
        'it-IT': 'Italian',
        'nl-NL': 'Dutch',
        'sv-SE': 'Swedish',
        'tr-TR': 'Turkish',
        'pl-PL': 'Polish',
    }
    return languages


def main():
    parser = argparse.ArgumentParser(description='Transcribe audio files to text')
    parser.add_argument('audio_file', help='Path to audio file')
    parser.add_argument('-l', '--language', default='zh-CN', 
                       help='Language code (default: zh-CN)')
    parser.add_argument('-j', '--json', action='store_true',
                       help='Output in JSON format')
    parser.add_argument('-o', '--output', help='Output file (optional)')
    parser.add_argument('--list-languages', action='store_true',
                       help='List supported language codes')
    
    args = parser.parse_args()
    
    if args.list_languages:
        languages = list_supported_languages()
        print("Supported language codes:")
        for code, name in languages.items():
            print(f"  {code}: {name}")
        return
    
    output_format = 'json' if args.json else 'text'
    
    result = transcribe_audio(args.audio_file, args.language, output_format)
    
    if args.json or isinstance(result, dict):
        output = json.dumps(result, indent=2, ensure_ascii=False)
    else:
        output = result
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Output written to: {args.output}")
    else:
        print(output)


if __name__ == '__main__':
    main()