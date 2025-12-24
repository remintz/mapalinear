"""
Audio conversion service.

Converts various audio formats to MP3 for standardized storage.
"""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

# Standard formats that don't need conversion
STANDARD_AUDIO_TYPES = {"audio/mp3", "audio/mpeg"}


async def convert_audio_to_mp3(
    data: bytes,
    original_mime_type: str,
    original_filename: str,
) -> Tuple[bytes, str, str]:
    """
    Convert audio data to MP3 format if needed.

    Args:
        data: Original audio data
        original_mime_type: Original MIME type (e.g., "audio/webm;codecs=opus")
        original_filename: Original filename

    Returns:
        Tuple of (converted_data, mime_type, filename)
        If already MP3, returns original data unchanged.
    """
    # Extract base MIME type (remove codec params like ";codecs=opus")
    base_mime_type = original_mime_type.split(";")[0].strip().lower()

    # If already MP3/MPEG, return as-is
    if base_mime_type in STANDARD_AUDIO_TYPES:
        logger.debug(f"Audio already in standard format: {base_mime_type}")
        return data, original_mime_type, original_filename

    logger.info(f"Converting audio from {original_mime_type} to MP3")

    try:
        # Create temp files for conversion
        with tempfile.NamedTemporaryFile(suffix=_get_extension(base_mime_type), delete=False) as input_file:
            input_path = Path(input_file.name)
            input_file.write(data)

        output_path = input_path.with_suffix(".mp3")

        try:
            # Run ffmpeg conversion
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i", str(input_path),
                "-vn",  # No video
                "-ar", "44100",  # Sample rate
                "-ac", "2",  # Stereo
                "-b:a", "128k",  # Bitrate
                "-f", "mp3",
                "-y",  # Overwrite
                str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"FFmpeg conversion failed: {error_msg}")
                # Return original data if conversion fails
                logger.warning("Returning original audio data due to conversion failure")
                return data, original_mime_type, original_filename

            # Read converted file
            converted_data = output_path.read_bytes()

            # Generate new filename
            original_stem = Path(original_filename).stem
            new_filename = f"{original_stem}.mp3"

            logger.info(
                f"Audio converted successfully: {len(data)} bytes -> {len(converted_data)} bytes"
            )

            return converted_data, "audio/mpeg", new_filename

        finally:
            # Cleanup temp files
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()

    except FileNotFoundError:
        logger.warning("FFmpeg not found, returning original audio")
        return data, original_mime_type, original_filename
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        return data, original_mime_type, original_filename


def _get_extension(mime_type: str) -> str:
    """Get file extension for MIME type."""
    extensions = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/aac": ".aac",
        "audio/flac": ".flac",
    }
    return extensions.get(mime_type, ".audio")


def is_audio_mime_type(mime_type: str) -> bool:
    """Check if MIME type is an audio type."""
    if not mime_type:
        return False
    base_type = mime_type.split(";")[0].strip().lower()
    return base_type.startswith("audio/")
