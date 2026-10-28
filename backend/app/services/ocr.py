"""OCR service for extracting text from recruitment images.

Hỗ trợ:
- Nhận diện văn bản từ ảnh (PNG, JPEG, WebP).
- Đọc pixel ảnh bằng Tesseract vie+eng.
- Trả về thông báo lỗi rõ ràng nếu ảnh mờ, không có chữ hoặc không thể đọc được.
- Đảm bảo người dùng luôn có thể dán hoặc nhập văn bản thủ công khi trích xuất thất bại.
"""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from app.core.upload_validation import validate_image_upload, UploadValidationError

logger = logging.getLogger("uvicorn.error")


@dataclass
class OCRResult:
    """Kết quả trích xuất văn bản từ hình ảnh."""

    success: bool
    text: Optional[str] = None
    failure_vi: Optional[str] = None
    confidence: Optional[float] = None


def run_system_tesseract(image_bytes: bytes) -> Optional[str]:
    """Thử chạy lệnh tesseract CLI nếu được cài đặt trên hệ thống."""
    tesseract_path = shutil.which("tesseract")
    if not tesseract_path:
        return None

    try:
        proc = subprocess.run(
            [tesseract_path, "stdin", "stdout", "-l", "vie+eng"],
            input=image_bytes,
            capture_output=True,
            timeout=10,
        )
        if proc.returncode == 0:
            text = proc.stdout.decode("utf-8", errors="replace").strip()
            if text:
                return text
    except Exception as exc:
        logger.warning("Không thể thực thi OCR (%s).", type(exc).__name__)

    return None


def extract_text_from_image(
    image_bytes: bytes,
    filename: Optional[str] = None,
    declared_content_type: Optional[str] = None,
) -> OCRResult:
    """Trích xuất văn bản từ tệp ảnh sau khi xác thực an toàn.

    Returns:
        OCRResult với text nếu thành công, hoặc failure_vi nếu thất bại.
    """
    try:
        validate_image_upload(
            image_bytes,
            filename=filename,
            declared_content_type=declared_content_type,
        )
    except UploadValidationError as err:
        return OCRResult(
            success=False,
            text=None,
            failure_vi=err.message_vi,
        )

    tesseract_text = run_system_tesseract(image_bytes)
    if tesseract_text and len(tesseract_text) > 5:
        return OCRResult(
            success=True,
            text=tesseract_text,
        )

    return OCRResult(
        success=False,
        text=None,
        failure_vi="Không nhận diện được nội dung văn bản từ ảnh. Vui lòng dán hoặc nhập văn bản tuyển dụng thủ công.",
    )
