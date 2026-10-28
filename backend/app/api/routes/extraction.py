"""Bounded, validated OCR and public URL extraction endpoints."""

import base64
import binascii
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.core.privacy import get_privacy_headers
from app.core.rate_limit import check_rate_limit
from app.core.upload_validation import MAX_UPLOAD_SIZE_BYTES
from app.schemas.extraction import ExtractionResponse, ImageExtractionRequest, URLExtractionRequest
from app.services.ocr import extract_text_from_image
from app.services.url_extraction import extract_text_from_url

router = APIRouter(prefix="/extractions", tags=["extractions"])
MAX_JSON_IMAGE_BYTES = ((MAX_UPLOAD_SIZE_BYTES + 2) // 3) * 4 + 4096


async def read_body(request: Request, limit: int) -> bytes:
    try:
        declared_size = int(request.headers.get("Content-Length", "0"))
    except ValueError:
        raise HTTPException(422, "Kích thước yêu cầu không hợp lệ.") from None
    if declared_size > limit:
        raise HTTPException(413, "Dữ liệu tải lên vượt giới hạn cho phép.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise HTTPException(413, "Dữ liệu tải lên vượt giới hạn cho phép.")
        body.extend(chunk)
    return bytes(body)


def parse_payload(model, body):
    try:
        return model.model_validate(body)
    except ValidationError:
        raise HTTPException(422, "Dữ liệu trích xuất không hợp lệ. Vui lòng kiểm tra các trường nhập.") from None


async def read_json(request: Request, limit: int):
    raw = await read_body(request, limit)
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "Dữ liệu JSON không hợp lệ.") from None
    if not isinstance(body, dict):
        raise HTTPException(422, "Dữ liệu JSON phải là một đối tượng.")
    return body


def prepare(request: Request, response: Response) -> str:
    check_rate_limit(request, bucket="extractions")
    response.headers.update(get_privacy_headers())
    return getattr(request.state, "request_id", uuid.uuid4().hex)


async def url_result(payload: URLExtractionRequest, req_id: str) -> ExtractionResponse:
    result = await run_in_threadpool(extract_text_from_url, payload.url)
    return ExtractionResponse(
        request_id=req_id, success=result.success, source_type="url", text=result.text,
        failure_vi=result.failure_vi, source_name=result.source_url,
    )


async def image_result(image_bytes: bytes, filename: Optional[str], mime: Optional[str], req_id: str) -> ExtractionResponse:
    if not image_bytes:
        raise HTTPException(422, "Tệp ảnh tải lên không có dữ liệu.")
    result = await run_in_threadpool(extract_text_from_image, image_bytes, filename=filename, declared_content_type=mime)
    return ExtractionResponse(
        request_id=req_id, success=result.success, source_type="image", text=result.text,
        failure_vi=result.failure_vi, source_name=filename or "upload.png", confidence=result.confidence,
    )


def decode_image(payload: ImageExtractionRequest) -> bytes:
    try:
        image_bytes = base64.b64decode(payload.image_base64, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, "Chuỗi base64 không hợp lệ.") from None
    if len(image_bytes) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(413, "Kích thước ảnh vượt giới hạn 5MB.")
    return image_bytes


@router.post("/url", response_model=ExtractionResponse, summary="Trích xuất văn bản từ URL công khai")
async def extract_from_url_endpoint(request: Request, response: Response) -> ExtractionResponse:
    req_id = prepare(request, response)
    payload = parse_payload(URLExtractionRequest, await read_json(request, 8192))
    return await url_result(payload, req_id)


@router.post("/image", response_model=ExtractionResponse, summary="Trích xuất văn bản từ ảnh tuyển dụng (OCR)")
async def extract_from_image_endpoint(
    request: Request, response: Response, content_type: Optional[str] = Header(None),
) -> ExtractionResponse:
    req_id = prepare(request, response)
    ct = (content_type or "").split(";", 1)[0].strip().lower()
    if ct == "application/json":
        payload = parse_payload(ImageExtractionRequest, await read_json(request, MAX_JSON_IMAGE_BYTES))
        return await image_result(decode_image(payload), payload.filename, payload.content_type, req_id)
    image_bytes = await read_body(request, MAX_UPLOAD_SIZE_BYTES)
    return await image_result(image_bytes, request.headers.get("X-Filename"), ct, req_id)


@router.post("", response_model=ExtractionResponse, summary="Trích xuất từ URL hoặc ảnh Base64")
async def generic_extraction_endpoint(request: Request, response: Response) -> ExtractionResponse:
    req_id = prepare(request, response)
    body = await read_json(request, MAX_JSON_IMAGE_BYTES)
    if "url" in body:
        return await url_result(parse_payload(URLExtractionRequest, body), req_id)
    payload = parse_payload(ImageExtractionRequest, body)
    return await image_result(decode_image(payload), payload.filename, payload.content_type, req_id)
