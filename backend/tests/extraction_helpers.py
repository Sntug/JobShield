"""Real image fixtures; extraction fakes stay in tests, never in the app."""

from io import BytesIO
from PIL import Image

JOB_TEXT = "Cong ty Cong nghe ABC tuyen dung Ky su Backend luong 20 trieu dong. Email tuyendung@mau-a.example."


def image_bytes(format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format=format)
    return buffer.getvalue()
