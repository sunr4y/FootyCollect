import logging
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files import File
from PIL import Image

MAX_FILE_SIZE = 15 * 1024 * 1024
logger = logging.getLogger(__name__)


def optimize_image(
    image_file: File,
    max_size: tuple[int, int] = (3840, 2160),
    quality: int = 90,
    img_format: str = "AVIF",
) -> File | None:
    """
    Optimize an image by:
    1. Checking file size
    2. Converting to AVIF
    3. Resizing if needed
    4. Optimizing quality
    """
    error_msg = f"Image file too large. Maximum size is {MAX_FILE_SIZE/1024/1024:.1f}MB"

    # Check file size
    if image_file.size > MAX_FILE_SIZE:
        raise ValidationError(error_msg)

    try:
        img = Image.open(image_file)

        # Convert to RGB if needed
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Resize if larger than max_size
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save as AVIF
        output = BytesIO()
        img.save(output, format=img_format, quality=quality)
        output.seek(0)

        # Prepare filename
        original_name = Path(image_file.name).stem
        new_name = f"{original_name}.avif"

        return File(output, name=new_name)
    except OSError:
        logger.exception("Error optimizing image")
        return None
