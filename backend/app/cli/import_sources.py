"""Validate/import locally reviewed source manifests; never a public write API."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.verifications import VerifiedEmployer, EmployerSource, EmployerClaim
from app.schemas.verifications import VerificationCreate
from app.services.verification_values import claim_key
from app.schemas.curation import ManifestClaim, ManifestSource


class ManifestEmployer(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: uuid.UUID
    legal_name: str = Field(min_length=1, max_length=255)
    tax_id: str | None = None
    is_active: bool = True
    is_demo: bool = False
    sources: list[ManifestSource] = Field(min_length=1)

    @field_validator("tax_id")
    @classmethod
    def valid_tax_id(cls, value):
        return None if value is None else VerificationCreate(tax_id=value).tax_id


class SourceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employers: list[ManifestEmployer] = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def unique_ids(self):
        employer_ids = [emp.id for emp in self.employers]
        source_ids = [source.id for emp in self.employers for source in emp.sources]
        if len(set(employer_ids)) != len(employer_ids) or len(set(source_ids)) != len(source_ids):
            raise ValueError("ID nguồn/doanh nghiệp bị trùng trong manifest.")
        return self


def import_sources(db: Session, manifest: SourceManifest, *, skip_unchanged: bool = False) -> tuple[int, int]:
    try:
        source_count = 0
        for entry in manifest.employers:
            employer = db.get(VerifiedEmployer, entry.id)
            identity_unchanged = employer is not None and all(getattr(employer, field) == getattr(entry, field) for field in ('legal_name', 'tax_id', 'is_active', 'is_demo'))
            if employer is None:
                employer = VerifiedEmployer(id=entry.id)
                db.add(employer)
            for field in ("legal_name", "tax_id", "is_active", "is_demo"):
                setattr(employer, field, getattr(entry, field))
            db.flush()
            for item in entry.sources:
                source = db.get(EmployerSource, item.id)
                if source is not None:
                    if skip_unchanged and source.employer_id == employer.id and item.source_revision == source.source_revision:
                        def comparable(value):
                            return value.replace(tzinfo=timezone.utc) if isinstance(value, datetime) and value.tzinfo is None else value
                        same_source = all(comparable(getattr(source, field)) == comparable(getattr(item, field)) for field in ('url', 'label_vi', 'evidence_excerpt_vi', 'reviewed_by', 'verified_at', 'valid_until', 'is_active', 'is_demo'))
                        current_claims = {(claim.field, claim.value_key, claim.assertion, claim.is_active) for claim in db.scalars(select(EmployerClaim).where(EmployerClaim.source_id == source.id))}
                        expected_claims = {(claim.field, claim_key(claim.field, claim.value), claim.assertion, True) for claim in item.claims}
                        if not identity_unchanged or not same_source or current_claims != expected_claims:
                            raise ValueError('Nguồn thay đổi nhưng chưa tăng revision.')
                        source_count += 1
                        continue
                    if source.employer_id != employer.id or item.source_revision <= source.source_revision:
                        raise ValueError("Nguồn đã tồn tại: không đổi chủ thể; cập nhật phải tăng revision.")
                    db.execute(delete(EmployerClaim).where(EmployerClaim.source_id == source.id))
                else:
                    source = EmployerSource(id=item.id, employer_id=employer.id)
                    db.add(source)
                for field in ("url", "label_vi", "evidence_excerpt_vi", "reviewed_by", "verified_at", "valid_until", "source_revision", "is_active", "is_demo"):
                    setattr(source, field, getattr(item, field))
                db.flush()
                for claim in item.claims:
                    db.add(EmployerClaim(employer_id=employer.id, source_id=source.id, field=claim.field, value_key=claim_key(claim.field, claim.value), assertion=claim.assertion))
                source_count += 1
        db.commit()
        return len(manifest.employers), source_count
    except Exception:
        db.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description="Kiểm tra manifest nguồn; chỉ ghi DB khi có --apply.")
    parser.add_argument("file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        if args.file.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("Manifest quá lớn.")
        manifest = SourceManifest.model_validate_json(args.file.read_bytes())
        if args.apply:
            from app.db.session import get_session_local
            with get_session_local()() as db:
                employers, sources = import_sources(db, manifest)
            print(f"Đã nhập {employers} doanh nghiệp, {sources} nguồn.")
        else:
            print(f"Manifest hợp lệ: {len(manifest.employers)} doanh nghiệp. Chưa kết nối hoặc ghi DB.")
    except Exception:
        # Never render validation/SQL exceptions: they can contain raw bank input.
        parser.exit(1, "Không nhập nguồn: file không hợp lệ hoặc DB từ chối. Không có thay đổi được commit.\n")


if __name__ == "__main__":
    main()
