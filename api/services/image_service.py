"""
Image conversion service.

Converts various image formats to JPEG for standardized storage.
Handles HEIC/HEIF from iPhones and other non-standard formats.
"""

import io
import logging
from pathlib import Path
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# Standard formats that don't need conversion
STANDARD_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Formats that need conversion to JPEG
CONVERTIBLE_IMAGE_TYPES = {"image/heic", "image/heif", "image/bmp", "image/tiff"}

# Register HEIF opener with Pillow
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORT = True
    logger.info("HEIF/HEIC support enabled")
except ImportError:
    HEIF_SUPPORT = False
    logger.warning("pillow-heif not installed, HEIC images will not be converted")


def convert_image_to_jpeg(
    data: bytes,
    original_mime_type: str,
    original_filename: str,
) -> Tuple[bytes, str, str]:
    """
    Convert image data to JPEG format if needed.

    Args:
        data: Original image data
        original_mime_type: Original MIME type (e.g., "image/heic")
        original_filename: Original filename

    Returns:
        Tuple of (converted_data, mime_type, filename)
        If already a standard format, returns original data unchanged.
    """
    # Extract base MIME type (remove any params)
    base_mime_type = original_mime_type.split(";")[0].strip().lower()

    # If already a standard web format, return as-is
    if base_mime_type in STANDARD_IMAGE_TYPES:
        logger.debug(f"Image already in standard format: {base_mime_type}")
        return data, original_mime_type, original_filename

    logger.info(f"Converting image from {original_mime_type} to JPEG")

    try:
        # Open image with Pillow (pillow-heif handles HEIC automatically)
        img = Image.open(io.BytesIO(data))

        # Convert to RGB if necessary (HEIC can have alpha channel)
        if img.mode in ("RGBA", "LA", "P"):
            # Create white background for transparency
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Preserve EXIF orientation
        try:
            from PIL import ExifTags
            exif = img.getexif()
            if exif:
                for tag, value in exif.items():
                    if ExifTags.TAGS.get(tag) == "Orientation":
                        if value == 3:
                            img = img.rotate(180, expand=True)
                        elif value == 6:
                            img = img.rotate(270, expand=True)
                        elif value == 8:
                            img = img.rotate(90, expand=True)
                        break
        except Exception as e:
            logger.debug(f"Could not process EXIF orientation: {e}")

        # Save as JPEG
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        converted_data = output.getvalue()

        # Generate new filename
        original_stem = Path(original_filename).stem
        new_filename = f"{original_stem}.jpg"

        logger.info(
            f"Image converted successfully: {len(data)} bytes -> {len(converted_data)} bytes"
        )

        return converted_data, "image/jpeg", new_filename

    except Exception as e:
        logger.error(f"Image conversion error: {e}")
        # Return original data if conversion fails
        logger.warning("Returning original image data due to conversion failure")
        return data, original_mime_type, original_filename


def is_image_mime_type(mime_type: str) -> bool:
    """Check if MIME type is an image type."""
    if not mime_type:
        return False
    base_type = mime_type.split(";")[0].strip().lower()
    return base_type.startswith("image/")
