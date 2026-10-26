"""Stateless public verification; all authoritative inputs come from the store."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.verifications import VerificationCreate, VerificationResponse
from app.services.verification_store import load_employers
from app.services.verifications import verify_claims

router = APIRouter(prefix="/verifications", tags=["verifications"])


@router.post("", response_model=VerificationResponse, summary="Đối chiếu thông tin nhà tuyển dụng", responses={413: {"description": "Payload quá lớn"}, 415: {"description": "Sai Content-Type"}, 429: {"description": "Quá giới hạn"}, 503: {"description": "Kho nguồn không khả dụng"}})
def create_verification(payload: VerificationCreate, request: Request, db: Session = Depends(get_db)):
    return verify_claims(payload, load_employers(db, payload), request_id=request.state.request_id)
