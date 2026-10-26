"""Read curated claims with indexed lookup; no input values are persisted."""

from datetime import datetime, timezone
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.verifications import VerifiedEmployer, EmployerSource, EmployerClaim
from app.schemas.verifications import VerificationCreate
from app.services.verification_values import lookup_keys


def load_employers(db: Session, payload: VerificationCreate, *, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    join_source = and_(EmployerClaim.source_id == EmployerSource.id, EmployerClaim.employer_id == EmployerSource.employer_id)
    usable = (
        VerifiedEmployer.is_active.is_(True), VerifiedEmployer.is_demo.is_(False),
        EmployerSource.is_active.is_(True), EmployerSource.is_demo.is_(False),
        EmployerClaim.is_active.is_(True), EmployerSource.verified_at <= now,
        or_(EmployerSource.valid_until.is_(None), EmployerSource.valid_until > now),
    )
    keys = lookup_keys(payload)
    if not keys:
        return []
    matches = or_(*(and_(EmployerClaim.field == field, EmployerClaim.value_key == value) for field, value in keys))
    ids = (select(EmployerClaim.employer_id).join(EmployerSource, join_source)
           .join(VerifiedEmployer, VerifiedEmployer.id == EmployerClaim.employer_id)
           .where(*usable, matches).distinct())
    query = (select(VerifiedEmployer, EmployerSource, EmployerClaim).select_from(EmployerClaim)
             .join(EmployerSource, join_source).join(VerifiedEmployer, VerifiedEmployer.id == EmployerClaim.employer_id)
             .where(*usable, EmployerClaim.employer_id.in_(ids))
             .order_by(VerifiedEmployer.id, EmployerSource.id, EmployerClaim.id))
    records = {}
    for employer, source, claim in db.execute(query):
        key = str(employer.id)
        record = records.setdefault(key, {"id": key, "name": employer.legal_name, "is_active": True, "is_demo": False, "claims": []})
        checked = source.verified_at
        expiry = source.valid_until
        # SQLite test timestamps lose timezone; PostgreSQL uses TIMESTAMPTZ.
        if checked.tzinfo is None:
            checked = checked.replace(tzinfo=timezone.utc)
        if expiry is not None and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        record["claims"].append({"field": claim.field, "value_key": claim.value_key, "assertion": claim.assertion, "source": {
            "id": str(source.id), "url": source.url, "label_vi": source.label_vi,
            "evidence_excerpt_vi": source.evidence_excerpt_vi, "verified_at": checked,
            "valid_until": expiry, "source_revision": source.source_revision,
            "is_active": True, "is_demo": False,
        }})
    return list(records.values())


def load_for_job(db: Session, job) -> list[dict]:
    from pydantic import ValidationError
    try:
        payload = VerificationCreate(company_name=job.company_name, contact_email=job.contact_email, recruitment_website=job.recruitment_website)
    except ValidationError:
        # Invalid extracted channels cannot establish verified source identity.
        return []
    return load_employers(db, payload)
