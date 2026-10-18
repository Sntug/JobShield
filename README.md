# JobShield — cấu trúc dự án

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
