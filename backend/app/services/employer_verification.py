"""Pure channel comparison against records supplied by the caller; no network I/O."""

from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

from app.schemas.analyses import JobExtracted


def _normalize_page(value: str) -> str:
    """URL paths remain case-sensitive even though hostnames do not."""
    try:
        parts = urlsplit(value.strip())
        if not parts.hostname:
            return ""
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, parts.fragment))
    except ValueError:
        return ""


def _has_provenance(source: dict, employer: dict, is_demo: bool) -> bool:
    if not all(source.get(key) for key in ("id", "url", "label_vi")):
        return False
    if is_demo:
        return True
    if source.get("is_demo") or employer.get("is_demo"):
        return False
    try:
        return datetime.fromisoformat(source.get("verified_at", "")).utcoffset() is not None
    except (ValueError, TypeError):
        return False


def verify_employer(job: JobExtracted, employers: list[dict], is_demo: bool = False) -> tuple[str, list[dict]]:
    """Return a status and its candidate records, without choosing by record order."""
    if employers and all("claims" in emp for emp in employers):
        from app.schemas.verifications import VerificationCreate
        from app.services.verifications import verify_claims
        from pydantic import ValidationError
        try:
            payload = VerificationCreate(company_name=job.company_name, contact_email=job.contact_email, recruitment_website=job.recruitment_website)
        except ValidationError:
            label = "Không đủ dữ liệu" if not (job.company_name or job.contact_email or job.recruitment_website) else "Chưa xác minh"
            return label, []
        result = verify_claims(payload, employers, request_id="internal")
        return result.verification_label_vi, employers
    if not (job.company_name or job.contact_email or job.recruitment_website):
        return "Không đủ dữ liệu", []
    candidates = [
        emp for emp in employers
        if job.company_name and emp.get("name")
        and emp["name"].strip().casefold() == job.company_name.strip().casefold()
        and (is_demo or not emp.get("is_demo"))
    ]
    if not candidates or not (job.contact_email or job.recruitment_website):
        return "Chưa xác minh", candidates

    matched, conflicting = [], []
    for emp in candidates:
        domains = {d.strip().casefold() for d in emp.get("official_domains", [])}
        contacts = {c.strip().casefold() for c in emp.get("official_contacts", [])}
        pages = {_normalize_page(p) for p in emp.get("official_recruitment_pages", [])} - {""}
        channel_matches, channel_conflicts = [], []
        if job.contact_email:
            email = job.contact_email.strip().casefold()
            matches = email in contacts or ("@" in email and email.rsplit("@", 1)[1] in domains)
            channel_matches.append(matches)
            channel_conflicts.append(bool(domains or contacts) and not matches)
        if job.recruitment_website:
            page = _normalize_page(job.recruitment_website)
            matches = bool(page) and (page in pages or urlsplit(page).hostname in domains)
            channel_matches.append(matches)
            channel_conflicts.append(bool(page and (domains or pages)) and not matches)

        sources = [s for s in emp.get("sources", []) if _has_provenance(s, emp, is_demo)]
        if any(channel_conflicts):
            conflicting.append(emp)
        elif all(channel_matches) and sources:
            matched.append({**emp, "sources": sources})

    if len(matched) == 1 and len(conflicting) == len(candidates) - 1:
        return "Khớp nguồn đã xác minh", matched
    if len(conflicting) == len(candidates):
        return "Thông tin xung đột", conflicting
    return "Chưa xác minh", matched or candidates
