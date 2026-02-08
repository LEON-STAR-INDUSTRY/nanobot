#!/usr/bin/env python3
"""
Text-to-Speech utility for nanobot.
Converts text to speech audio files using edge-tts (Microsoft Edge TTS).
"""

import argparse
import asyncio
import json
import os
import re
import sys
import tempfile

try:
    import edge_tts
except ImportError:
    print("Error: edge-tts not installed. Install with: pip install edge-tts")
    sys.exit(1)


# Default voice for Chinese
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

# Max recommended text length for TTS (to keep audio reasonable)
MAX_TEXT_LENGTH = 500

# Regex pattern for Unicode emoji (ranges chosen to avoid CJK U+4E00-U+9FFF)
_EMOJI_RE = re.compile(
    "["
    "\U0000231A-\U0000231B"  # watch/hourglass
    "\U000023CF-\U000023F3"  # misc technical
    "\U00002600-\U000027B0"  # misc symbols + dingbats (safe: below CJK)
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "]+",
    flags=re.UNICODE,
)


def clean_text_for_tts(text: str) -> str:
    """
    Clean markdown-formatted text for TTS consumption.
    
    Strips markdown syntax, emoji, code blocks, tables, HTML tags, etc.
    so that TTS reads only the natural language content.
    """
    if not text:
        return text
    
    # Remove fenced code blocks (```...```)
    text = re.sub(r"```[\s\S]*?```", "", text)
    
    # Remove inline code (`code`) -> keep inner text
    text = re.sub(r"`([^`]*)`", r"\1", text)
    
    # Remove images ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    
    # Convert links [text](url) -> text
    text = re.sub(r"\[([^\]]*?)\]\([^)]*\)", r"\1", text)
    
    # Remove markdown table rows (lines with | delimiters)
    text = re.sub(r"^\s*\|.*\|\s*$", "", text, flags=re.MULTILINE)
    # Remove table separator lines (|---|---|)
    text = re.sub(r"^\s*\|[-:\s|]+\|\s*$", "", text, flags=re.MULTILINE)
    
    # Remove horizontal rules (---, ***, ___)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    
    # Remove markdown headers (# ## ### etc.) -> keep text
    text = re.sub(r"^\s*#{1,6}\s+", "", text, flags=re.MULTILINE)
    
    # Remove bold/italic markers: ***text***, **text**, *text*, ___text___, __text__, _text_
    # Order matters: longest markers first
    text = re.sub(r"\*{3}(.+?)\*{3}", r"\1", text)
    text = re.sub(r"\*{2}(.+?)\*{2}", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"_{3}(.+?)_{3}", r"\1", text)
    text = re.sub(r"_{2}(.+?)_{2}", r"\1", text)
    # Single underscore: only match word-boundary to avoid breaking compound_words
    text = re.sub(r"(?<=\s)_(.+?)_(?=\s|$)", r"\1", text)
    
    # Remove strikethrough ~~text~~ -> keep text
    text = re.sub(r"~~(.+?)~~", r"\1", text)
    
    # Remove blockquote markers (> text) -> keep text
    text = re.sub(r"^\s*>+\s?", "", text, flags=re.MULTILINE)
    
    # Remove unordered list markers (- item, * item, + item) -> keep text
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    
    # Remove ordered list markers (1. item, 2. item) -> keep text
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    
    # Remove emoji
    text = _EMOJI_RE.sub("", text)
    
    # Remove leftover markdown-style reference links [id]: url
    text = re.sub(r"^\s*\[[^\]]+\]:\s+.*$", "", text, flags=re.MULTILINE)
    
    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)
    
    return text.strip()


async def text_to_speech(text: str, output_path: str, voice: str = DEFAULT_VOICE) -> dict:
    """
    Convert text to speech and save as MP3.
    
    Args:
        text: Text to convert to speech.
        output_path: Path to save the MP3 file.
        voice: Voice name (default: zh-CN-XiaoxiaoNeural).
    
    Returns:
        dict with success status and metadata.
    """
    try:
        if not text or not text.strip():
            return {"success": False, "error": "Empty text"}
        
        # Clean markdown/emoji before TTS
        text = clean_text_for_tts(text)
        
        if not text or not text.strip():
            return {"success": False, "error": "Empty text after cleaning"}
        
        # Truncate if too long
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH] + "..."
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        
        # Get file size
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            return {"success": False, "error": "Generated audio file is empty"}
        
        return {
            "success": True,
            "file": output_path,
            "size": file_size,
            "voice": voice,
            "text_length": len(text),
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


async def list_voices(language: str | None = None) -> list[dict]:
    """List available voices, optionally filtered by language."""
    voices = await edge_tts.list_voices()
    if language:
        voices = [v for v in voices if v["Locale"].startswith(language)]
    return [{"name": v["ShortName"], "locale": v["Locale"], "gender": v["Gender"]} for v in voices]


def main():
    parser = argparse.ArgumentParser(description="Convert text to speech using edge-tts")
    parser.add_argument("text", nargs="?", help="Text to convert to speech")
    parser.add_argument("-v", "--voice", default=DEFAULT_VOICE, help=f"Voice name (default: {DEFAULT_VOICE})")
    parser.add_argument("-o", "--output", help="Output file path (default: temp file)")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--list-voices", metavar="LANG", nargs="?", const="", help="List available voices (optionally filter by language)")
    
    args = parser.parse_args()
    
    if args.list_voices is not None:
        lang = args.list_voices if args.list_voices else None
        voices = asyncio.run(list_voices(lang))
        if args.json:
            print(json.dumps(voices, indent=2, ensure_ascii=False))
        else:
            for v in voices:
                print(f"  {v['name']}: {v['locale']} ({v['gender']})")
        return
    
    if not args.text:
        parser.error("text is required (unless using --list-voices)")
    
    output_path = args.output or tempfile.mktemp(suffix=".mp3")
    
    result = asyncio.run(text_to_speech(args.text, output_path, args.voice))
    
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("success"):
            print(f"Audio saved to: {result['file']}")
        else:
            print(f"Error: {result.get('error')}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
