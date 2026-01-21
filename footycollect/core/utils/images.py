import logging
from io import BytesIO
from pathlib import Path

import pillow_avif  # noqa: F401 - needed to register AVIF support
from django.core.exceptions import ValidationError
from django.core.files import File
from PIL import Image

MAX_FILE_SIZE = 15 * 1024 * 1024
logger = logging.getLogger(__name__)


def _check_image_has_transparency(img: Image.Image) -> bool:
    """Check if image has transparency."""
    if img.mode in ("RGBA", "LA"):
        return True
    if img.mode == "P":
        if img.im is not None:
            try:
                palette_mode = img.im.getpalettemode()
                if "A" in palette_mode:
                    return True
            except (AttributeError, TypeError):
                pass
        if "transparency" in img.info or img.info.get("transparency") is not None:
            return True
    return False


def _convert_image_mode(img: Image.Image, img_format: str, *, has_transparency: bool) -> Image.Image:
    """Convert image to appropriate mode preserving transparency."""
    converted_img = img

    if img_format == "JPEG" and img.mode in ("RGBA", "LA", "P"):
        if img.mode == "P" and has_transparency:
            converted_img = img.convert("RGBA").convert("RGB")
        elif img.mode in ("RGBA", "LA"):
            converted_img = img.convert("RGB")
        else:
            converted_img = img.convert("RGB")
    elif has_transparency:
        if img.mode != "RGBA":
            converted_img = img.convert("RGBA")
    elif img.mode not in ("RGB", "L"):
        converted_img = img.convert("RGB")

    return converted_img


def _resize_image_if_needed(img: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    """Resize image if larger than max_size."""
    if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
    return img


def optimize_image(
    image_file: File,
    max_size: tuple[int, int] = (3840, 2160),
    quality: int = 90,
    img_format: str = "AVIF",
) -> File | None:
    """
    Optimize an image by:
    1. Checking file size
    2. Converting to AVIF while preserving transparency
    3. Resizing if needed
    4. Optimizing quality

    Transparency is preserved: images with alpha channel (RGBA, LA, or P with transparency)
    are converted to RGBA, while images without transparency are converted to RGB.
    """
    error_msg = f"Image file too large. Maximum size is {MAX_FILE_SIZE/1024/1024:.1f}MB"

    if image_file.size > MAX_FILE_SIZE:
        raise ValidationError(error_msg)

    try:
        img = Image.open(image_file)
        has_transparency = _check_image_has_transparency(img)
        img = _convert_image_mode(img, img_format, has_transparency=has_transparency)
        img = _resize_image_if_needed(img, max_size)

        output = BytesIO()
        img.save(output, format=img_format, quality=quality)
        output.seek(0)

        original_name = Path(image_file.name).stem
        new_name = f"{original_name}.avif"

        return File(output, name=new_name)
    except OSError:
        logger.exception("Error optimizing image")
        return None
