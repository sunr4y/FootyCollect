from io import BytesIO
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.core.files import File
from django.test import TestCase
from PIL import Image

from footycollect.core.utils.images import optimize_image


class TestOptimizeImage(TestCase):
    """Test cases for optimize_image function."""

    def setUp(self):
        """Set up test data."""
        # Create a test image
        self.test_image = Image.new("RGB", (100, 100), color="red")
        self.image_buffer = BytesIO()
        self.test_image.save(self.image_buffer, format="JPEG")
        self.image_buffer.seek(0)

        self.image_file = File(self.image_buffer, name="test.jpg")

    def test_optimize_image_success(self):
        """Test successful image optimization."""
        result = optimize_image(self.image_file, img_format="JPEG")

        assert result is not None
        assert result.name == "test.avif"
        assert isinstance(result, File)

    def test_optimize_image_with_custom_parameters(self):
        """Test image optimization with custom parameters."""
        result = optimize_image(
            self.image_file,
            max_size=(100, 100),
            quality=80,
            img_format="JPEG",
        )

        assert result is not None
        assert result.name == "test.avif"  # Gets .avif extension
        assert isinstance(result, File)

    def test_optimize_image_file_too_large(self):
        """Test image optimization with file too large."""
        # Create a mock file that's too large
        large_file = Mock()
        large_file.size = 20 * 1024 * 1024  # 20MB
        large_file.name = "large.jpg"

        with pytest.raises(ValidationError) as context:
            optimize_image(large_file)

        assert "Image file too large" in str(context.value)

    def test_optimize_image_rgba_conversion(self):
        """Test image optimization with RGBA image."""
        # Create RGBA image
        rgba_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        rgba_buffer = BytesIO()
        rgba_image.save(rgba_buffer, format="PNG")
        rgba_buffer.seek(0)

        rgba_file = File(rgba_buffer, name="test.png")

        result = optimize_image(rgba_file, img_format="JPEG")

        assert result is not None
        assert result.name == "test.avif"

    def test_optimize_image_palette_conversion(self):
        """Test image optimization with palette image."""
        # Create palette image
        palette_image = Image.new("P", (100, 100), color=0)
        palette_buffer = BytesIO()
        palette_image.save(palette_buffer, format="PNG")
        palette_buffer.seek(0)

        palette_file = File(palette_buffer, name="test.png")

        result = optimize_image(palette_file, img_format="JPEG")

        assert result is not None
        assert result.name == "test.avif"

    def test_optimize_image_resize_large_image(self):
        """Test image optimization with large image that needs resizing."""
        # Create large image
        large_image = Image.new("RGB", (5000, 5000), color="blue")
        large_buffer = BytesIO()
        large_image.save(large_buffer, format="JPEG")
        large_buffer.seek(0)

        large_file = File(large_buffer, name="large.jpg")

        result = optimize_image(large_file, max_size=(1000, 1000), img_format="JPEG")

        assert result is not None
        assert result.name == "large.avif"

    def test_optimize_image_os_error(self):
        """Test image optimization with OSError."""
        with patch("PIL.Image.open") as mock_open:
            mock_open.side_effect = OSError("Test error")

            result = optimize_image(self.image_file, img_format="JPEG")

            assert result is None

    def test_optimize_image_with_different_formats(self):
        """Test image optimization with different output formats."""
        formats = ["JPEG", "PNG", "WEBP"]

        for img_format in formats:
            with self.subTest(format=img_format):
                result = optimize_image(self.image_file, img_format=img_format)

                assert result is not None
                assert result.name == "test.avif"  # Extension stays .avif

    def test_optimize_image_quality_settings(self):
        """Test image optimization with different quality settings."""
        qualities = [50, 75, 90, 95]

        for quality in qualities:
            with self.subTest(quality=quality):
                result = optimize_image(self.image_file, quality=quality, img_format="JPEG")

                assert result is not None
                assert result.name == "test.avif"

    def test_optimize_image_max_size_settings(self):
        """Test image optimization with different max size settings."""
        max_sizes = [(100, 100), (500, 500), (1000, 1000), (2000, 2000)]

        for max_size in max_sizes:
            with self.subTest(max_size=max_size):
                result = optimize_image(self.image_file, max_size=max_size, img_format="JPEG")

                assert result is not None
                assert result.name == "test.avif"

    def test_optimize_image_filename_handling(self):
        """Test image optimization with different filename formats."""
        filenames = ["test.jpg", "test.png", "test.webp", "test_with_underscores.jpg"]

        for filename in filenames:
            with self.subTest(filename=filename):
                file_obj = File(self.image_buffer, name=filename)
                result = optimize_image(file_obj, img_format="JPEG")

                assert result is not None
                expected_name = filename.split(".")[0] + ".avif"
                assert result.name == expected_name
