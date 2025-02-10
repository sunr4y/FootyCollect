from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.utils.translation import gettext_lazy as _


def validate_avatar(image):
    """Validate avatar file size and type"""

    def raise_unsupported():
        raise ValidationError(_("File type is not supported"))

    # Check file size
    if image.size > 10 * 1024 * 1024:  # 10MB
        raise ValidationError(_("Image file too large ( > 10mb )"))

    # Check if it's an image
    try:
        w, h = get_image_dimensions(image)
        if not w or not h:
            raise_unsupported()
    except Exception as e:
        raise ValidationError(_("File type is not supported")) from e

    # Check file type
    valid_types = ["image/jpeg", "image/png", "image/gif"]
    if hasattr(image, "content_type") and image.content_type not in valid_types:
        raise ValidationError(_("Please upload a valid image file (JPG, PNG, GIF)"))
