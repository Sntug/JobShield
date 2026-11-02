# JobShield

## Trạng thái kiểm chứng local sau review — 02/11/2026

Các chức năng R0–R5 đã được triển khai. Bộ kiểm thử, tải, smoke và restore local đã chạy lại sau review; kết quả cụ thể ở dưới. Đây chưa phải nghiệm thu deployment hoặc production, và restore local không chứng minh khả năng khôi phục database production.

- **R1 & R1.2/R1.3 (Phân tích tin tuyển dụng & Đối chiếu nguồn):** Phân tích văn bản tin tuyển dụng không cần đăng nhập (`/analyze`), xác minh doanh nghiệp qua kho nguồn kiểm duyệt (`/verify-employer`).
- **R2 (Tài khoản & Phân quyền):** Đăng ký, đăng nhập JWT HTTP-only, chuyển giao phiên phân tích khách sang tài khoản (`POST /api/v1/auth/claim-guest`), quản lý và thu hồi phiên an toàn.
- **R3 (Trích xuất đa phương thức an toàn):** Trích xuất văn bản từ ảnh PNG/JPEG/WebP (OCR Tesseract có kiểm tra MIME, giới hạn 5 MiB / 16 MP) và trích xuất URL (SSRF protection chống IP nội bộ, timeout, giới hạn tải 1 MiB).
- **R4 (Báo cáo cộng đồng & Cổng kiểm duyệt Admin):** Người dùng gửi báo cáo lừa đảo kèm chứng cứ (`/reports/new`), Admin quản lý kiểm duyệt báo cáo (`/admin/moderation`) với cơ chế optimistic locking chống conflict, tự động xuất bản cảnh báo công khai (`/warnings`) có che giấu thông tin cá nhân (PII Redaction).
- **R5 (AI Giải thích tùy chọn):** Trợ lý AI giải thích (Gemini 2.5 Flash) tuân thủ nghiêm ngặt nguyên tắc **Rule Supremacy** (không ghi đè điểm rủi ro của deterministic engine) và **AI Consent** (chỉ kích hoạt khi người dùng đồng ý).
- **R6 (Kiểm thử hồi quy, Diễn tập khôi phục & Vận hành):** kiểm thử local đã qua; release/deployment acceptance vẫn cần xác nhận với môi trường đích.

### Kết quả xác minh local

- **Backend:** 456 passed, 3 skipped (OCR CI-only), 14 warnings; gồm các bài PostgreSQL và archive restore. Từ `backend/`, `POSTGRES_TEST_URL` trỏ tới DB PostgreSQL 17 local dùng một lần, `RUN_RESTORE_DRILL_PG_TEST=1 .venv/bin/python -m pytest -q --tb=short` hoàn tất trong 23.72s.
- **Frontend:** Vitest 73/73; `npm run lint` và `npm run typecheck` đều exit 0.
- **E2E:** Playwright 25/25 với OCR thật, backend hiện tại và DB tổng hợp cô lập: `PLAYWRIGHT_PORT=3100 API_PROXY_TARGET=http://127.0.0.1:8002 npm run test:e2e` (từ `frontend/`).
- **Load:** 10 requests, 5 workers, 10,000 ký tự; 10/10 thành công cho analysis và lookup, 0% lỗi, 14 acceptance checks pass. Analysis p50/p95 0.0899/0.0950s; lookup p50/p95 0.0235/0.0328s. Rate limit cũng trả 10 lần HTTP 201 rồi HTTP 429 với `Retry-After: 60s`.
- **Smoke:** local `http://127.0.0.1:8002` đạt 8/8 khi không truyền `--sha` (header là `dev`); một SHA sai cho 7/8 và exit 1. Lần local này không xác nhận commit deployment.
- **Restore:** `pg_dump -Fc`/`pg_restore` qua test PostgreSQL local với dữ liệu tổng hợp, FK, RLS/policy và cleanup thành công; không chạy trên nguồn production.

Tài liệu vận hành và nghiệm thu:
- [Release Notes v1.0.0](docs/release-notes-v1.0.0.md)
- [Báo cáo Nghiệm thu Phát hành R6](docs/r6-release-acceptance-report.md)
- [Runbook Khôi phục Thảm họa & Rollback](docs/runbooks/disaster-recovery-and-restore.md)
- [Đặc tả API v1.0.0](docs/api.md)
- [Báo cáo Đo tải & Hiệu năng](docs/reports/r6-load-test-report.md)
- [Báo cáo Kiểm tra sau Phát hành](docs/reports/r6-post-release-smoke-report.md)

### Các lệnh kiểm thử & vận hành nhanh

```sh
# 1. Chạy hồi quy R6 (từ thư mục gốc repository)
(cd backend && .venv/bin/python -m pytest tests/test_r6_regression.py -v)

# 2. Chạy benchmark hiệu năng
(cd backend && .venv/bin/python -m pytest tests/test_performance_benchmarks.py -v)

# 3. Chạy load test CLI
backend/.venv/bin/python scripts/load-test.py --target http://127.0.0.1:8000 --concurrency 5 --total-requests 10

# 4. Diễn tập local với Docker container jobshield-test-pg (PostgreSQL 17)
./scripts/restore-drill.sh

# 5. Kiểm tra sức khỏe dịch vụ (Post-Release Smoke Test)
python3 scripts/post-release-smoke.py --url http://127.0.0.1:8000
```

`restore-drill.sh` chỉ dùng PostgreSQL container local `jobshield-test-pg`; `SOURCE_DB` có thể chọn một database trong container. Lệnh này không nhắm tới database remote.

## Trạng thái triển khai local — 28/10/2026

- `/analyze`: phân tích văn bản, lưu/đọc snapshot theo phiên khách; cảnh báo rủi ro độc lập với kết quả đối chiếu nguồn.
- R3 tại `/analyze`: nhập ảnh PNG/JPEG/WebP hoặc URL HTTP/HTTPS công khai, xem/sửa văn bản trích xuất và dán thủ công khi thất bại. API `/api/v1/extractions/{image,url}` và `/api/v1/extractions` không lưu ảnh hoặc nội dung trích xuất vào DB.
- `/verify-employer`: tra cứu công khai sáu nhóm thông tin, hiển thị căn cứ theo trường, dữ kiện thiếu và khuyến nghị; không lưu payload tra cứu/ngân hàng.
- `POST /api/v1/verifications`: validation, giới hạn body/tần suất, lỗi lược dữ liệu riêng và nguồn có provenance/revision. Kho nguồn gồm ba bảng với composite FK chống gắn sai chủ thể.
- Bộ nguồn khởi đầu thật và hướng dẫn quản trị ở [backend/data/README.md](backend/data/README.md). Fixture E2E nằm riêng trong `backend/tests/fixtures/`, không tự nạp khi app khởi động.
- R1.2/R1.3 và R3 có implementation và kiểm chứng local; deployment/UAT người dùng là bước nghiệm thu riêng, chưa được suy ra từ test tự động. Các trang quản trị vẫn thuộc mốc sau.

Backend (từ `backend/`, `DATABASE_URL` được cấu hình riêng cho đúng DB đích):

```sh
uv sync --frozen
uv run alembic upgrade head
uv run python -m app.cli.import_sources data/verified_sources.json
# Lệnh trên chỉ validate. Sau khi review đúng DB đích và dữ liệu:
uv run python -m app.cli.import_sources data/verified_sources.json --apply
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend (từ `frontend/`, `NEXT_PUBLIC_API_BASE_URL` trỏ backend tương ứng):

```sh
npm ci --include=optional
npm run dev
```

OCR local cần `tesseract` trong `PATH` và dữ liệu ngôn ngữ `vie`, `eng`; Dockerfile backend đã cài đủ. Nếu thiếu engine hoặc ảnh không đọc được, giao diện cho dán văn bản thủ công. Ảnh tối đa 5 MiB và 16 triệu pixel; kiểm tra chữ ký, cấu trúc ảnh và MIME trước OCR. Không lấy chữ từ metadata hoặc fixture DEMO.

URL chỉ hỗ trợ cổng 80/443 và IP public; kiểm tra lại từng redirect, kết nối tới IP đã duyệt và giữ hostname gốc để xác minh TLS. Nội dung tải tối đa 1 MiB; không vượt đăng nhập/CAPTCHA hoặc chạy JavaScript. Deadline HTTP ngắt cả header, body và TLS đang chờ; phân giải DNS dùng timeout của hệ điều hành. Mọi phản hồi extraction có `Cache-Control: no-store`; rate limit 10 request/60 giây/IP dùng chung cho ba endpoint, trên từng worker.

Không chạy migration hoặc import vào production chỉ vì các lệnh đã được ghi ở đây. Bản migration mới chỉ thêm ba bảng nguồn; bài downgrade xóa các bảng nguồn nên chỉ diễn tập trên DB/schema thử riêng.

## Lịch sử khởi tạo — 15/10/2026

Phần bên dưới là baseline lịch sử, không mô tả trạng thái code hiện tại.

Đọc [kế hoạch bàn giao theo tính năng](docs/superpowers/plans/2026-10-15-jobshield-delivery-plan.md), bắt đầu tại phiếu R0.1. Quy trình mới đưa Docker/CI/staging lên sớm, làm luồng phân tích văn bản cho khách trước tài khoản; mỗi phiếu có mục tiêu, tiêu chí nghiệm thu, bằng chứng và phần tự học. Đây là thay đổi kế hoạch, chưa triển khai hạ tầng hoặc chức năng.

Trạng thái ngày 15/10/2026: G1 có nền toolchain/shell; G2A có 9 tình huống tổng hợp và test fixture; ERD/quyền/vòng đời dữ liệu đã được thiết kế trong [kiến trúc](docs/architecture.md). API contract, backend/DB thật, Docker và luồng sản phẩm chưa triển khai. Kết quả lịch sử G2: backend 16 passed, Vitest 2 passed/3 todo; frontend full typecheck có lỗi file sinh trùng, lint và nhánh dependency braces còn tồn đọng. Chưa chạy lại các kiểm tra đó trong lượt thiết kế kế hoạch. [Yêu cầu sản phẩm](docs/requirements.md) giữ đích đầy đủ; [hướng dẫn môi trường](docs/development.md) giữ bài thực hành G1.

## Phân chia trách nhiệm

- `frontend/`: Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui, React Hook Form, Zod và TanStack Query. Có vị trí file cho đủ trang public, người dùng và admin; `(public)`, `(user)`, `(admin)` là route group, không xuất hiện trong URL. Chỉ trang chủ có shell; các trang sản phẩm còn là placeholder 404, chưa có bảo vệ quyền truy cập.
- `backend/`: FastAPI/Pydantic, SQLAlchemy/Alembic và PostgreSQL. Tách route, schema, model, service; dành chỗ cho trích xuất text/ảnh/URL, OCR, rule engine, risk assessment, xác minh nhà tuyển dụng, báo cáo và LLM tùy chọn.
- `frontend/tests/`, `frontend/e2e/`, `backend/tests/`: vị trí Vitest, Playwright và Pytest. Self-check môi trường và regression 404 đã chạy; ba unit test sản phẩm đang todo. Test nghiệp vụ và ranh giới API/Database/bảo mật chưa thực hiện.
- `compose.yaml`, các `Dockerfile`, `.dockerignore`: file khung chưa có cấu hình. Các `.env.example` có giá trị minh họa cho frontend/backend, không có secret thật.
- `docs/`: yêu cầu sản phẩm, kiến trúc, bài thực hành và kế hoạch bàn giao; tài liệu API còn là file khung. CI/CD, staging và theo dõi lỗi đã vào roadmap mới, chưa cấu hình. Thư mục này đang được ignore theo lựa chọn hiện có, nên tài liệu chỉ lưu local; chưa thêm Grafana/Prometheus.

## Phân bổ các entity dự kiến

| File model | Entity trong prompt |
| --- | --- |
| `backend/app/models/users.py` | users, roles |
| `backend/app/models/analyses.py` | recruitment_analyses, recruitment_sources, extracted_job_information |
| `backend/app/models/indicators.py` | risk_indicators, analysis_indicators |
| `backend/app/models/employers.py` | verified_employers, employer_sources |
| `backend/app/models/reports.py` | recruitment_reports, report_evidence, moderation_actions |
| `backend/app/models/saved_analyses.py` | saved_analyses |

Đây là phân bổ file, chưa phải schema Database. Cảnh báo công khai có vị trí route `warnings.py`; cách lưu trữ cần được thiết kế trong bước học Database/API.

## Những phần sẽ thực hiện sau

Frontend shell và backend environment đã có manifest/lockfile/runners; đây chưa phải sản phẩm chạy xuyên suốt. Backend main/routes/models/migrations còn khung, chưa có server/API/DB thật. Settings chỉ thiết lập quy ước DATABASE_URL bắt buộc/riêng tư bằng dữ liệu minh họa. docs/api.md chưa có hợp đồng; auth, seed, nghiệp vụ, OCR/LLM và Docker chưa nghiệm thu. Build frontend đã đạt cho shell/placeholder, không chứng minh các chức năng đó hoạt động.

Tailwind được nạp qua `postcss.config.mjs` và `src/app/globals.css`; shadcn Button đã có trong `src/components/ui/`. Chỉ thêm component được dùng ở giai đoạn tương ứng.

Dữ liệu sẽ đặt ở `backend/app/seed/demo_data.json` và các fixture, phải được ghi rõ là dữ liệu tổng hợp minh họa. `services/ai/` dành chỗ cho interface provider, một provider LLM cấu hình được và prompt; chưa tích hợp hoặc gửi dữ liệu ra ngoài.

Thực hiện từng phần theo yêu cầu tiếp theo của người dùng và quy tắc trong `AGENTS.md`.

## Cây thư mục khung ban đầu

Cây dưới đây mô tả lần khởi tạo. Khi bắt đầu G1 ngày 14/10/2026, `AGENTS.md` và `prompt.txt` không còn trên đĩa; quy tắc người dùng cung cấp trong chat vẫn áp dụng. Các tài liệu G1 và kế hoạch được thêm sau lần khởi tạo, không phải file ứng dụng đã triển khai.

```text
JobShield/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── .gitkeep
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── admin.py
│   │   │   │   ├── analyses.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── employers.py
│   │   │   │   ├── extraction.py
│   │   │   │   ├── reports.py
│   │   │   │   ├── risk.py
│   │   │   │   ├── saved_analyses.py
│   │   │   │   ├── statistics.py
│   │   │   │   ├── users.py
│   │   │   │   └── warnings.py
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   ├── errors.py
│   │   │   └── router.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── privacy.py
│   │   │   ├── rate_limit.py
│   │   │   ├── security.py
│   │   │   ├── upload_validation.py
│   │   │   └── url_safety.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   └── session.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── analyses.py
│   │   │   ├── employers.py
│   │   │   ├── indicators.py
│   │   │   ├── reports.py
│   │   │   ├── saved_analyses.py
│   │   │   └── users.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── analyses.py
│   │   │   ├── auth.py
│   │   │   ├── common.py
│   │   │   ├── employers.py
│   │   │   ├── extraction.py
│   │   │   ├── reports.py
│   │   │   ├── risk.py
│   │   │   ├── saved_analyses.py
│   │   │   ├── statistics.py
│   │   │   └── users.py
│   │   ├── seed/
│   │   │   ├── __init__.py
│   │   │   ├── demo_data.json
│   │   │   └── load.py
│   │   ├── services/
│   │   │   ├── ai/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── llm_provider.py
│   │   │   │   └── prompts.py
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py
│   │   │   ├── employer_verification.py
│   │   │   ├── extraction.py
│   │   │   ├── ocr.py
│   │   │   ├── report_moderation.py
│   │   │   ├── risk_assessment.py
│   │   │   ├── rule_engine.py
│   │   │   ├── statistics.py
│   │   │   └── url_extraction.py
│   │   ├── __init__.py
│   │   └── main.py
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── recruitment_cases.json
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_ai_fallback.py
│   │   ├── test_authentication.py
│   │   ├── test_authorization.py
│   │   ├── test_employer_verification.py
│   │   ├── test_extraction.py
│   │   ├── test_extraction_failures.py
│   │   ├── test_missing_information.py
│   │   ├── test_moderation.py
│   │   ├── test_privacy.py
│   │   ├── test_reports.py
│   │   ├── test_risk_assessment.py
│   │   ├── test_rule_engine.py
│   │   ├── test_upload_validation.py
│   │   └── test_url_safety.py
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile
│   ├── alembic.ini
│   └── pyproject.toml
├── docs/
│   ├── api.md
│   ├── architecture.md
│   └── development.md
├── frontend/
│   ├── e2e/
│   │   ├── admin-moderation.spec.ts
│   │   ├── analysis.spec.ts
│   │   ├── auth.spec.ts
│   │   └── reports.spec.ts
│   ├── public/
│   │   └── .gitkeep
│   ├── src/
│   │   ├── app/
│   │   │   ├── (admin)/
│   │   │   │   └── admin/
│   │   │   │       ├── employers/
│   │   │   │       │   └── page.tsx
│   │   │   │       ├── reports/
│   │   │   │       │   └── page.tsx
│   │   │   │       ├── rules/
│   │   │   │       │   └── page.tsx
│   │   │   │       ├── layout.tsx
│   │   │   │       └── page.tsx
│   │   │   ├── (public)/
│   │   │   │   ├── analysis/
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── analyze/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── login/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── register/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── safety/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── verify-employer/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── page.tsx
│   │   │   ├── (user)/
│   │   │   │   ├── dashboard/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── history/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── profile/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── reports/
│   │   │   │   │   ├── new/
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── saved/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── layout.tsx
│   │   │   ├── globals.css
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── admin/
│   │   │   │   ├── employer-form.tsx
│   │   │   │   ├── moderation-form.tsx
│   │   │   │   └── rule-form.tsx
│   │   │   ├── analysis/
│   │   │   │   ├── analysis-results.tsx
│   │   │   │   ├── evidence-list.tsx
│   │   │   │   ├── extracted-job-editor.tsx
│   │   │   │   ├── indicator-list.tsx
│   │   │   │   ├── recommended-actions.tsx
│   │   │   │   ├── recruitment-input-form.tsx
│   │   │   │   ├── risk-summary.tsx
│   │   │   │   └── verification-findings.tsx
│   │   │   ├── auth/
│   │   │   │   └── auth-form.tsx
│   │   │   ├── dashboard/
│   │   │   │   └── risk-statistics.tsx
│   │   │   ├── employers/
│   │   │   │   └── verification-form.tsx
│   │   │   ├── layout/
│   │   │   │   ├── header.tsx
│   │   │   │   └── sidebar.tsx
│   │   │   ├── profile/
│   │   │   │   └── profile-form.tsx
│   │   │   ├── reports/
│   │   │   │   ├── report-form.tsx
│   │   │   │   └── report-status.tsx
│   │   │   └── ui/
│   │   │       └── .gitkeep
│   │   ├── hooks/
│   │   │   ├── use-admin.ts
│   │   │   ├── use-analyses.ts
│   │   │   ├── use-auth.ts
│   │   │   ├── use-employers.ts
│   │   │   └── use-reports.ts
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   ├── utils.ts
│   │   │   └── validations.ts
│   │   ├── providers/
│   │   │   ├── auth-provider.tsx
│   │   │   └── query-provider.tsx
│   │   └── types/
│   │       └── api.ts
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── recruitment-cases.ts
│   │   ├── analysis-results.test.tsx
│   │   ├── recruitment-input-form.test.tsx
│   │   ├── report-form.test.tsx
│   │   └── setup.ts
│   ├── .dockerignore
│   ├── .env.example
│   ├── Dockerfile
│   ├── components.json
│   ├── eslint.config.mjs
│   ├── next-env.d.ts
│   ├── next.config.ts
│   ├── package.json
│   ├── playwright.config.ts
│   ├── postcss.config.mjs
│   ├── tsconfig.json
│   └── vitest.config.ts
├── .env.example
├── .gitignore
├── AGENTS.md
```

## Vận hành và kiểm thử lát cắt R1.1 (Guest Text Analysis)

Lát cắt R1.1 cho phép người dùng khách phân tích văn bản tin tuyển dụng trực tiếp qua giao diện `/analyze` và API `/api/v1/analyses`.

### 1. Cấu hình môi trường (.env)

**Backend (`backend/.env`):**
```bash
# PostgreSQL kết nối chính
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/jobshield

# (Tùy chọn) PostgreSQL test container biệt lập cho integration tests
POSTGRES_TEST_URL=postgresql+psycopg://r11_review:r11_local_test@127.0.0.1:55432/jobshield_r11_review

# Allowlist các domain frontend gọi API
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001
```

**Frontend (`frontend/.env.local`):**
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 2. Khởi chạy ứng dụng

**Chạy Backend:**
```bash
cd backend
uv run alembic upgrade head
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Chạy Frontend:**
```bash
cd frontend
npm run dev
# Truy cập trình duyệt: http://localhost:3000/analyze
```

### 3. Kiểm thử tự động (Verification)

```bash
# Kiểm thử toàn bộ Backend (unit + API + rule engine + migrations + test DB container):
cd backend && uv run pytest

# Kiểm thử Frontend Unit (Vitest) và Lint / Typecheck:
cd frontend && npm test && npm run lint && npm run typecheck

# Kiểm thử E2E Browser (Playwright):
cd frontend && npm run test:e2e
```

### 4. Dọn dẹp dữ liệu phiên hết hạn (Data Retention Cleanup)

- **Nguyên tắc:** Phiên khách có TTL cố định 24 giờ. Bản ghi `Analysis` kế thừa `expires_at` của phiên và bị cascade xóa khi phiên bị xóa.
- **Lệnh CLI dọn dẹp:**
  ```bash
  cd backend && python -m app.cli.cleanup
  ```
- **Lưu ý triển khai production:** Ứng dụng **không** chạy vòng lặp scheduler ngầm trong web process (để tránh lãng phí tài nguyên và xung đột đa worker). Trước khi đưa lên production, hạ tầng vận hành **bắt buộc phải cấu hình lịch chạy bên ngoài** (ví dụ: Linux `cron`, `systemd timer`, Kubernetes `CronJob`, hoặc Supabase/AWS scheduled task) để thực thi định kỳ lệnh CLI trên (khuyến nghị chạy mỗi giờ một lần: `0 * * * *`).

**Lịch dev/test:** `.github/workflows/cleanup-dev.yml` dùng lại CLI trên, dự kiến chạy **02:17 mỗi ngày giờ Việt Nam** (19:17 UTC ngày trước). GitHub chỉ kích hoạt lịch khi workflow đã có trên nhánh mặc định; lịch có thể bị trễ. Workflow này chỉ chấp nhận connection của project Supabase dev/test `JobShield` (`vleyapvlgnukcawgxozg`), không dùng connection production.

1. Sau khi người sở hữu duyệt việc cấp quyền DB cho GitHub Actions và xóa dữ liệu hết hạn, lưu connection dev/test trong Actions secret `DEV_DATABASE_URL`. Không ghi connection vào YAML hoặc log. URI phải đúng định dạng connection hiện tại: driver `postgresql+psycopg`, host `aws-0-ap-southeast-1.pooler.supabase.com`, port `5432`, database `postgres`, username `postgres.vleyapvlgnukcawgxozg`. Query parameter duy nhất được chấp nhận là `sslmode=require`, `verify-ca` hoặc `verify-full`; nếu không có thì workflow bật TLS bằng `PGSSLMODE=require`.
2. Khi workflow khả dụng trong Actions, chọn **Cleanup expired guest sessions (dev) → Run workflow** và để `purge` tắt. Lần chạy này chỉ xác minh DB và đếm dữ liệu hết hạn. Thiếu secret hoặc sai DB phải làm job fail trước bước xóa.
3. Chỉ bật `purge` sau khi đã duyệt lần xóa. CLI xóa vĩnh viễn các phiên hết hạn và analysis thuộc phiên đó trong một transaction, giữ dữ liệu còn hạn. Khi lịch hoạt động, bước xóa tự chạy mỗi ngày; quyền đọc hết sau 24h, còn dữ liệu có thể chờ thêm gần 24h đến lần cleanup kế tiếp (hoặc lâu hơn nếu job trễ/thất bại).

Để nghiệm thu vận hành, ghi run URL, commit và số dòng xóa; kiểm tra dữ liệu thử đã hết hạn bị xóa và dữ liệu còn hạn vẫn tồn tại. Kiểm thử local/CI không thay thế bằng chứng lịch chạy thật. Muốn dừng lịch, vào Actions và **Disable workflow**. Cấu hình này chưa thiết lập cleanup cho DB production.
# PR Preview tự động (Vercel + Render DEV)

Sau khi thay đổi này được push và tích hợp, PR #N dùng backend
`https://jobshield-pr-N.onrender.com`. Không nhập URL PR vào biến môi trường theo
nhánh. `VERCEL_GIT_PULL_REQUEST_ID` quyết định routing; override cũ
`NEXT_PUBLIC_API_BASE_URL` bị bỏ qua **chỉ trong Preview**. Production/local giữ API
base hiện có. Vercel phải bật **Automatically expose System Environment Variables**
(đã kiểm tra bật trên project `job-shield`).

Browser gọi API cùng origin frontend, Next rewrite `/api/v1/*` và `/ready` sang
Render. Không cần thêm origin của mỗi deployment vào CORS backend. Nhánh chưa gắn
PR trả 503 `PR_NOT_ASSOCIATED`; mở PR rồi để Vercel tạo deployment có metadata PR
(redeploy một lần nếu deployment được tạo trước PR). Không fallback về API cũ hoặc
production. Render DEV base service `JobShield` phải bật Automatic PR Previews và
giữ Docker Command trống để dùng CMD trong repo; giữ service slug `jobshield`.

Trên service DEV gốc và các PR Preview đã tồn tại, đặt **Build Filters → Included
Paths = `**`**, không có Ignored Paths. Giữ Root Directory `backend/` và các đường
dẫn Docker hiện có. Root Directory mặc định bỏ qua thay đổi ngoài backend, nên
commit chỉ sửa frontend/workflow có thể không deploy backend và làm smoke lệch
SHA vĩnh viễn; explicit filter toàn repo cho phép kích hoạt những thay đổi đó.
Sau cấu hình phải xác nhận một push chỉ sửa ngoài `backend/` tự tạo deploy và
`X-Commit-SHA` của backend bắt kịp HEAD, không dùng manual deploy làm bằng chứng.
Đổi lại, DEV/Preview sẽ build backend cả khi chỉ sửa frontend hoặc tài liệu.

Request xác minh dùng `credentials: "same-origin"` để giữ cookie truy cập Vercel
Preview; không gửi cookie tới API khác origin và không thêm guest token. Không
dùng `omit` cho request cùng origin trên Preview đang bật Deployment Protection.

Docker startup chỉ tự bootstrap khi nhận đúng DEV PR hostname, `IS_PULL_REQUEST=true`
và đúng Supabase DEV project `vleyapvlgnukcawgxozg`, session pooler port 5432, TLS.
Mỗi PR dùng schema `preview_pr_N`: advisory lock có timeout, migration Alembic tới
head và import `backend/data/verified_sources.json` trong transaction trước khi
Uvicorn nhận request. Khởi động lại không nhân đôi nguồn; sửa nguồn phải tăng
revision. Không nhập fixture tổng hợp E2E vào cloud.

`search_path` được đặt và xác minh mỗi lần mượn connection; không fallback public.
Supavisor thực tế bỏ qua startup `options`, nên không thay connect hook bằng tham
số đó. Schema riêng giúp tránh PR ghi nhầm dữ liệu của nhau, nhưng **không phải
phân quyền DB riêng**: các Preview vẫn dùng cùng credential DEV. Không cấp quyền
anon hoặc expose schema PR qua Data API. Production và local không tự migration.

`/healthz` và `/` chỉ kiểm tra process. `/ready` phải xác nhận revision Alembic và
các cột model dùng được; thiếu schema trả 503. Render DEV nên đặt health check
`/ready`. CI Playwright chạy production build qua cùng đường proxy. Workflow
`Deployed Preview Smoke` chờ frontend deployment thành công, kiểm tra backend cùng
SHA, schema current, nguồn FPT/provenance và tạo/đọc analysis bằng guest token.
Nó chạy script tin cậy từ default branch, không chạy code PR với token GitHub;
không cần Render/Vercel API token mới. Workflow cần có trên default branch để hoạt
động theo bản mới nhất; ở PR cài đặt lần đầu, workflow dùng commit checker đã
review được pin SHA bất biến thay vì skip hoặc chạy script từ PR chưa được tin cậy.
Sau khi cài trên default branch, workflow tự dùng checker của default branch.
Các deployment Render/Production chỉ chạy bước định tuyến và hiện “Ignored
deployment event”. Bảng Actions trên PR có thể chỉ hiện lượt deployment mới nhất,
nên đổi tên job không đủ để giữ kết quả Vercel. Kết quả chức năng được ghi riêng
vào commit status **`JobShield / Preview smoke`**: pending trước kiểm tra, success
chỉ khi toàn bộ smoke qua, failure khi smoke lỗi. Chỉ event Vercel Preview đã
xác minh thuộc HEAD của PR cùng repo được ghi status; Render không cập nhật nó.
Job smoke có quyền `statuses: write` để ghi kết quả này. Nếu job bị hủy giữa chừng,
status giữ pending; mở link Details để xem lượt chạy thực tế.
Các lượt Vercel cùng SHA được xếp hàng; deployment ID đã ghi trong status ngăn
rerun deployment cũ ghi đè kết quả của deployment mới hơn.

Test local qua proxy (backend riêng phải chạy và DB test đã migrate/nạp fixture):

```sh
cd frontend
API_PROXY_TARGET=http://127.0.0.1:8000 PLAYWRIGHT_PORT=3001 npm run test:e2e
```

Schema PR được giữ lại khi đóng PR; không tự DROP hoặc sao chép dữ liệu public.
Chỉ dọn schema DEV cụ thể sau khi không còn cần dữ liệu thử. Render Free vẫn có
cold start; smoke chờ tối đa 300 giây rồi báo lỗi thay vì báo xanh giả. Nếu bật
Vercel Deployment Protection, smoke từ Actions cần cơ chế truy cập được phê duyệt;
không tắt protection chỉ để làm test xanh.

Với Preview đang bật Vercel Authentication: tại Deployment Protection → Protection
Bypass for Automation → Add Secret, người quản trị tự tạo/copy secret. Lưu cùng giá
trị trong GitHub repository → Settings → Secrets and variables → Actions → New
repository secret, tên `VERCEL_AUTOMATION_BYPASS_SECRET`. Không dán secret vào chat,
source, URL hoặc `NEXT_PUBLIC_*`. Redeploy Preview sau khi tạo/đổi secret. Checker
chỉ gửi header `x-vercel-protection-bypass` tới host HTTPS Preview được phép,
không gửi tới GitHub API hoặc theo redirect; 401 báo lỗi ngay để sửa quyền truy cập.
