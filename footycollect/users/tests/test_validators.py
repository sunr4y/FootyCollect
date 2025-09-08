"""
Tests for user validators.
"""

import contextlib
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from footycollect.users.validators import validate_avatar


class TestValidateAvatar:
    """Test avatar validation function."""

    def test_valid_avatar_jpeg(self):
        """Test that valid JPEG avatar passes validation."""
        # Use real test image
        test_image_path = Path(__file__).parent / "test_images" / "test_avatar.jpg"

        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "test_avatar.jpg",
                f.read(),
                content_type="image/jpeg",
            )

        # Should not raise ValidationError
        try:
            validate_avatar(test_image)
        except ValidationError:
            pytest.fail("Valid JPEG avatar failed validation")

    def test_valid_avatar_png(self):
        """Test that valid PNG avatar passes validation."""
        # Use real test image
        test_image_path = Path(__file__).parent / "test_images" / "test_avatar.png"

        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "test_avatar.png",
                f.read(),
                content_type="image/png",
            )

        # Should not raise ValidationError
        try:
            validate_avatar(test_image)
        except ValidationError:
            pytest.fail("Valid PNG avatar failed validation")

    def test_valid_avatar_gif(self):
        """Test that valid GIF avatar passes validation."""
        # Use real test image
        test_image_path = Path(__file__).parent / "test_images" / "test_avatar.gif"

        with test_image_path.open("rb") as f:
            test_image = SimpleUploadedFile(
                "test_avatar.gif",
                f.read(),
                content_type="image/gif",
            )

        # Should not raise ValidationError
        try:
            validate_avatar(test_image)
        except ValidationError:
            pytest.fail("Valid GIF avatar failed validation")

    def test_invalid_file_type(self):
        """Test that invalid file types are rejected."""
        # Create an invalid file type
        test_file = SimpleUploadedFile(
            "test_document.pdf",
            b"fake_pdf_content",
            content_type="application/pdf",
        )

        with pytest.raises(ValidationError, match="File type is not supported"):
            validate_avatar(test_file)

    def test_file_too_large(self):
        """Test that files larger than 10MB are rejected."""
        # Create a file larger than 10MB
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        test_image = SimpleUploadedFile(
            "large_avatar.jpg",
            large_content,
            content_type="image/jpeg",
        )

        with pytest.raises(ValidationError, match="Image file too large"):
            validate_avatar(test_image)

    def test_file_without_content_type(self):
        """Test that files without content type are handled."""
        # Use real test image but without content type
        test_image_path = Path(__file__).parent / "test_images" / "test_avatar.jpg"

        with test_image_path.open("rb") as f:
            test_file = SimpleUploadedFile(
                "test_file",
                f.read(),
                content_type=None,
            )

        # Should not raise ValidationError for content type check
        # but might raise for other validation
        with contextlib.suppress(ValidationError):
            validate_avatar(test_file)

    def test_empty_file(self):
        """Test that empty files are rejected."""
        # Create an empty file
        test_image = SimpleUploadedFile(
            "empty_avatar.jpg",
            b"",
            content_type="image/jpeg",
        )

        with pytest.raises(ValidationError):
            validate_avatar(test_image)
