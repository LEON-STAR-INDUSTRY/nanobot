#!/usr/bin/env python3
"""
Create a simple test audio file for speech recognition testing.
Note: This creates a silent audio file - real testing requires actual speech audio.
"""

import os
import sys
import wave
import struct
import math

def create_silent_wav(filename, duration=3, sample_rate=16000):
    """
    Create a silent WAV file for testing.
    In real usage, you would use actual speech audio files.
    """
    # Create a silent audio file
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)   # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        
        # Generate silent audio (all zeros)
        silent_data = b'\x00' * (num_samples * 2)
        wav_file.writeframes(silent_data)
    
    print(f"Created silent test WAV file: {filename}")
    print(f"Duration: {duration} seconds, Sample rate: {sample_rate} Hz")
    print("\nNote: This is a silent file. For actual testing, use real speech audio.")
    print("You can record your own audio or use sample files from:")
    print("  - https://www.voiptroubleshooter.com/open_speech/american.html")
    print("  - Or record your own with: 'arecord test.wav' (Linux) or Audacity")

def create_tone_wav(filename, duration=3, frequency=440, sample_rate=16000):
    """
    Create a tone WAV file (not speech, but useful for testing).
    """
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)   # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        
        # Generate a sine wave tone
        frames = []
        for i in range(num_samples):
            # Calculate sample value
            sample = int(32767.0 * math.sin(2 * math.pi * frequency * i / sample_rate))
            # Pack as little-endian signed short
            frames.append(struct.pack('<h', sample))
        
        wav_file.writeframes(b''.join(frames))
    
    print(f"Created tone test WAV file: {filename}")
    print(f"Duration: {duration} seconds, Frequency: {frequency} Hz")

def main():
    print("=== Test Audio File Creator ===\n")
    print("This script creates test audio files for speech recognition testing.")
    print("Note: These are not actual speech files - they're for basic testing only.\n")
    
    # Create test directory
    test_dir = "test_audio"
    os.makedirs(test_dir, exist_ok=True)
    
    # Create silent audio file
    silent_file = os.path.join(test_dir, "silent_test.wav")
    create_silent_wav(silent_file)
    
    # Create tone audio file
    tone_file = os.path.join(test_dir, "tone_test.wav")
    create_tone_wav(tone_file)
    
    print(f"\nTest files created in: {test_dir}/")
    print("\nTo test with real speech:")
    print("1. Record your own audio:")
    print("   - Windows: Use Voice Recorder app")
    print("   - macOS: Use QuickTime Player")
    print("   - Linux: Use 'arecord test.wav'")
    print("\n2. Save as WAV format (16kHz, mono recommended)")
    print("\n3. Test with:")
    print(f"   python transcribe.py {test_dir}/your_audio.wav")
    
    print("\nExample test commands:")
    print(f"  python transcribe.py {silent_file}")
    print(f"  python transcribe.py {tone_file} -j")
    print(f"  python transcribe.py {silent_file} -l zh-CN")

if __name__ == '__main__':
    main()