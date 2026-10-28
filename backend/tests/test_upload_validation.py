"""Unit tests for upload validation (R3.1)."""

import pytest

from app.core.upload_validation import (
    ALLOWED_IMAGE_TYPES,
    MAX_UPLOAD_SIZE_BYTES,
    UploadValidationError,
    detect_image_format,
    validate_image_upload,
)

from tests.extraction_helpers import image_bytes

SAMPLE_PNG = image_bytes()
SAMPLE_JPEG = image_bytes("JPEG")
SAMPLE_WEBP = image_bytes("WEBP")


def test_empty_upload_rejected():
    with pytest.raises(UploadValidationError) as exc:
        validate_image_upload(b"")
    assert exc.value.code == "EMPTY_FILE"


def test_oversized_upload_rejected():
    large_bytes = SAMPLE_PNG + b"0" * (MAX_UPLOAD_SIZE_BYTES + 1)
    with pytest.raises(UploadValidationError) as exc:
        validate_image_upload(large_bytes)
    assert exc.value.code == "FILE_TOO_LARGE"


@pytest.mark.parametrize(
    "content,expected_mime",
    [
        (SAMPLE_PNG, "image/png"),
        (SAMPLE_JPEG, "image/jpeg"),
        (SAMPLE_WEBP, "image/webp"),
    ],
)
def test_valid_image_formats_accepted(content, expected_mime):
    detected, filename = validate_image_upload(content, filename="test.png")
    assert detected == expected_mime
    assert filename == "test.png"


@pytest.mark.parametrize(
    "bad_content",
    [
        b"<svg><script>alert(1)</script></svg>",
        b"<html><body>Not an image</body></html>",
        b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00",
        b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00",
        b"Hello world text file",
        b"\x00" * 30,
    ],
)
def test_unsupported_formats_rejected(bad_content):
    with pytest.raises(UploadValidationError) as exc:
        validate_image_upload(bad_content)
    assert exc.value.code == "UNSUPPORTED_IMAGE_FORMAT"


def test_declared_mime_mismatch_rejected():
    with pytest.raises(UploadValidationError) as exc:
        validate_image_upload(SAMPLE_PNG, declared_content_type="image/jpeg")
    assert exc.value.code == "MIME_MISMATCH"


def test_filename_sanitization():
    _, clean_name = validate_image_upload(
        SAMPLE_PNG,
        filename="../../../etc/passwd/hack<script>.png",
    )
    assert ".." not in clean_name
    assert "/" not in clean_name
    assert "<" not in clean_name
    assert clean_name.endswith(".png")
