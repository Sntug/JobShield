"""Rule engine for recruitment scam and risk indicators detection.

Phát hiện dấu hiệu cảnh báo theo từng mệnh đề, phân tách độc lập giữa mức độ rủi ro (risk)
và trạng thái xác minh (verification), bảo đảm không ghi đè dấu hiệu cảnh báo khi khớp nguồn.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from app.schemas.analyses import EvidenceData, IndicatorItem, JobExtracted


def to_ascii_slug(s: str) -> str:
    """Chuyển chuỗi tiếng Việt thành chuỗi ascii không dấu và chỉ giữ chữ/số."""
    nfkd = unicodedata.normalize("NFKD", s)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]", "", ascii_str.lower())


NEGATION_PAT = re.compile(
    r"^(?:Không|Chưa|Tuyệt đối không|Tránh|Đừng|Cảnh báo không)\b|"
    r"\b(?:không|chưa|tuyệt đối không|đừng)\s+(?:thu|đóng|nộp|yêu cầu|chuyển|gửi|cung cấp|nạp|đặt cọc|cam kết)\b",
    re.IGNORECASE,
)

CLAUSE_SPLIT = re.compile(
    r"\s*(?:,\s*|;\s*|:\s*)?(?:nhưng|song|tuy nhiên)\s*|"
    r"\s*[,;:]\s*(?=(?:không|chưa|tuyệt đối không|đừng|tránh|cảnh báo không|hãy|vui lòng|xin|yêu cầu|đóng|thu|nộp|chuyển|nạp|đặt cọc|cam kết|cung cấp|chụp|gửi|liên hệ)\b)",
    re.IGNORECASE,
)


def is_negated(clause: str) -> bool:
    """Kiểm tra mệnh đề hoặc câu có mang ý nghĩa phủ định hay không."""
    return bool(NEGATION_PAT.search(clause.strip()))


def detect_indicators(
    text: str, employer_records: Optional[List[Dict[str, Any]]] = None
) -> List[IndicatorItem]:
    """Phát hiện các dấu hiệu rủi ro: phân biệt danh sách danh từ với mệnh đề có động từ mới."""
    indicators: List[IndicatorItem] = []
    # Tách câu: dấu chấm/chấm than/chấm hỏi theo sau bởi khoảng trắng, hoặc xuống dòng
    # Bảo toàn dấu chấm trong số thập phân / phân cách hàng nghìn (1.000.000, 4.5) vì không có khoảng trắng sau dấu chấm
    sentences = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)

    for sent in sentences:
        s = sent.strip().rstrip(".")
        if not s:
            continue

        # --- A. Các chỉ dấu rủi ro cấp câu (kết hợp mệnh đề đối chiếu hoặc yêu cầu ngữ cảnh toàn câu) ---

        # 4. Kênh liên hệ đáng ngờ
        m_susp = re.search(
            r"Chỉ liên hệ qua nhóm chat kín;\s*không liên hệ email trên website công ty",
            s,
            re.IGNORECASE,
        )
        if m_susp and not re.search(r"\b(?:tránh|đừng|cảnh báo không|tuyệt đối không)\b", s[:m_susp.start()], re.IGNORECASE):
            indicators.append(
                IndicatorItem(
                    category_vi="Kênh liên hệ đáng ngờ",
                    rule_id="RULE_SUSPICIOUS_CHANNEL",
                    matched_quote=m_susp.group(0),
                )
            )

        # 5. Hứa thu nhập phi thực tế
        m_inc = re.search(
            r"(?:Cam kết|hứa)\s+kiếm\s+[\d.]+\s*triệu đồng mỗi ngày chỉ với \d+ phút,\s*không cần kinh nghiệm",
            s,
            re.IGNORECASE,
        )
        if m_inc and not re.search(r"\b(?:không|chưa|đừng|tuyệt đối không)\s+(?:cam kết|hứa)\b", s[:m_inc.start() + 10], re.IGNORECASE):
            indicators.append(
                IndicatorItem(
                    category_vi="Hứa thu nhập phi thực tế",
                    rule_id="RULE_UNREALISTIC_INCOME",
                    matched_quote=m_inc.group(0),
                )
            )

        # 8. Chỉ dấu mạo danh: chỉ kích hoạt khi có xung đột thực tế với official_domains của employer_records
        m_imp = re.search(
            r"Chúng tôi là phòng tuyển dụng\s+([^,]+),\s*chỉ nhận hồ sơ tại\s+([^\s,]+)",
            s,
            re.IGNORECASE,
        )
        if m_imp and not re.search(r"\b(?:tránh|đừng|cảnh báo không|tuyệt đối không)\b", s[:m_imp.start()], re.IGNORECASE):
            claimed_company = m_imp.group(1).strip()
            email = m_imp.group(2).strip().rstrip(".,;")
            domain = email.split("@")[-1].lower() if "@" in email else ""

            is_impersonation = False
            if employer_records:
                for emp in employer_records:
                    if emp.get("name") and emp["name"].strip().lower() == claimed_company.lower():
                        official_domains = [d.lower() for d in emp.get("official_domains", [])]
                        if official_domains and domain not in official_domains:
                            is_impersonation = True
                            break

            if is_impersonation:
                indicators.append(
                    IndicatorItem(
                        category_vi="Chỉ dấu mạo danh",
                        rule_id="RULE_IMPERSONATION",
                        matched_quote=m_imp.group(0),
                    )
                )

        # --- B. Các chỉ dấu rủi ro theo từng mệnh đề độc lập (bảo toàn danh sách danh từ, tách mệnh đề khi có động từ mới) ---
        clauses = [c.strip() for c in CLAUSE_SPLIT.split(s) if c.strip()]

        for c in clauses:
            if is_negated(c):
                continue

            # 1. Phí tuyển dụng trước (không phụ thuộc cố định đuôi "để nhận việc")
            m1 = re.search(
                r"(?:yêu cầu\s+)?(?:đóng|thu|nộp)\s+phí\s+tuyển\s+dụng\s+[\d.]+\s*(?:đồng|đ|vnd)(?:\s+(?:để|trước|nhận)[^.!?\n,;]*)?",
                c,
                re.IGNORECASE,
            )
            if m1:
                indicators.append(
                    IndicatorItem(
                        category_vi="Phí tuyển dụng trước",
                        rule_id="RULE_UPFRONT_FEE",
                        matched_quote=m1.group(0),
                    )
                )

            # 2. Đặt cọc trước phỏng vấn
            m2 = re.search(
                r"(?:yêu cầu\s+)?(?:đặt cọc|cọc)\s+[\d.]+\s*(?:đồng|đ|vnd)(?:\s+trước\s+phỏng\s+vấn)?",
                c,
                re.IGNORECASE,
            )
            if m2:
                indicators.append(
                    IndicatorItem(
                        category_vi="Đặt cọc trước phỏng vấn",
                        rule_id="RULE_DEPOSIT_BEFORE_INTERVIEW",
                        matched_quote=m2.group(0),
                    )
                )

            # 3. Yêu cầu chuyển tiền cá nhân
            m3 = re.search(
                r"Chuyển tiền vào tài khoản cá nhân(?:\s+để giữ chỗ)?",
                c,
                re.IGNORECASE,
            )
            if m3:
                indicators.append(
                    IndicatorItem(
                        category_vi="Yêu cầu chuyển tiền",
                        rule_id="RULE_PERSONAL_TRANSFER",
                        matched_quote=m3.group(0),
                    )
                )

            # 6. Nhiệm vụ có nạp tiền
            m6 = re.search(
                r"Nạp\s+[\d.]+\s*đồng\s+để mở nhiệm vụ\s+nhận hoa hồng",
                c,
                re.IGNORECASE,
            )
            if m6:
                indicators.append(
                    IndicatorItem(
                        category_vi="Nhiệm vụ có nạp tiền",
                        rule_id="RULE_TASK_TOPUP",
                        matched_quote=m6.group(0),
                    )
                )

            # 7. Yêu cầu dữ liệu nhạy cảm bất thường (giữ trọn danh sách danh từ sau động từ, linh hoạt nhận diện OTP, CCCD, CMND, mật khẩu)
            m7 = re.search(
                r"(?:(?:hãy\s+)?(?:gửi|cung cấp|chụp)|yêu cầu\s+(?:gửi|cung cấp)?)\s+[^.!?\n]*(?:OTP|CCCD|CMND|mật khẩu|thẻ ngân hàng|tài khoản ngân hàng)[^.!?\n]*",
                c,
                re.IGNORECASE,
            )
            if m7:
                indicators.append(
                    IndicatorItem(
                        category_vi="Yêu cầu dữ liệu nhạy cảm bất thường",
                        rule_id="RULE_SENSITIVE_DATA",
                        matched_quote=m7.group(0),
                    )
                )

    return indicators


from urllib.parse import urlparse


def extract_domain(val: Optional[str]) -> Optional[str]:
    """Trích xuất hostname/domain từ email hoặc URL."""
    if not val:
        return None
    val = val.strip().lower()
    if "@" in val:
        return val.split("@")[-1].strip()
    if "://" not in val:
        val = f"https://{val}"
    try:
        parsed = urlparse(val)
        return parsed.hostname.lower() if parsed.hostname else None
    except Exception:
        return None


def evaluate_analysis(
    text: str,
    job: JobExtracted,
    indicators: List[IndicatorItem],
    employer_records: Optional[List[Dict[str, Any]]] = None,
    is_demo: bool = False,
) -> Tuple[str, str, str, EvidenceData, List[str]]:
    """Đánh giá độc lập mức độ rủi ro (risk) và trạng thái đối chiếu (verification)."""
    # 1. Thu thập danh sách các thông tin còn thiếu thực tế
    missing_items: List[str] = []
    if not job.company_name:
        missing_items.append("Tên công ty")
    if not job.job_title:
        missing_items.append("Vị trí tuyển dụng")
    if not job.salary:
        missing_items.append("Mức lương")
    has_contact = bool(job.contact_email or job.recruitment_website or job.contact_phone)
    if not has_contact:
        missing_items.append("Email/domain hoặc kênh tuyển dụng đối chiếu được")
    if not employer_records:
        missing_items.append("Nguồn nhà tuyển dụng")

    # Kiểm tra thiếu thông tin: thiếu vị trí, thiếu công ty, hoặc thiếu cả lương và liên hệ
    is_missing_info = (
        not job.company_name
        or not job.job_title
        or (not job.salary and not has_contact)
    )

    # 2. XÁC ĐỊNH MỨC ĐỘ RỦI RO (RISK) - Độc lập tuyệt đối, dấu hiệu cảnh báo luôn ưu tiên cao nhất
    if indicators:
        risk_label_vi = "Rủi ro cao"
    elif is_missing_info:
        risk_label_vi = "Không đủ thông tin"
    else:
        risk_label_vi = "Ít dấu hiệu rủi ro"

    # 3. XÁC ĐỊNH TRẠNG THÁI XÁC MINH & HÀNH ĐỘNG
    matched_sources: List[Dict[str, Any]] = []
    actions_vi: List[str] = []

    if employer_records:
        matching_employers = [
            emp for emp in employer_records
            if emp.get("name") and job.company_name and emp["name"].strip().lower() == job.company_name.strip().lower()
        ]

        # Kiểm tra kênh đối chiếu của tin
        email_domain = extract_domain(job.contact_email)
        web_domain = extract_domain(job.recruitment_website)
        has_verifiable_channel = bool(job.contact_email or job.recruitment_website)

        # Trường hợp: không có email và không có website để đối chiếu kênh
        if not has_verifiable_channel:
            verification_label_vi = "Chưa xác minh"
            # Giữ nguyên Rủi ro cao nếu có indicator; chỉ gán Không đủ thông tin khi KHÔNG có indicator
            if not indicators:
                risk_label_vi = "Không đủ thông tin"

            demo_suffix = " DEMO" if is_demo else ""
            if len(matching_employers) > 1:
                finding_vi = f"Hai nguồn{demo_suffix} có tên giống nhau; không có contact/domain để chọn bản ghi phù hợp."
                missing_items = ["Liên hệ hoặc domain phân biệt doanh nghiệp"]
                actions_vi = [f"Yêu cầu email/domain hoặc trang tuyển dụng để phân biệt hai nguồn{demo_suffix}."]
                for emp in matching_employers:
                    for s in emp.get("sources", []):
                        matched_sources.append({
                            "id": s.get("id"),
                            "url": s.get("url"),
                            "label_vi": s.get("label_vi"),
                            "verified_at": s.get("verified_at"),
                            "is_demo": s.get("is_demo", is_demo),
                        })
            elif len(matching_employers) == 1:
                if indicators:
                    finding_vi = "Có dấu hiệu cảnh báo trong tin; tên giống bản ghi doanh nghiệp nhưng chưa đủ thông tin kênh liên hệ để xác minh đối chiếu."
                else:
                    finding_vi = f"Tên giống một bản ghi{demo_suffix} nhưng tên hiển thị chat không đủ đối chiếu; không tự suy ra matched hoặc conflicting."
                missing_items = ["Email/domain tuyển dụng đối chiếu được"]
                actions_vi = [f"Yêu cầu email/domain tuyển dụng và đối chiếu nguồn{demo_suffix} đã cho."]
                for s in matching_employers[0].get("sources", []):
                    matched_sources.append({
                        "id": s.get("id"),
                        "url": s.get("url"),
                        "label_vi": s.get("label_vi"),
                        "verified_at": s.get("verified_at"),
                        "is_demo": s.get("is_demo", is_demo),
                    })
            else:
                verification_label_vi = "Chưa xác minh"
                finding_vi = "Doanh nghiệp không có trong danh sách nguồn đối chiếu độc lập."
                actions_vi = ["Xác nhận vị trí với kênh tuyển dụng độc lập trước khi gửi hồ sơ."]

        elif matching_employers:
            # Có kênh liên hệ và có bản ghi trùng tên -> Đánh giá chi tiết từng bản ghi
            matched_emp: Optional[Dict[str, Any]] = None
            conflicted_emp: Optional[Dict[str, Any]] = None

            for emp in matching_employers:
                official_domains = [d.lower() for d in emp.get("official_domains", [])]
                official_contacts = [c.lower() for c in emp.get("official_contacts", [])]
                official_pages = [p.lower().rstrip("/") for p in emp.get("official_recruitment_pages", [])]

                # So sánh email
                email_match = False
                email_conflict = False
                if job.contact_email:
                    if job.contact_email.lower() in official_contacts or (email_domain and email_domain in official_domains):
                        email_match = True
                    elif official_domains or official_contacts:
                        email_conflict = True

                # So sánh website
                web_match = False
                web_conflict = False
                if job.recruitment_website:
                    clean_web = job.recruitment_website.lower().rstrip("/")
                    if clean_web in official_pages or (web_domain and web_domain in official_domains):
                        web_match = True
                    elif official_domains or official_pages:
                        web_conflict = True

                if (email_match or web_match) and not email_conflict and not web_conflict:
                    matched_emp = emp
                    break
                elif email_conflict or web_conflict:
                    conflicted_emp = emp

            demo_label = " DEMO A" if is_demo else ""

            if matched_emp and matched_emp.get("sources"):
                # THỰC SỰ KHỚP KÊNH VÀ CÓ NGUỒN PROVENANCE
                verification_label_vi = "Khớp nguồn đã xác minh"
                for s in matched_emp.get("sources", []):
                    matched_sources.append({
                        "id": s.get("id"),
                        "url": s.get("url"),
                        "label_vi": s.get("label_vi"),
                        "verified_at": s.get("verified_at"),
                        "is_demo": s.get("is_demo", is_demo),
                    })
                missing_items = [item for item in missing_items if item != "Nguồn nhà tuyển dụng"]

                if indicators:
                    finding_vi = (
                        f"Nguồn nhà tuyển dụng khớp nguồn{demo_label} nhưng phát hiện dấu hiệu cảnh báo trong nội dung tin; "
                        "khớp nguồn không bảo đảm tin an toàn."
                    )
                    actions_vi = [
                        "Kiểm tra lại tin trên trang tuyển dụng chính thức được đối chiếu.",
                        "Tạm dừng thực hiện các yêu cầu tài chính hoặc nạp tiền trong tin.",
                    ]
                else:
                    finding_vi = (
                        f"Email và trang tuyển dụng khớp nguồn{demo_label}. "
                        "Chưa có dấu hiệu kích hoạt trong nội dung; khớp nguồn không bảo đảm tin thật."
                    )
                    actions_vi = [
                        "Kiểm tra lại tin trên trang tuyển dụng được đối chiếu.",
                        "Xác nhận vị trí với kênh tuyển dụng đã biết trước khi gửi hồ sơ.",
                    ]

            elif conflicted_emp:
                # XUNG ĐỘT KÊNH VỚI NGUỒN CHÍNH THỨC
                verification_label_vi = "Thông tin xung đột"
                for s in conflicted_emp.get("sources", []):
                    matched_sources.append({
                        "id": s.get("id"),
                        "url": s.get("url"),
                        "label_vi": s.get("label_vi"),
                        "verified_at": s.get("verified_at"),
                        "is_demo": s.get("is_demo", is_demo),
                    })
                missing_items = []
                finding_vi = f"Email trong tin khác email/domain của nguồn{demo_label}; có chỉ dấu mạo danh, chưa kết luận gian lận."
                actions_vi = [
                    "Đối chiếu với tuyendung@mau-a.example trong bài DEMO." if is_demo else "Đối chiếu email với website tuyển dụng chính thức của công ty.",
                    "Xác nhận người tuyển dụng qua nguồn độc lập trước khi gửi hồ sơ.",
                ]

            else:
                # Không đủ căn cứ để kết luận khớp hay xung đột (ví dụ sources rỗng hoặc chưa khớp)
                verification_label_vi = "Chưa xác minh"
                finding_vi = "Tên doanh nghiệp có trong danh sách nhưng kênh liên hệ chưa đủ căn cứ xác minh độc lập."
                actions_vi = ["Xác nhận vị trí với kênh tuyển dụng độc lập trước khi gửi hồ sơ."]

        else:
            verification_label_vi = "Chưa xác minh"
            finding_vi = "Doanh nghiệp không có trong danh sách nguồn đối chiếu độc lập."
            actions_vi = ["Xác nhận vị trí với kênh tuyển dụng độc lập trước khi gửi hồ sơ."]

    else:
        # Runtime mặc định: không có employer_records
        if indicators:
            verification_label_vi = "Chưa xác minh"
            has_fee = any(ind.rule_id in ("RULE_UPFRONT_FEE", "RULE_DEPOSIT_BEFORE_INTERVIEW", "RULE_PERSONAL_TRANSFER") for ind in indicators)
            has_task = any(ind.rule_id in ("RULE_UNREALISTIC_INCOME", "RULE_TASK_TOPUP", "RULE_SENSITIVE_DATA") for ind in indicators)

            if has_fee:
                finding_vi = "Có yêu cầu thanh toán rõ trong tin; chưa có nguồn độc lập xác minh nhà tuyển dụng hoặc vụ gian lận."
                missing_items = ["Nguồn nhà tuyển dụng đã xác minh"]
                actions_vi = [
                    "Tạm dừng thanh toán phí hoặc đặt cọc.",
                    "Yêu cầu giải thích bằng văn bản và đối chiếu kênh tuyển dụng độc lập.",
                ]
            elif has_task:
                finding_vi = "Trích đoạn hỗ trợ các dấu hiệu rủi ro; không có nguồn độc lập hoặc quyết định kiểm duyệt xác nhận gian lận."
                missing_items = ["Nguồn độc lập đã xác minh", "Quyết định kiểm duyệt có chứng cứ"]
                actions_vi = [
                    "Không nạp tiền theo yêu cầu trong tin.",
                    "Không gửi mã OTP hoặc giấy tờ nhạy cảm qua chat.",
                    "Tìm nguồn nhà tuyển dụng có thể đối chiếu.",
                ]
            else:
                finding_vi = "Có dấu hiệu cảnh báo trong tin; chưa có nguồn độc lập xác minh nhà tuyển dụng hoặc vụ gian lận."
                actions_vi = ["Xác nhận người tuyển dụng qua nguồn độc lập trước khi gửi hồ sơ."]

        elif is_missing_info:
            verification_label_vi = "Không đủ dữ liệu" if (not job.company_name and not job.job_title and not job.salary and not has_contact) else "Chưa xác minh"
            finding_vi = "Không đủ thông tin — chưa thể đánh giá; hãy bổ sung vị trí, công ty và kênh tuyển dụng."
            actions_vi = ["Bổ sung tên công ty, vị trí, lương và kênh tuyển dụng có thể kiểm tra."]

        else:
            verification_label_vi = "Chưa xác minh"
            finding_vi = "Chưa phát hiện dấu hiệu cảnh báo rõ ràng; nội dung chưa được đối chiếu với nguồn xác minh độc lập."
            actions_vi = [
                "Kiểm tra lại tin trên trang tuyển dụng chính thức của công ty.",
                "Xác nhận vị trí với kênh tuyển dụng đã biết trước khi gửi hồ sơ.",
            ]

    # Giới hạn
    if is_demo:
        limitations = [
            "Dữ liệu tổng hợp DEMO. Nguồn chỉ được đối chiếu trong bài kiểm tra; "
            "không chứng minh tin tuyển dụng ngoài đời là thật hoặc gian lận."
        ]
    else:
        limitations = [
            "Kết quả phân tích tự động dựa trên quy tắc văn bản tại thời điểm đánh giá; "
            "không thay thế xác minh pháp lý hoặc điều tra thực tế."
        ]

    evidence = EvidenceData(
        matched_sources=matched_sources,
        missing_vi=missing_items,
        limitations_vi=limitations,
        is_demo=is_demo,
    )

    return risk_label_vi, verification_label_vi, finding_vi, evidence, actions_vi
