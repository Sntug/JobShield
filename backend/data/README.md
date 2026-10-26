# Nguồn đối chiếu được quản trị

`verified_sources.json` là bộ nguồn thật khởi đầu, được kiểm tra ngày 26/10/2026 bởi Codex và đối chiếu độc lập bởi Antigravity. Hiện chỉ có một doanh nghiệp: **FPT Software Company Limited**, cùng tên thương hiệu FPT Software.

Nguồn chính chủ: [FPT Software — Contact us](https://fptsoftware.com/contact-us). Phạm vi được quan sát:

- Trang công bố tên doanh nghiệp ở footer và tên thương hiệu.
- Mục Human Resources công bố **Recruitment@fpt.com**.
- Link “Find Career Opportunities” trỏ [career.fpt-software.com](https://career.fpt-software.com/).

Không suy số đăng ký BR No thành mã số thuế khi nguồn không nói rõ; không xác minh toàn domain `fpt.com` cho một công ty thành viên; không thêm nguồn mạng xã hội/tài khoản ngân hàng tưởng tượng. Khớp các dữ kiện này không xác nhận một tin tuyển dụng cụ thể hoặc bảo đảm an toàn.

## Kiểm tra và nhập nguồn

Từ `backend/`, với `DATABASE_URL` của môi trường đích đã cấu hình riêng:

```sh
# Chỉ validate, không kết nối DB:
uv run python -m app.cli.import_sources data/verified_sources.json
# Áp dụng migration vào đúng DB dev trước khi nhập lần đầu:
uv run alembic upgrade head
# Chỉ sau khi đã review target và nguồn:
uv run python -m app.cli.import_sources data/verified_sources.json --apply
```

Importer chỉ dành cho người vận hành tin cậy, không nối với upload/API public. Toàn manifest được validate trước khi ghi; transaction rollback khi có lỗi. Không đưa secret vào manifest hoặc command line.

Mỗi source cần UUID ổn định, employer tương ứng, URL public HTTP/HTTPS, nhãn và trích đoạn đã lược riêng tư, người/quy trình đã kiểm chứng, ngày kiểm chứng có timezone, revision dương, và ít nhất một claim. Claim có `field`, `value`, `assertion` (`supports`/`refutes`). `domain` chỉ được khai báo sau khi xác minh độc lập; không tự sinh từ một mailbox/profile. Claim phủ định phải có bằng chứng trực tiếp đúng chủ thể, không thay việc “không có trong danh sách”.

Bank value có đủ bank_name/account_number/account_holder để chuẩn hóa rồi băm; không lưu tuple thô và không được chứa số/chủ tài khoản trong phần source public. Hash không phải mã hóa; không coi kho claim là dữ liệu được phép công khai.

## Cập nhật và thu hồi

Giữ source UUID/employer UUID, tăng `source_revision`, sửa claims/evidence đã review rồi nhập lại. Không thay source sang employer khác. Nhập lại cùng revision bị từ chối để tránh ghi đè âm thầm. Thu hồi bằng `is_active: false` và tăng revision; tất cả claim từ nguồn bị loại khỏi runtime. `valid_until` tùy chọn; nguồn hết hạn không còn làm căn cứ. Snapshot analysis cũ vẫn giữ ngày/revision/nội dung public đã sử dụng.

## Kiểm thử tách biệt

`tests/fixtures/r12_e2e_sources.json` là dữ liệu tổng hợp, chỉ dùng qua `python -m tests.seed_r12_e2e` trên DB loopback có tên bắt đầu `jobshield_r12_e2e_` hoặc `jobshield_ci_e2e`. Script từ chối DB khác. Không chạy importer production với fixture này. Ứng dụng không tự nạp bất cứ nguồn nào khi khởi động.
