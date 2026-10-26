"""Bounded JSON ingress and redacted errors for the public verification endpoint."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.rate_limit import check_rate_limit

MAX_BODY_BYTES = 32 * 1024
MESSAGES = {
    "NO_INPUT_PROVIDED": "Phải cung cấp ít nhất một thông tin để đối chiếu.",
    "VALIDATION_ERROR": "Dữ liệu xác minh không hợp lệ.",
    "PAYLOAD_TOO_LARGE": "Dữ liệu vượt giới hạn 32 KiB.",
    "UNSUPPORTED_MEDIA_TYPE": "Yêu cầu phải dùng application/json.",
    "RATE_LIMITED": "Quá giới hạn yêu cầu. Vui lòng thử lại sau.",
    "SOURCE_STORE_UNAVAILABLE": "Kho nguồn tạm thời không khả dụng. Vui lòng thử lại sau.",
    "INTERNAL_ERROR": "Không thể hoàn tất xác minh. Vui lòng thử lại sau.",
}


def verification_path(path):
    return path.rstrip("/") == "/api/v1/verifications"


def verification_error(request_id, status, code, *, errors=None, headers=None):
    return JSONResponse(status_code=status, content={"detail": {"code": code, "message_vi": MESSAGES[code], "errors": errors or []}, "request_id": request_id}, headers={"Cache-Control": "no-store", **(headers or {})})


def verification_validation_error(request, exc):
    code = "VALIDATION_ERROR"
    errors = []
    known = {"company_name", "tax_id", "contact_email", "recruitment_website", "social_channel_url", "bank_account", "account_number", "bank_name", "account_holder"}
    for error in exc.errors():
        if "NO_INPUT_PROVIDED" in error.get("msg", ""):
            code = "NO_INPUT_PROVIDED"
        location = [part for part in error.get("loc", ()) if part != "body"]
        field = ".".join(location) if location and all(isinstance(part, str) and part in known for part in location) else "$"
        error_type = error.get("type", "")
        if error_type == "extra_forbidden":
            item_code = "UNKNOWN_FIELD"
        elif error_type == "missing":
            item_code = "REQUIRED_FIELD"
        elif error_type == "string_too_long":
            item_code = "TOO_LONG"
        elif error_type.endswith("_type"):
            item_code = "INVALID_TYPE"
        else:
            item_code = "INVALID_FORMAT"
        errors.append({"field": field, "code": item_code, "message_vi": "Trường dữ liệu không đúng yêu cầu."})
    return verification_error(request.state.request_id, 422, code, errors=errors)


class VerificationRequestGuard:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or not verification_path(scope["path"]):
            return await self.app(scope, receive, send)
        request = Request(scope)
        request_id = scope.get("state", {}).get("request_id", "")
        try:
            check_rate_limit(request, bucket="verifications")
        except HTTPException as exc:
            return await verification_error(request_id, 429, "RATE_LIMITED", headers=exc.headers)(scope, receive, send)
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return await verification_error(request_id, 415, "UNSUPPORTED_MEDIA_TYPE")(scope, receive, send)
        try:
            declared_size = int(request.headers.get("content-length", "0"))
        except ValueError:
            declared_size = 0
        if declared_size > MAX_BODY_BYTES:
            return await verification_error(request_id, 413, "PAYLOAD_TOO_LARGE")(scope, receive, send)
        chunks, total = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > MAX_BODY_BYTES:
                return await verification_error(request_id, 413, "PAYLOAD_TOO_LARGE")(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        body = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)
