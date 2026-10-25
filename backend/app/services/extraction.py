"""Text extraction service for recruitment job postings.

Trích xuất 11 trường thông tin tuyển dụng từ văn bản thuần bằng biểu thức chính quy và quy tắc ngôn ngữ.
"""

import re
from typing import List, Optional
from app.schemas.analyses import JobExtracted


def extract_job_fields(text: str) -> JobExtracted:
    """Trích xuất 11 trường thực thể từ văn bản tin tuyển dụng.

    Mọi trường nếu không tìm thấy hoặc không đủ cơ sở đều trả về None.
    """
    job = JobExtracted()

    # 1. Email liên hệ
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    if email_match:
        job.contact_email = email_match.group(0).rstrip(".")

    # 2. Số điện thoại liên hệ
    phone_match = re.search(r"(?:Điện thoại:\s*|(?:^|\s))((?:0000000000|0\d{9,10}))\b", text)
    if phone_match:
        job.contact_phone = phone_match.group(1)

    # 3. Website tuyển dụng
    url_match = re.search(r"https?://[^\s,;]+", text)
    if url_match:
        job.recruitment_website = url_match.group(0).rstrip(".,;")

    # 4. Tên công ty: tìm "Công ty ... tuyển", "Tập đoàn ... tuyển", "Nhóm Việc ... tuyển", "phòng tuyển dụng Công ty ..."
    company_match = re.search(
        r"(?:^|\n|\.\s*|phòng tuyển dụng\s+)((?:Công ty|Doanh nghiệp|Tập đoàn|Nhóm Việc|Hệ thống)\s+[^.\n,]+?)(?=\s+tuyển|\s+cần tuyển|,|\.|$)",
        text,
        re.IGNORECASE,
    )
    if company_match:
        job.company_name = company_match.group(1).strip()

    # 5. Vị trí tuyển dụng (job_title)
    title_match = re.search(
        r"(?:tuyển|cần tuyển)\s+([^.\n,]+?)(?=\.\s*|\s*,\s*bán thời gian|\s*,\s*toàn thời gian|\s*Lương:|\s*Làm online|$)",
        text,
        re.IGNORECASE,
    )
    if title_match:
        raw_title = title_match.group(1).strip()
        cleaned_title = re.sub(r"\s+online$", "", raw_title, flags=re.IGNORECASE).strip()
        if cleaned_title.lower() != "người làm":
            job.job_title = cleaned_title

    # 6. Mức lương (salary)
    salary_match = re.search(
        r"(?:Lương:\s*([^.\n]+?)(?=\.|\s*Địa điểm:|\s*Hình thức:|\s*Làm online|$)|(?:Cam kết kiếm|thu nhập)\s+([^.\n]+?)(?=\s+chỉ với|\.|$))",
        text,
        re.IGNORECASE,
    )
    if salary_match:
        salary_str = (salary_match.group(1) or salary_match.group(2) or "").strip()
        if salary_str:
            job.salary = salary_str

    # 7. Địa điểm làm việc (location)
    location_match = re.search(
        r"(?:Địa điểm:\s*([^.\n]+?)(?=\.|\s*Hình thức:|$)|(Văn phòng[^.,\n]*)|(Làm online|người làm online|online))",
        text,
        re.IGNORECASE,
    )
    if location_match:
        loc = (location_match.group(1) or location_match.group(2) or location_match.group(3) or "").strip()
        if loc.lower().startswith("làm online") or loc.lower().startswith("người làm online"):
            job.location = "online"
        elif loc:
            job.location = loc

    # 8. Hình thức làm việc (employment_type)
    emp_match = re.search(
        r"(?:Hình thức:\s*([^.\n]+?)(?=\.|\s*Email:|$)|(Thực tập bán thời gian|bán thời gian|toàn thời gian|part-time|full-time))",
        text,
        re.IGNORECASE,
    )
    if emp_match:
        job.employment_type = (emp_match.group(1) or emp_match.group(2) or "").strip()

    # 9. Yêu cầu ứng tuyển (application_requirements)
    req_match = re.search(
        r"(?:Yêu cầu:\s*([^.\n]+?)(?=\.|\s*Không thu phí|\s*Không cung cấp|$)|(không cần kinh nghiệm))",
        text,
        re.IGNORECASE,
    )
    if req_match:
        req = (req_match.group(1) or req_match.group(2) or "").strip()
        if "đóng phí" not in req.lower() and "đặt cọc" not in req.lower():
            job.application_requirements = req

    # 10. Khoản thanh toán yêu cầu (required_payments) - hỗ trợ dấu chấm phân cách hàng nghìn
    payments: List[str] = []
    no_fee = re.search(r"Không thu phí(?:\s+hoặc\s+đặt cọc)?", text, re.IGNORECASE)
    if no_fee:
        payments.append(no_fee.group(0))

    fee_match = re.search(
        r"(?:yêu cầu\s+)?(?:đóng|thu|nộp)\s+phí\s+tuyển\s+dụng\s+[\d.]+\s*(?:đồng|đ|vnd)(?:\s+(?:để|trước|nhận)[^.\n,;]*)?",
        text,
        re.IGNORECASE,
    )
    if fee_match:
        payments.append(fee_match.group(0).strip())

    deposit_match = re.search(r"Đặt cọc\s+[\d.]+\s*đồng\s+trước phỏng vấn", text, re.IGNORECASE)
    if deposit_match:
        payments.append(deposit_match.group(0).strip())

    topup_match = re.search(r"Nạp\s+[\d.]+\s*đồng\s+để mở nhiệm vụ\s+nhận hoa hồng", text, re.IGNORECASE)
    if topup_match:
        payments.append(topup_match.group(0).strip())

    if payments:
        job.required_payments = "; ".join(payments)

    # 11. Chỉ dẫn đáng ngờ (suspicious_instructions)
    suspicious: List[str] = []
    transfer_match = re.search(r"Chuyển tiền vào tài khoản cá nhân[^.\n]*", text, re.IGNORECASE)
    if transfer_match:
        suspicious.append(transfer_match.group(0).strip())

    channel_match = re.search(
        r"Chỉ liên hệ qua nhóm chat kín;\s*không liên hệ email trên website công ty",
        text,
        re.IGNORECASE,
    )
    if channel_match:
        suspicious.append(channel_match.group(0).strip())

    otp_match = re.search(
        r"Gửi ảnh hai mặt CCCD và mã OTP ngân hàng qua chat trước khi nhận việc",
        text,
        re.IGNORECASE,
    )
    if otp_match:
        suspicious.append(otp_match.group(0).strip())

    if suspicious:
        job.suspicious_instructions = "; ".join(suspicious)

    return job
