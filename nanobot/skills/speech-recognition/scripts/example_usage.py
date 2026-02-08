#!/usr/bin/env python3
"""
Example usage of the speech recognition skill.
This shows how to integrate with the nanobot agent.
"""

import os
import sys
import tempfile

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def example_transcription():
    """Example of basic audio transcription."""
    print("=== Example 1: Basic Transcription ===\n")
    
    # Simulate receiving an audio message
    print("Agent receives: [audio] (audio file attachment)")
    print("Agent should:")
    print("1. Detect audio file")
    print("2. Transcribe using speech recognition")
    print("3. Process transcribed text")
    print("4. Respond appropriately\n")
    
    # Example code that would be in the agent
    example_code = '''
# In agent message handler:
if message_contains_audio:
    audio_file = get_audio_file(message)
    
    # Transcribe audio
    transcribed_text = transcribe_audio(audio_file, language='en-US')
    
    if "error" in transcribed_text.lower():
        response = f"Could not transcribe audio: {transcribed_text}"
    else:
        # Process the transcribed text as normal user input
        response = process_user_input(transcribed_text)
    
    send_response(response)
'''
    print("Example agent code:")
    print(example_code)

def example_multilingual():
    """Example of multilingual support."""
    print("\n=== Example 2: Multilingual Support ===\n")
    
    print("Supported languages include:")
    print("  - en-US: English (US)")
    print("  - zh-CN: Chinese (Simplified)")
    print("  - ja-JP: Japanese")
    print("  - fr-FR: French")
    print("  - de-DE: German")
    print("  - es-ES: Spanish")
    print("  - ... and many more\n")
    
    example_code = '''
# Detect language from context or user preference
def detect_language(context):
    # Could be based on:
    # 1. User's previous messages
    # 2. User profile/location
    # 3. Audio file metadata
    # 4. Explicit user instruction
    return 'zh-CN'  # Example: Chinese

# Transcribe with detected language
language = detect_language(user_context)
transcribed_text = transcribe_audio(audio_file, language=language)
'''
    print("Example language detection:")
    print(example_code)

def example_error_handling():
    """Example of error handling."""
    print("\n=== Example 3: Error Handling ===\n")
    
    print("Common error scenarios:")
    print("1. Unsupported audio format")
    print("2. Poor audio quality")
    print("3. No speech detected")
    print("4. Network issues (Google API)")
    print("5. FFmpeg not installed\n")
    
    example_code = '''
def handle_audio_message(audio_file):
    try:
        # Try to transcribe
        result = transcribe_audio(audio_file)
        
        if "could not understand" in result.lower():
            return "抱歉，我听不清楚这段音频。请尝试说话更清晰一些，或者减少背景噪音。"
        
        elif "service error" in result.lower():
            return "语音识别服务暂时不可用。请稍后再试，或者直接发送文字消息。"
        
        elif "failed to convert" in result.lower() and "ffmpeg" in result.lower():
            return "需要FFmpeg来处理此音频格式。请安装FFmpeg或发送WAV格式的音频文件。"
        
        else:
            # Success - process the text
            return process_response(result)
            
    except Exception as e:
        return f"处理音频时出错: {str(e)}。请尝试发送文字消息。"
'''
    print("Example error handling:")
    print(example_code)

def example_integration():
    """Example of full integration with nanobot."""
    print("\n=== Example 4: Full Integration ===\n")
    
    print("Complete workflow in nanobot agent:")
    
    workflow = '''
1. User sends audio message
   → Agent detects [audio] tag or file attachment

2. Audio processing
   → Save audio file temporarily
   → Check file format and size
   → Convert to WAV if needed (requires ffmpeg)

3. Speech recognition
   → Use Google Web Speech API
   → Apply language detection/selection
   → Get transcribed text

4. Text processing
   → Use transcribed text as user input
   → Pass to normal message handler
   → Generate appropriate response

5. Response
   → Send response to user
   → Optionally include transcription for confirmation
   → Clean up temporary files
'''
    print(workflow)
    
    print("\nSuggested agent response patterns:")
    print("- '我听到你说: \"[transcribed text]\"。我的回复是...'")
    print("- '根据你的语音消息，[response]'")
    print("- '[Direct response to transcribed content]'")

def main():
    print("=== Speech Recognition Skill - Usage Examples ===\n")
    
    example_transcription()
    example_multilingual()
    example_error_handling()
    example_integration()
    
    print("\n=== Quick Start ===\n")
    print("To use this skill in nanobot:")
    print("1. Install dependencies:")
    print("   python scripts/install_deps.py")
    print("2. Test with an audio file:")
    print("   python scripts/transcribe.py test_audio.wav")
    print("3. Integrate into your agent by:")
    print("   - Importing transcribe.py")
    print("   - Adding audio detection to message handler")
    print("   - Processing transcribed text as user input")
    
    print("\nFor more details, see SKILL.md")

if __name__ == '__main__':
    main()