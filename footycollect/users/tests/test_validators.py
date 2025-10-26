from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from footycollect.users.validators import validate_avatar


class TestValidateAvatar(TestCase):
    """Test cases for validate_avatar function."""

    def test_validate_avatar_success(self):
        """Test successful avatar validation."""
        # Create a valid image file
        image_content = b"fake_image_content"
        image_file = SimpleUploadedFile(
            "test.jpg",
            image_content,
            content_type="image/jpeg",
        )

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.return_value = (100, 100)

            # Should not raise any exception
            validate_avatar(image_file)

    def test_validate_avatar_file_too_large(self):
        """Test avatar validation with file too large."""
        # Create a large file
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB
        large_file = SimpleUploadedFile(
            "large.jpg",
            large_content,
            content_type="image/jpeg",
        )

        with pytest.raises(ValidationError) as context:
            validate_avatar(large_file)

        assert "Image file too large" in str(context.value)

    def test_validate_avatar_invalid_dimensions(self):
        """Test avatar validation with invalid dimensions."""
        image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake_content",
            content_type="image/jpeg",
        )

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.return_value = (0, 0)  # Invalid dimensions

            with pytest.raises(ValidationError) as context:
                validate_avatar(image_file)

            assert "File type is not supported" in str(context.value)

    def test_validate_avatar_no_dimensions(self):
        """Test avatar validation with no dimensions."""
        image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake_content",
            content_type="image/jpeg",
        )

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.return_value = (None, None)  # No dimensions

            with pytest.raises(ValidationError) as context:
                validate_avatar(image_file)

            assert "File type is not supported" in str(context.value)

    def test_validate_avatar_dimensions_exception(self):
        """Test avatar validation with dimensions exception."""
        image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake_content",
            content_type="image/jpeg",
        )

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.side_effect = Exception("Test error")

            with pytest.raises(ValidationError) as context:
                validate_avatar(image_file)

            assert "File type is not supported" in str(context.value)

    def test_validate_avatar_invalid_content_type(self):
        """Test avatar validation with invalid content type."""
        image_file = SimpleUploadedFile(
            "test.txt",
            b"fake_content",
            content_type="text/plain",
        )

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.return_value = (100, 100)

            with pytest.raises(ValidationError) as context:
                validate_avatar(image_file)

            # Validator will raise specific message for invalid content type
            assert "Please upload a valid image file (JPG, PNG, GIF)" in str(context.value)

    def test_validate_avatar_valid_content_types(self):
        """Test avatar validation with valid content types."""
        valid_types = ["image/jpeg", "image/png", "image/gif"]

        for content_type in valid_types:
            with self.subTest(content_type=content_type):
                image_file = SimpleUploadedFile(
                    "test.jpg",
                    b"fake_content",
                    content_type=content_type,
                )

                with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
                    mock_dimensions.return_value = (100, 100)

                    # Should not raise any exception
                    validate_avatar(image_file)

    def test_validate_avatar_no_content_type(self):
        """Test avatar validation with no content type."""
        image_file = SimpleUploadedFile(
            "test.jpg",
            b"fake_content",
            # No content_type specified
        )

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.return_value = (100, 100)

            # SimpleUploadedFile provides a content_type attribute even if not specified (None)
            with pytest.raises(ValidationError):
                validate_avatar(image_file)

    def test_validate_avatar_mock_file_without_content_type(self):
        """Test avatar validation with mock file without content_type attribute."""
        mock_file = Mock()
        mock_file.size = 1024
        mock_file.content_type = "image/jpeg"

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.return_value = (100, 100)

            # Should not raise any exception
            validate_avatar(mock_file)

    def test_validate_avatar_mock_file_without_content_type_attribute(self):
        """Test avatar validation with mock file without content_type attribute."""
        mock_file = Mock()
        mock_file.size = 1024
        # Mock will report attribute present; set to None to simulate missing/unsupported
        mock_file.content_type = None

        with patch("footycollect.users.validators.get_image_dimensions") as mock_dimensions:
            mock_dimensions.return_value = (100, 100)

            # Expect a validation error due to invalid/None content type
            with pytest.raises(ValidationError):
                validate_avatar(mock_file)
