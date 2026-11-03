# JobShield

**Đánh giá rủi ro tin tuyển dụng trước khi ứng tuyển.**

JobShield giúp người tìm việc nhận diện dấu hiệu lừa đảo trong tin tuyển dụng, đối chiếu thông tin nhà tuyển dụng với nguồn đã kiểm duyệt và xem cảnh báo từ cộng đồng. Bạn có thể phân tích tin và tra cứu nhà tuyển dụng mà không cần tài khoản.

[Chạy thử trên máy](#chạy-trên-máy) · [Kiểm thử](#kiểm-thử) · [Vận hành](#vận-hành)

## Tính năng

| Tính năng | Bạn có thể làm gì? |
| --- | --- |
| Phân tích tin tuyển dụng | Dán văn bản, tải ảnh hoặc nhập URL công khai. Kiểm tra nội dung trích xuất trước khi xem mức rủi ro, dấu hiệu phát hiện và bước xác minh tiếp theo. |
| Đối chiếu nhà tuyển dụng | So sánh thông tin liên hệ và thông tin doanh nghiệp với nguồn đã kiểm duyệt. Xem nguồn và dữ kiện còn thiếu cho từng mục. |
| Giải thích bằng AI | Bật khi cần và đồng ý trước khi gửi nội dung đến nhà cung cấp AI. AI bổ sung giải thích; bộ quy tắc vẫn quyết định mức rủi ro. |
| Báo cáo cộng đồng | Đăng nhập để gửi báo cáo kèm chứng cứ và theo dõi trạng thái. Cảnh báo công khai được kiểm duyệt và lược bỏ thông tin cá nhân. |
| Lưu kết quả | Đăng nhập để lưu và xem lại kết quả phân tích. |

> Kết quả là căn cứ để kiểm tra thêm. Thông tin trùng khớp với nguồn chính thức không xác nhận người đăng hoặc tính an toàn của một tin cụ thể. Hãy liên hệ doanh nghiệp qua kênh chính thức trước khi chuyển tiền hoặc cung cấp giấy tờ cá nhân.

## Chạy trên máy

**Cần có:** Git, [uv](https://docs.astral.sh/uv/), Node.js từ 24.8 đến dưới 25, npm 11 và PostgreSQL. CI dùng PostgreSQL 17. Nếu muốn đọc ảnh, cài thêm Tesseract với dữ liệu ngôn ngữ `vie` và `eng`.

1. **Lấy mã nguồn và cấu hình.** Tạo một cơ sở dữ liệu PostgreSQL riêng cho phát triển. Sửa `DATABASE_URL` trong `backend/.env` để trỏ đến cơ sở dữ liệu đó.

   ```sh
   git clone https://github.com/Sntug/JobShield.git
   cd JobShield
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env.local
   ```

2. **Chạy API.** Từ thư mục gốc, mở terminal cho backend:

   ```sh
   cd backend
   uv python install
   uv sync --frozen
   uv run alembic upgrade head
   uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

3. **Chạy giao diện.** Từ thư mục gốc, mở terminal thứ hai:

   ```sh
   cd frontend
   npm ci --include=optional
   npm run dev
   ```

4. **Thử phân tích.** Mở [trang phân tích](http://localhost:3000/analyze) và dán một tin tuyển dụng mẫu. Bạn cũng có thể thử [tra cứu nhà tuyển dụng](http://localhost:3000/verify-employer), xem [cảnh báo cộng đồng](http://localhost:3000/safety) hoặc mở [tài liệu API tương tác](http://127.0.0.1:8000/docs).

Cơ sở dữ liệu mới chưa có nguồn đối chiếu. Để thử tra cứu với dữ liệu thật, xem [cách kiểm tra và nhập nguồn](backend/data/README.md#kiểm-tra-và-nhập-nguồn). AI mặc định tắt; khi cần thử Gemini, đặt `AI_PROVIDER=gemini` và `AI_API_KEY` trong `backend/.env`. Chỉ đặt cấu hình công khai như `NEXT_PUBLIC_API_BASE_URL` trong `frontend/.env.local`.

## Kiến trúc

| Thành phần | Vai trò |
| --- | --- |
| [`frontend/`](frontend/) | Next.js App Router, React, TypeScript và Tailwind CSS; giao diện cho khách, người dùng và quản trị viên. |
| [`backend/`](backend/) | FastAPI, Pydantic và Tesseract; API `/api/v1`, trích xuất nội dung, chấm điểm theo quy tắc và đối chiếu nguồn. |
| [`backend/alembic/`](backend/alembic/) | Migration PostgreSQL. Backend truy cập dữ liệu qua SQLAlchemy. |

## Kiểm thử

Chạy các lệnh sau từ thư mục gốc sau khi cài dependency:

```sh
(cd backend && uv run pytest)
(cd frontend && npm run lint && npm run typecheck && npm test)
```

Kiểm thử tích hợp PostgreSQL cần `POSTGRES_TEST_URL` trỏ đến cơ sở dữ liệu thử nghiệm riêng. Với Playwright, dùng backend đang chạy cùng cơ sở dữ liệu kiểm thử đã migrate và nạp dữ liệu mẫu theo [workflow CI](.github/workflows/ci.yml). Đảm bảo hai cổng 3100 và 3101 còn trống.

```sh
cd frontend
npm run playwright:install
API_PROXY_TARGET=http://127.0.0.1:8000 PLAYWRIGHT_PORT=3100 npm run test:e2e
```

## Vận hành

- **Kiểm tra dịch vụ:** `/healthz` xác nhận tiến trình đang chạy; `/ready` kiểm tra cả kết nối cơ sở dữ liệu và schema. Dùng [script smoke](scripts/post-release-smoke.py) với `--url` và `--sha` để kiểm tra bản triển khai cụ thể.
- **Preview cho pull request:** Vercel chuyển tiếp API tới Render DEV tương ứng; mỗi PR dùng một schema riêng trên cơ sở dữ liệu DEV. [Workflow preview smoke](.github/workflows/preview-smoke.yml) kiểm tra frontend và backend cùng commit.
- **Phiên khách:** Quyền truy cập hết hạn sau 24 giờ. Dữ liệu hết hạn được xóa khi tác vụ cleanup chạy. [Workflow dev](.github/workflows/cleanup-dev.yml) chỉ dùng cho DEV; production cần lịch riêng để chạy `uv run python -m app.cli.cleanup` từ `backend/`.
- **Đo tải và khôi phục:** Dùng [script đo tải](scripts/load-test.py) trên môi trường thử nghiệm và [script diễn tập khôi phục](scripts/restore-drill.sh) với PostgreSQL local. Kết quả local không xác nhận khả năng khôi phục dữ liệu production.

[Nhật ký kiểm chứng và cấu hình Preview trước đây](https://github.com/Sntug/JobShield/blob/6192e00d33de6646bbe1c006d5edbf1c47a7948c/README.md).

## Đóng góp

Khi báo lỗi, ghi các bước tái hiện, kết quả mong đợi và kết quả thực tế. Hãy dùng dữ liệu giả lập hoặc đã ẩn thông tin cá nhân. Khi gửi pull request, mô tả thay đổi và các kiểm tra đã chạy.
