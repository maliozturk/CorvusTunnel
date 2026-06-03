"""
CorvusTunnel TTS — Text-to-Speech using edge-tts.

Converts agent questions/messages to audio files for Telegram voice messages.
Supports 100+ languages including Turkish and English.

Usage:
    from integrations.tts import text_to_audio
    audio_path = await text_to_audio("What should I do with this file?", lang="en")
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger("corvustunnel.tts")

# Default voices per language (Microsoft Neural TTS)
DEFAULT_VOICES = {
    "en": "en-US-AriaNeural",
    "tr": "tr-TR-AhmetNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "es": "es-ES-AlvaroNeural",
    "pt": "pt-BR-AntonioNeural",
    "ja": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
    "zh": "zh-CN-YunxiNeural",
    "ru": "ru-RU-DmitryNeural",
    "ar": "ar-SA-HamedNeural",
    "it": "it-IT-DiegoNeural",
    "nl": "nl-NL-MaartenNeural",
    "pl": "pl-PL-MarekNeural",
    "hi": "hi-IN-MadhurNeural",
}


def _get_tts_dir() -> Path:
    """Return the directory for temporary TTS audio files."""
    tts_dir = Path.home() / ".corvustunnel" / "tts_cache"
    tts_dir.mkdir(parents=True, exist_ok=True)
    return tts_dir


async def text_to_audio(
    text: str,
    lang: str = "en",
    voice: str | None = None,
    output_path: str | None = None,
) -> str:
    """Convert text to an audio file using edge-tts.

    Args:
        text: The text to convert to speech.
        lang: Language code (e.g., "en", "tr"). Used to select default voice.
        voice: Override voice name (e.g., "en-US-AriaNeural").
        output_path: Output file path. If None, creates a temp file.

    Returns:
        Path to the generated audio file (.mp3).

    Raises:
        ImportError: If edge-tts is not installed.
        RuntimeError: If TTS conversion fails.
    """
    try:
        import edge_tts
    except ImportError:
        raise ImportError(
            "edge-tts is not installed. Install with: "
            "pip install corvustunnel[voice]"
        )

    # Select voice
    selected_voice = voice or DEFAULT_VOICES.get(lang, DEFAULT_VOICES["en"])

    # Output path
    if output_path is None:
        tts_dir = _get_tts_dir()
        output_path = str(tts_dir / f"tts_{os.getpid()}_{id(text) & 0xFFFF}.mp3")

    try:
        communicate = edge_tts.Communicate(text, selected_voice)
        await communicate.save(output_path)
        logger.debug("TTS generated: %s (%d chars, voice=%s)", output_path, len(text), selected_voice)
        return output_path
    except Exception as e:
        logger.error("TTS failed: %s", e)
        raise RuntimeError(f"TTS conversion failed: {e}") from e


async def list_voices(lang: str | None = None) -> list[dict]:
    """List available TTS voices, optionally filtered by language.

    Returns:
        List of voice dicts with Name, ShortName, Gender, Locale fields.
    """
    try:
        import edge_tts
    except ImportError:
        raise ImportError("edge-tts not installed")

    voices = await edge_tts.list_voices()

    if lang:
        voices = [v for v in voices if v.get("Locale", "").startswith(lang)]

    return voices


def text_to_audio_sync(
    text: str,
    lang: str = "en",
    voice: str | None = None,
    output_path: str | None = None,
) -> str:
    """Synchronous wrapper for text_to_audio."""
    return asyncio.run(text_to_audio(text, lang, voice, output_path))
