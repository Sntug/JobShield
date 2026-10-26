"""Pure six-field verification against curated, field-specific provenance."""

from datetime import datetime, timezone
import re
from urllib.parse import urlsplit

from pydantic import ValidationError

from app.schemas.verifications import FieldCheck, VerificationCreate, VerificationResponse, VerificationSource
from app.services.verification_values import SHARED_DOMAINS, bank_private_values, claim_key

VERIFICATION_VERSION = "1.2.0"
FIELD_LABELS = {"company_name": "Tên công ty", "tax_id": "Mã số thuế", "contact_email": "Email liên hệ", "recruitment_website": "Website tuyển dụng", "social_channel_url": "Kênh mạng xã hội", "bank_account": "Thông tin tài khoản ngân hàng"}
LIMITATION = "Khớp nguồn không xác nhận tin tuyển dụng thật, an toàn hoặc nên chuyển tiền."


def _as_datetime(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    return value if isinstance(value, datetime) and value.utcoffset() is not None else None


def _eligible(source, now):
    checked = _as_datetime(source.get("verified_at"))
    expiry = _as_datetime(source.get("valid_until"))
    return (source.get("is_active", True) and not source.get("is_demo") and checked is not None
            and checked <= now and (source.get("valid_until") is None or expiry is not None and expiry > now))


def _matches(claim, field, value):
    if claim["field"] == field:
        return claim["value_key"] == claim_key(field, value)
    if claim["field"] == "domain":
        if field == "contact_email":
            domain = value.rsplit("@", 1)[1]
            return domain not in SHARED_DOMAINS and claim_key("domain", domain) == claim["value_key"]
        if field == "recruitment_website":
            domain = urlsplit(value).hostname
            return domain not in SHARED_DOMAINS and claim_key("domain", domain) == claim["value_key"]
    return False


def verify_claims(payload: VerificationCreate, employers: list[dict], *, request_id: str, now: datetime | None = None) -> VerificationResponse:
    now = now or datetime.now(timezone.utc)
    values = payload.model_dump(exclude_none=True)
    bank = values.get("bank_account", {})
    private_values = bank_private_values(bank)

    def public_text(text):
        for value in private_values:
            pattern = re.escape(value) if len(value) >= 4 else r"(?<!\w)" + re.escape(value) + r"(?!\w)"
            text = re.sub(pattern, "•••", text, flags=re.IGNORECASE)
        return text

    records = []
    public_sources = {}
    for employer in employers:
        if not employer.get("is_active", True) or employer.get("is_demo"):
            continue
        claims = []
        for claim in employer.get("claims", []):
            source = claim["source"]
            if not claim.get("is_active", True) or not _eligible(source, now):
                continue
            # A public link/ID must never be an accidental echo of bank input.
            if any(value.casefold() in str(source.get(key, "")).casefold() for value in private_values if len(value) >= 4 for key in ("url", "id")):
                continue
            try:
                public_source = VerificationSource(
                    id=str(source["id"]), url=source["url"], label_vi=public_text(source["label_vi"]),
                    verified_at=source["verified_at"], source_revision=source["source_revision"],
                    evidence_excerpt_vi=public_text(source["evidence_excerpt_vi"]),
                )
            except (KeyError, ValidationError):
                continue
            claims.append(claim)
            public_sources[public_source.id] = public_source
        if claims:
            records.append({**employer, "claims": claims})

    positive = {}
    for field, value in values.items():
        positive[field] = {
            employer["id"] for employer in records
            if any(claim.get("assertion", "supports") == "supports" and _matches(claim, field, value) for claim in employer["claims"])
        }
    strong_sets = [ids for field, ids in positive.items() if field != "company_name" and ids]
    unique_subjects = {next(iter(ids)) for ids in strong_sets if len(ids) == 1}
    split_identity = len(unique_subjects) > 1
    if strong_sets:
        possible_ids = set.intersection(*strong_sets)
    else:
        possible_ids = positive.get("company_name", set())
    candidate = next((emp for emp in records if emp["id"] in possible_ids), None) if len(possible_ids) == 1 else None
    checks = []
    used_sources = set()
    for field, value in values.items():
        matches, refutes = [], []
        if split_identity:
            evidence_records = [emp for emp in records if emp["id"] in positive[field]]
        else:
            evidence_records = [candidate] if candidate else []
        for employer in evidence_records:
            for claim in employer["claims"]:
                if _matches(claim, field, value):
                    target = refutes if claim.get("assertion") == "refutes" else matches
                    target.append(str(claim["source"]["id"]))
        # A verified tax identifier is exclusive to its legal subject; other
        # channels may be additional/unlisted and need explicit refutation.
        if candidate and field == "tax_id" and not matches:
            refutes.extend(str(claim["source"]["id"]) for claim in candidate["claims"] if claim["field"] == "tax_id" and claim.get("assertion", "supports") == "supports")
        scoped_refutes = []
        if candidate is None and not split_identity:
            scoped_refutes = [str(claim["source"]["id"]) for employer in records for claim in employer["claims"] if claim.get("assertion") == "refutes" and _matches(claim, field, value)]
        if split_identity and matches and field != "company_name":
            status, reason = "conflicting", "Định danh này liên kết với chủ thể khác so với định danh còn lại."
        elif refutes:
            status, reason = "conflicting", "Có nguồn kiểm chứng phủ định thông tin này hoặc các nguồn mâu thuẫn."
        elif matches:
            status, reason = "matched", "Thông tin khớp căn cứ kiểm chứng cho đúng trường này."
        elif scoped_refutes:
            status, reason = "unverified", "Có căn cứ phủ định mối liên hệ trong phạm vi một doanh nghiệp; chưa xác định được chủ thể mà bạn cần kiểm tra."
        else:
            status, reason = "unverified", "Chưa có đủ nguồn để đối chiếu thông tin này với một chủ thể duy nhất."
        ids = sorted(set(matches + refutes + scoped_refutes))
        checks.append(FieldCheck(field=field, status=status, reason_vi=reason, source_ids=ids))
        used_sources.update(ids)

    only_name = set(values) == {"company_name"}
    ambiguous = any(len(ids) > 1 for ids in strong_sets) and len(possible_ids) != 1
    if split_identity or any(check.status == "conflicting" for check in checks):
        label = "Thông tin xung đột"
    elif only_name or ambiguous:
        label = "Không đủ dữ liệu"
    elif candidate and all(check.status == "matched" for check in checks):
        label = "Khớp nguồn đã xác minh"
    else:
        label = "Chưa xác minh"
    summaries = {
        "Thông tin xung đột": "Có thông tin đối chiếu mâu thuẫn; cần xác minh lại, chưa kết luận gian lận.",
        "Không đủ dữ liệu": "Chưa đủ dữ kiện để phân biệt và định danh một doanh nghiệp.",
        "Khớp nguồn đã xác minh": "Các thông tin được cung cấp khớp nguồn của một chủ thể đã được đối chiếu.",
        "Chưa xác minh": "Một phần hoặc toàn bộ thông tin chưa có đủ căn cứ kiểm chứng.",
    }
    missing = ["Mã số thuế hoặc kênh tuyển dụng để phân biệt doanh nghiệp"] if label == "Không đủ dữ liệu" else [f"Nguồn đối chiếu cho {FIELD_LABELS[check.field].lower()}" for check in checks if check.status == "unverified"]
    return VerificationResponse(
        request_id=request_id, verification_label_vi=label, summary_vi=summaries[label],
        findings_vi=list(dict.fromkeys(f"{FIELD_LABELS[check.field]}: {check.reason_vi}" for check in checks)),
        field_checks=checks, matched_sources=[public_sources[key] for key in sorted(used_sources)],
        missing_fields_vi=missing, limitations_vi=[LIMITATION, "Đối chiếu kho nguồn được quản trị tại thời điểm kiểm tra; không tra cứu trực tiếp ngân hàng hoặc nền tảng bên ngoài."],
        recommended_actions_vi=["Xác nhận vị trí và người tuyển dụng qua kênh độc lập đã đối chiếu trước khi gửi hồ sơ."] + (["Không coi kết quả này là căn cứ để chuyển tiền hoặc cung cấp dữ liệu ngân hàng."] if bank else []),
        verification_version=VERIFICATION_VERSION, checked_at=now,
    )
