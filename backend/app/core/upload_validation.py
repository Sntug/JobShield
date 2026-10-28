"""Upload validation for recruitment images and evidence files.

Bảo vệ an toàn upload: giới hạn kích thước, kiểm tra MIME type và magic bytes thực tế.
Kiểm tra cấu trúc và kích thước pixel bằng Pillow trước khi gọi OCR.
"""

from io import BytesIO
from typing import Optional, Set, Tuple
import warnings

from PIL import Image

# Kích thước tệp tối đa: 5 MB
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024

# Các định dạng ảnh được hỗ trợ
ALLOWED_IMAGE_TYPES: Set[str] = {
    "image/png",
    "image/jpeg",
    "image/webp",
}

# Magic bytes signatures
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
RIFF_MAGIC = b"RIFF"
WEBP_MAGIC = b"WEBP"


class UploadValidationError(Exception):
    """Lỗi xác thực tệp upload."""

    def __init__(self, message_vi: str, code: str = "INVALID_UPLOAD"):
        super().__init__(message_vi)
        self.message_vi = message_vi
        self.code = code


def detect_image_format(content: bytes) -> Optional[str]:
    """Nhận diện định dạng ảnh dựa trên magic bytes của dữ liệu thô."""
    if len(content) < 12:
        return None

    if content.startswith(PNG_MAGIC):
        return "image/png"

    if content.startswith(JPEG_MAGIC):
        return "image/jpeg"

    if content.startswith(RIFF_MAGIC) and content[8:12] == WEBP_MAGIC:
        return "image/webp"

    return None


def validate_image_upload(
    content: bytes,
    filename: Optional[str] = None,
    declared_content_type: Optional[str] = None,
    max_size: int = MAX_UPLOAD_SIZE_BYTES,
) -> Tuple[str, str]:
    """Kiểm tra tính hợp lệ của tệp ảnh upload.

    Returns:
        Tuple[str, str]: (detected_mime_type, sanitized_filename)

    Raises:
        UploadValidationError: Nếu tệp không hợp lệ về kích thước, định dạng hoặc nội dung.
    """
    if not content or len(content) == 0:
        raise UploadValidationError(
            "Tệp ảnh rỗng hoặc không có dữ liệu.",
            code="EMPTY_FILE",
        )

    if len(content) > max_size:
        max_mb = max_size // (1024 * 1024)
        raise UploadValidationError(
            f"Kích thước tệp ({len(content) // 1024} KB) vượt quá giới hạn tối đa {max_mb}MB.",
            code="FILE_TOO_LARGE",
        )

    detected_mime = detect_image_format(content)
    if not detected_mime or detected_mime not in ALLOWED_IMAGE_TYPES:
        raise UploadValidationError(
            "Định dạng tệp không được hỗ trợ. Chỉ chấp nhận ảnh PNG, JPEG hoặc WebP.",
            code="UNSUPPORTED_IMAGE_FORMAT",
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                if image.width * image.height > 16_000_000:
                    raise UploadValidationError("Ảnh vượt giới hạn 16 triệu điểm ảnh.", code="IMAGE_TOO_LARGE")
                image.verify()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise UploadValidationError("Tệp ảnh bị hỏng hoặc không đọc được.", code="INVALID_IMAGE") from None

    # Nếu client có khai báo content-type, kiểm tra xem có khớp không
    if declared_content_type:
        clean_declared = declared_content_type.split(";")[0].strip().lower()
        if clean_declared != detected_mime:
            raise UploadValidationError(
                "Nội dung tệp thực tế không khớp với định dạng đã khai báo.",
                code="MIME_MISMATCH",
            )

    # Chuẩn hóa tên tệp an toàn
    clean_filename = "upload.png"
    if filename:
        import os
        base = os.path.basename(filename).strip()
        # Loại bỏ ký tự nguy hiểm
        sanitized = "".join(c for c in base if c.isalnum() or c in "._- ")
        if sanitized:
            clean_filename = sanitized[:100]

    return detected_mime, clean_filename
