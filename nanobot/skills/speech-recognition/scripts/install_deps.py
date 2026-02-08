#!/usr/bin/env python3
"""
Install dependencies for speech recognition skill.
"""

import subprocess
import sys
import os

def install_packages():
    """Install required Python packages."""
    packages = [
        'SpeechRecognition',
        'pydub',
    ]
    
    print("Installing required Python packages...")
    for package in packages:
        print(f"Installing {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")
            return False
    
    return True

def check_ffmpeg():
    """Check if ffmpeg is available."""
    print("\nChecking for ffmpeg...")
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✓ ffmpeg is available")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ ffmpeg not found or not in PATH")
        print("\nFFmpeg is required for processing non-WAV audio formats.")
        print("Please install ffmpeg:")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        print("  macOS: brew install ffmpeg")
        print("  Linux: sudo apt-get install ffmpeg")
        print("\nAfter installation, make sure ffmpeg is in your PATH.")
        return False

def test_imports():
    """Test if required modules can be imported."""
    print("\nTesting imports...")
    try:
        import speech_recognition as sr
        from pydub import AudioSegment
        print("✓ All Python modules imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def main():
    print("=== Speech Recognition Skill Dependency Installer ===\n")
    
    # Install Python packages
    if not install_packages():
        print("\nFailed to install Python packages.")
        return 1
    
    # Test imports
    if not test_imports():
        print("\nImport test failed.")
        return 1
    
    # Check for ffmpeg
    check_ffmpeg()
    
    print("\n=== Installation Complete ===")
    print("\nTo test the installation, run:")
    print("  python scripts/transcribe.py --help")
    print("\nExample usage:")
    print("  python scripts/transcribe.py audio.mp3")
    print("  python scripts/transcribe.py audio.wav -l zh-CN")
    print("  python scripts/transcribe.py audio.m4a -j -o output.json")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())