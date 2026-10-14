# JobShield Implementation Plan — xây dựng theo giai đoạn và điểm dừng tự học

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task; superpowers:subagent-driven-development chỉ dùng nếu người dùng chọn cách đó. Steps use checkbox (`- [ ]`) syntax for tracking. Trong cả hai cách, các phần tự học vẫn do người dùng thực hiện; agent không giao chúng cho agent khác để làm thay.

**Goal:** Xây dựng JobShield hoạt động xuyên suốt với dữ liệu PostgreSQL, đánh giá rủi ro có giải thích, tài khoản, báo cáo và quản trị; mỗi giai đoạn kết thúc bằng một công việc tự học tạo nền tảng cần thiết cho giai đoạn kế tiếp.

**Architecture:** Giữ cấu trúc Next.js frontend và FastAPI backend hiện có. Logic trích xuất văn bản, đối chiếu dữ liệu đã cung cấp và chấm điểm thuần nằm trong service; lớp API, cơ sở dữ liệu, xác thực, nguồn bên ngoài và triển khai do người dùng xây dựng qua hướng dẫn. Đưa luồng văn bản chạy thật lên trước, sau đó mở rộng đầu vào, AI, chức năng tài khoản và kiểm duyệt; cuối cùng đóng gói toàn bộ ứng dụng bằng Docker Compose.

**Tech Stack:** Next.js, TypeScript, Tailwind CSS, shadcn/ui, React Hook Form, Zod, TanStack Query; Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL; LLM cấu hình được, OCR; Docker, Docker Compose; Pytest, frontend unit tests và Playwright. G1 đã chọn stable tương thích ARM64, ghi version exact trong manifests/lockfiles và development.md; Python 3.15.0 chỉ nằm trong backend/.venv.

**Spec ban đầu:** `/Users/sontung/Documents/GitHub/JobShield/prompt.txt`; quy tắc thực hiện: `/Users/sontung/Documents/GitHub/JobShield/AGENTS.md`. Cả hai hiện không có trên đĩa; quy tắc người dùng cung cấp trong chat vẫn áp dụng. G1 có snapshot tại docs/requirements.md với provenance rõ. Lượt rà soát G1 theo yêu cầu sửa bug đã bổ sung ngoại lệ ignore riêng cho snapshot và kế hoạch để hai tài liệu có thể theo dõi trong Git, giữ ignore các tài liệu local khác.

## Global Constraints

- “All user-facing text must be in Vietnamese.”
- “Prioritize a complete, reliable MVP over unnecessary features.”
- “Development must work on: macOS Apple Silicon (ARM64).”
- “Use compatible stable versions.”
- “The application must still function without an AI API key.”
- “The score must be explainable and reproducible.”
- “Do not classify missing information as evidence of safety.”
- “User reports must not automatically become verified warnings.”
- “Never invent evidence, employer records, official domains, or external verification results.”
- “Do not assume the existence of a company proves the authenticity of a particular recruitment advertisement.”
- “Never bypass authentication, CAPTCHA, or access restrictions.”
- “Do not expose private user reports publicly.”
- “Do not use hardcoded responses to simulate backend functionality.”
- Dữ liệu minh họa phải được ghi rõ là tổng hợp; không biến doanh nghiệp giả thành nguồn xác minh thực tế.
- Theo `AGENTS.md`: Infrastructure, CI/CD, Database, API, giám sát và bảo mật chỉ được hướng dẫn; người dùng tự viết, tự chạy, tự kiểm tra. Quy tắc này áp dụng cả test, fixture hoặc script nếu chúng thực hiện những lĩnh vực đó.
- Phạm vi lúc lập kế hoạch ban đầu chỉ là tài liệu. Sau đó người dùng cho phép thực hiện G1 và hai ngoại lệ môi trường frontend/backend; Python mới nhất chỉ trong venv. Không tự triển khai hợp đồng API, Database/migration/seed, auth, provider hoặc Docker; chưa chuyển G2.

## Review Focus

1. Tin trông hợp lệ nhưng thiếu dữ kiện: hiển thị “Không đủ thông tin” khi chưa đủ cơ sở, không suy ra an toàn. Chủ sở hữu test: G4 và G5.
2. Công ty có thật nhưng liên hệ tuyển dụng khác nguồn chính thức: phân biệt xác minh doanh nghiệp với xác minh tin tuyển dụng. Chủ sở hữu test: G4, G5 và G10.
3. Người khác biết ID phân tích/báo cáo/tệp: vẫn không được đọc dữ liệu riêng tư; guest cũng không được có URL kết quả công khai mặc định. Chủ sở hữu test: G3, G5, G8 và G9.
4. Ảnh không đọc được, URL bị chặn, LLM mất kết nối: có đường sửa/dán văn bản và phân tích bằng rule; không dựng dữ liệu thành công giả. Chủ sở hữu test: G6 và G7.
5. Báo cáo thiếu bằng chứng, thao tác kiểm duyệt lặp hoặc đồng thời: không tự xuất bản cảnh báo, không ghi đè lịch sử quyết định. Chủ sở hữu test: G9 và G10.

---

## 1. Cách sử dụng kế hoạch

Đây là kế hoạch xây dựng theo giai đoạn, không phải lệnh thực thi toàn bộ `prompt.txt`. Chọn một giai đoạn, hoàn thành phần độc lập mà agent được phép làm, rồi học phần kết thúc của giai đoạn đó. Bước sau chỉ bắt đầu khi có kết quả kiểm tra của bước trước.

**A — Agent làm:** giao diện, nội dung tiếng Việt, trình bày dữ liệu đã có, logic nghiệp vụ thuần và test của chúng. Không coi việc một file nằm trong frontend là đủ để được làm: `api-client.ts`, hook gọi backend, auth provider và bảo vệ route vẫn thuộc API/bảo mật.

**U — Người dùng làm, agent hướng dẫn:** mọi schema Database/API, persistence, xác thực, phân quyền, upload/URL, OCR, LLM provider, secret, environment, Docker, giám sát và kiểm tra những ranh giới đó.

Một điểm dừng có ba trạng thái: **chưa học → đang thực hành → có bằng chứng đạt**. Không chuyển trạng thái bằng suy đoán. Nếu bước U chưa đạt, agent giải thích lỗi hoặc tiếp tục công việc A thật sự độc lập; không âm thầm dựng backend giả để vượt qua điểm dừng.

**Cách triển khai khuyến nghị:** agent trực tiếp làm phần A, người dùng trực tiếp làm phần U. Nhiều giai đoạn dùng lại kết quả dữ liệu và quyền truy cập của nhau; đổi agent cho mỗi đoạn không làm giảm các phụ thuộc này.

## 2. Trạng thái hiện tại và đầu ra cuối cùng

Snapshot lúc lập kế hoạch, trước khi thực hiện G1: đã đọc `AGENTS.md`, `prompt.txt`, `README.md` và kiểm tra cây file ngày 14/10/2026. Bảng dưới là trạng thái khung ban đầu, không phải trạng thái sau G1:

| Hạng mục | Trạng thái đã thấy | Hệ quả |
| --- | --- | --- |
| Frontend | 74 file, tất cả rỗng | Chưa có trang hay cấu hình có thể chạy |
| Backend | 89 file, tất cả rỗng | Chưa có service, API, model hoặc test thực thi |
| `docs/` trước kế hoạch này | 3 file tài liệu rỗng | Cần viết tài liệu từ nguồn yêu cầu |
| Manifest, Docker, Compose, env example | File khung rỗng | Chưa thể install/build/test/start từ cấu trúc này |
| `.codegraph/` | Không có | Bỏ qua CodeGraph; không tự tạo index |

Đích hoàn thành là một ứng dụng chạy local có frontend kết nối backend thật, dữ liệu tồn tại qua lần khởi động lại, guest phân tích được, user lưu và báo cáo được, admin kiểm duyệt được. Demo không cần key AI; mock chỉ dùng trong unit test và kiểm tra component trước khi tích hợp, không làm bằng chứng hoàn thành sản phẩm.

## 3. Bản đồ giai đoạn và phụ thuộc

| Giai đoạn | Kết quả sản phẩm | Công việc tự học cuối giai đoạn | Điều kiện tạo ra cho bước sau | Ước lượng |
| --- | --- | --- | --- | --- |
| G1. Nền tảng | Kiến trúc, phạm vi MVP, công cụ chạy tối thiểu | Environment và dependency trên ARM64 | Có runtime/test runner dùng được | 3–5 giờ |
| G2. Dữ liệu và hợp đồng | Thiết kế thống nhất giữa frontend/backend | Schema Database, hợp đồng API và quyền dữ liệu | Biết lưu gì, truyền gì, ai được truy cập | 4–6 giờ |
| G3. Backend nền và tài khoản | PostgreSQL thật, đăng ký/đăng nhập thật | Migration, seed nền, authentication/authorization | Có DB, phiên truy cập và danh tính | 7–10 giờ |
| G4. Phân tích văn bản | Rule engine, điểm rủi ro và đối chiếu nguồn | API điều phối, lưu kết quả, cấu hình rule | Có luồng text → kết quả có ID thật | 6–9 giờ |
| G5. Luồng công khai | Giao diện phân tích/kết quả/xác minh hoàn chỉnh | Tích hợp frontend–backend, quyền guest và lỗi API | Sản phẩm đầu tiên chạy từ trình duyệt đến DB | 6–9 giờ |
| G6. Ảnh và URL | Đầu vào đa dạng, sửa văn bản khi trích xuất lỗi | Upload an toàn, OCR, URL extraction và SSRF | Mọi đầu vào quy về cùng luồng text | 6–9 giờ |
| G7. AI tùy chọn | Giải thích ngữ cảnh và trạng thái fallback | Provider LLM, consent, tối thiểu hóa dữ liệu, timeout | AI hỗ trợ luồng đã hoạt động độc lập | 4–7 giờ |
| G8. Không gian người dùng | Lịch sử, lưu kết quả, dashboard và hồ sơ | API dữ liệu cá nhân, pagination và phân quyền | Tài khoản có hành vi và dữ liệu riêng thật | 4–6 giờ |
| G9. Báo cáo cộng đồng | Gửi/theo dõi báo cáo và màn hình kiểm duyệt | DB/API báo cáo, bằng chứng, audit và quyền | Có quy trình đưa báo cáo tới người duyệt | 6–9 giờ |
| G10. Quản trị và cảnh báo | Quản lý nguồn/rule, thống kê, cảnh báo có chứng cứ | Admin API, xuất bản có kiểm soát và lịch sử thay đổi | MVP đầy đủ chức năng, sẵn sàng đóng gói | 5–8 giờ |
| G11. Vận hành local | Bộ kiểm tra và tài liệu chạy toàn stack | Docker image/container/volume/network/Compose, backup/restore | Hoàn tất tiêu chí nghiệm thu local | 7–10 giờ |

Tổng dự trù: **58–88 giờ**, chưa gồm thời gian chờ phản hồi hoặc sửa môi trường máy. Chia thành buổi 60–90 phút; không cần hoàn thành một giai đoạn trong một buổi. Ước lượng là thời gian làm và học, không phải cam kết tiến độ.

Quan hệ bắt buộc:

```text
G1 công cụ
  → G2 thiết kế dữ liệu/hợp đồng
    → G3 DB + danh tính
      → G4 phân tích văn bản + lưu
        → G5 giao diện tích hợp thật
          → G6 ảnh/URL → G7 AI tùy chọn
            → G8 dữ liệu cá nhân
              → G9 báo cáo/kiểm duyệt
                → G10 quản trị/cảnh báo
                  → G11 đóng gói/nghiệm thu
```

Đây là thứ tự thực hiện, không phải phụ thuộc kỹ thuật giả: G8 không cần LLM để chạy, nhưng được xếp sau G7 để hoàn thiện luồng phân tích trước khi mở rộng tài khoản. Không có key AI vẫn hoàn thành G7 bằng kiểm thử fallback. Nếu cần rút ngắn đường tới MVP, vẫn hoàn thiện hành vi G7 không-key, chưa bật provider trả phí.

Không nhóm toàn bộ API hay Docker thành một môn học tách khỏi sản phẩm: G2 học hợp đồng vì backend sắp cần nó; G4 học API vì engine đã có; G6 học SSRF vì sắp nhận URL; G11 học build image vì ứng dụng thực đã sẵn sàng đóng gói.

## 4. Bản đồ file và trách nhiệm

Tất cả đường dẫn bên dưới tính từ `/Users/sontung/Documents/GitHub/JobShield`. Bản đồ được lập từ cây file khung ban đầu; một số file toolchain và shell đã có nội dung sau G1. Giữ cấu trúc hiện có; chỉ thêm file có nhiệm vụ cụ thể trong bảng.

| Nhóm | File hiện có sẽ sửa | File mới được lên kế hoạch | Chủ sở hữu |
| --- | --- | --- | --- |
| Yêu cầu/tài liệu | `docs/architecture.md`, `docs/api.md`, `docs/development.md`, `README.md` | `docs/requirements.md`, `docs/acceptance.md` | A cho sản phẩm; U cho phần kỹ thuật tự học |
| Toolchain | `frontend/package.json`, `frontend/tsconfig.json`, `frontend/next.config.ts`, `frontend/next-env.d.ts`, `frontend/postcss.config.mjs`, `frontend/components.json`, `frontend/eslint.config.mjs`, `frontend/vitest.config.ts`, `frontend/playwright.config.ts`, `frontend/tests/setup.ts`, `backend/pyproject.toml` | Lockfile tương ứng công cụ được người dùng chọn tại G1 | U |
| DB nền | `backend/app/db/{base,session}.py`, `backend/app/models/{users,analyses,indicators,employers,reports,saved_analyses}.py`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic.ini`, `backend/app/seed/{load.py,demo_data.json}` | `backend/alembic/versions/0001_initial.py`, `backend/alembic/versions/0002_reporting.py`, `backend/app/models/warnings.py`, `backend/alembic/versions/0003_public_warnings.py` | U |
| Backend API nền | `backend/app/main.py`, `backend/app/api/{router,dependencies,errors}.py`, `backend/app/api/routes/*.py`, `backend/app/schemas/*.py`, `backend/app/core/{config,security,privacy,rate_limit}.py` | Không thêm tầng repository/service wrapper nếu chưa cần | U |
| Logic thuần | `backend/app/services/{extraction,rule_engine,risk_assessment,employer_verification,report_moderation}.py` | `backend/app/services/domain.py`, `backend/tests/test_report_transitions.py` | A; `domain.py` chỉ chứa kiểu nghiệp vụ thuần, không ORM/Pydantic/API |
| Điều phối/nguồn ngoài | `backend/app/services/{analysis,ocr,url_extraction,statistics}.py`, `backend/app/services/ai/{base,llm_provider,prompts}.py`, `backend/app/core/{upload_validation,url_safety}.py` | Chỉ thêm adapter nếu provider được chọn cần nó | U |
| Frontend trình bày | `frontend/src/app/**/{layout,page}.tsx`, `frontend/src/app/globals.css`, `frontend/src/components/{layout,analysis,employers,auth,dashboard,profile,reports,admin}/*`, `frontend/src/lib/utils.ts` | Component shadcn/ui thực sự dùng trong `frontend/src/components/ui/` | A; phần guard/auth trong layout thuộc U |
| Frontend tích hợp | `frontend/src/types/api.ts`, `frontend/src/lib/{api-client,validations}.ts`, `frontend/src/hooks/use-*.ts`, `frontend/src/providers/{query-provider,auth-provider}.tsx` | Không thêm client giả cho ứng dụng | U cho contract, request, quyền, validation ở ranh giới; A cho validation hiển thị thuần |
| Kiểm tra | `backend/tests/test_*.py`, `backend/tests/conftest.py`, `backend/tests/fixtures/recruitment_cases.json`, `frontend/tests/*.test.tsx`, `frontend/tests/fixtures/recruitment-cases.ts`, `frontend/e2e/*.spec.ts` | `frontend/e2e/employer-verification.spec.ts`, `frontend/e2e/analysis-inputs.spec.ts`, `frontend/e2e/user-dashboard.spec.ts`, `frontend/e2e/admin-management.spec.ts`, `frontend/tests/report-status.test.tsx`, `backend/tests/test_statistics.py` | A cho test thuần/component; U cho DB/API/auth/ngoại dịch vụ và chạy test chúng |
| Docker/môi trường | `frontend/Dockerfile`, `backend/Dockerfile`, `frontend/.dockerignore`, `backend/.dockerignore`, `compose.yaml`, `.env.example`, `frontend/.env.example`, `backend/.env.example` | Không CI/CD, không cloud ở MVP | U |

Các file `__init__.py` hiện có chỉ bổ sung export khi cần. Không tạo một module con chỉ để chuyển tiếp lời gọi. Các migration được đánh số ở đây là tên dự kiến; nếu người dùng dùng tên revision Alembic khác, cập nhật tài liệu theo tên thật trước khi chuyển giai đoạn.

## 5. G1 — Kiến trúc và công cụ phát triển

**Mục tiêu:** Có phạm vi thống nhất và môi trường tối thiểu để viết/chạy test, chưa khởi động toàn stack.

**Đầu vào:** File khung hiện tại, yêu cầu trong `prompt.txt`, quy tắc A/U. Không giả định máy đã có Node, Python, Docker hoặc dependency.

**Rà soát ngày 14/10/2026:** G1A và toolchain G1U đạt theo hai ngoại lệ môi trường. Frontend: typecheck đạt, Vitest 1 passed/3 todo, Chromium 2 passed; build mặc định Turbopack người dùng chạy đạt và Webpack agent chạy đạt. Backend: Python 3.15.0 chỉ trong .venv, 12 Pytest passed, manifest khớp uv.lock/30 packages compatible; env examples và lỗi missing/empty config đã kiểm tra. Python toàn máy không đổi. Đã sửa page/layout rỗng gây TS errors/HTTP 500, thêm 404 tiếng Việt, mở ignore riêng cho snapshot/kế hoạch và cập nhật tài liệu trạng thái cũ. 7 high braces frontend và lint vẫn hoãn. G1 hoàn tất mức nền tảng; chưa chuyển G2 hoặc triển khai API/Database/Docker. Source provenance/giới hạn snapshot giữ trong requirements.

Checkpoint frontend theo ngoại lệ (nghiệm thu trước lượt backend):

- [x] Node/npm ARM64, manifest exact và lockfile; npm ci offline exit 0, không missing/invalid peer sau tái tạo.
- [x] Next/Tailwind/shadcn Button và form/query; browser kiểm tra CSS và keyboard focus.
- [x] Vitest toàn suite: 1 passed, 3 todo cho nghiệp vụ G5/G9; không coi todos là đạt.
- [x] Playwright/Chromium toàn suite: 1 passed; server frontend tự bắt đầu/kết thúc.
- [x] Frontend env example công khai, env local ignored; không có secret hoặc request backend. Backend còn nguyên 89 file.

### Task 1A — Ghi quyết định sản phẩm và kiến trúc (A, 45–60 phút)

**Files:** tạo `docs/requirements.md`; sửa `docs/architecture.md`.

**Consumes:** Ba workflow, ba vai trò và tiêu chí hoàn thành trong spec.

**Produces:** Ranh giới thành phần, toàn bộ trang bắt buộc, danh sách dữ liệu cần hiển thị, bảng A/U và định nghĩa “hoàn thành”. Không tạo schema SQL hoặc hợp đồng endpoint trong task này.

- [x] Chép các yêu cầu bắt buộc thành bản snapshot sản phẩm có thể theo dõi trong Git; ghi nguồn và ngày, gồm quy tắc không kết luận gian lận khi thiếu chứng cứ.
- [x] Vẽ luồng dữ liệu: đầu vào → trích xuất → rule → đối chiếu nguồn → assessment → lưu → kết quả; AI là phần tăng cường tùy chọn.
- [x] Ghi rõ backend sở hữu đánh giá/quyền dữ liệu; frontend trình bày; dữ liệu demo luôn có nhãn; chưa có dịch vụ xác minh chính phủ.
- [x] Đối chiếu với bảng phủ yêu cầu ở mục 17; không thêm CI/CD, Grafana hoặc cloud để tạo thêm điểm dừng.
- [x] Kiểm tra tài liệu không làm mất mục tiêu end-to-end; checkpoint là hai tài liệu đọc được, chưa phải phần mềm chạy được.

### Task 1U — Tự thiết lập toolchain và môi trường (U, 2–4 giờ; điểm dừng)

**Files:** các manifest/cấu hình toolchain trong mục 4; `frontend/vitest.config.mts` thay file .ts khung để dùng ESM, `frontend/tests/toolchain.test.tsx` và `frontend/e2e/toolchain.spec.ts` kiểm tra runners/shell/404; `frontend/src/app/not-found.tsx`, default export notFound ở page khung và layout nhóm chuyển tiếp children giữ route hợp lệ; `backend/app/core/config.py`, tests config/toolchain, env examples; `docs/development.md`.

**Consumes:** Kiến trúc G1 và stack bắt buộc. **Produces:** runtime ARM64, phiên bản/lockfile đã chọn, frontend shell chạy được, backend import và test runner hoạt động.

- [x] Agent theo ngoại lệ đã kiểm tra công cụ đang có bằng lệnh chỉ đọc; agent giải thích kết quả và hướng dẫn chọn phiên bản stable tương thích từ tài liệu chính thức tại thời điểm thực hành.
- [x] Agent theo ngoại lệ đã chọn công cụ quản lý Python và Node, ghi phiên bản chính xác vào tài liệu, cài dependency cho stack đã yêu cầu. Không cài nhiều công cụ quản lý cùng một mục đích.
- [x] Agent theo ngoại lệ đã thiết lập cấu hình Next/Tailwind/shadcn, Vitest/Playwright và Pytest; shell chỉ chứng minh frontend khởi động và backend/test runner nạp được, chưa giả lập sản phẩm.
- [x] Agent theo ngoại lệ đã tách cấu hình công khai frontend khỏi secret backend; env example dùng giá trị minh họa; xác nhận file secret không vào Git.
- [x] Agent đã ghi phiên bản runtime và output kiểm tra đã loại secret. **Đạt khi:** công cụ chạy được trên máy ARM64, manifest không rỗng, test runner chạy được một self-check tối thiểu và thiếu config được báo rõ.

**Vì sao kết thúc ở đây:** G2/G3 cần công cụ tạo và kiểm tra schema/API; viết app trước khi môi trường dùng được sẽ để lại code không thể kiểm chứng.

**Hành động nhỏ lúc bắt đầu:** mở `docs/architecture.md` và đọc luồng dữ liệu trong 2 phút.

## 6. G2 — Thiết kế dữ liệu, hợp đồng và quyền sở hữu

**Mục tiêu:** Chốt thiết kế trước migration và API; tránh frontend/backend tự đặt hai bộ trạng thái khác nhau.

**Đầu vào:** G1 đạt; chưa cần PostgreSQL đang chạy để thảo luận thiết kế.

### Task 2A — Bộ tình huống sản phẩm dùng xuyên suốt (A, 45–90 phút)

**Files:** `docs/requirements.md`; fixture nghiệp vụ thuần `backend/tests/fixtures/recruitment_cases.json`, `frontend/tests/fixtures/recruitment-cases.ts`.

**Consumes:** Các ví dụ kiểm thử trong spec. **Produces:** Tình huống tổng hợp có nhãn demo, kỳ vọng sản phẩm; không tạo seed DB hay khẳng định nguồn giả đã xác minh thật.

- [ ] Viết tình huống đủ dữ liệu, yêu cầu đóng phí, mạo danh qua liên hệ, thiếu thông tin, dấu hiệu đáng ngờ chưa có bằng chứng, trích xuất thất bại.
- [ ] Với mỗi tình huống, ghi riêng dấu hiệu, nguồn bằng chứng có/không, trạng thái xác minh và hành động đề xuất; không gộp tất cả thành “lừa đảo”.
- [ ] Thêm tình huống đồng âm tên doanh nghiệp và liên hệ không đủ để đối chiếu; phải giữ trạng thái chưa xác minh.
- [ ] Kiểm tra fixture không có thông tin cá nhân thật, không có key, và mọi nguồn giả đều dùng nhãn demo; chỉ chứa dữ liệu bài kiểm tra, chưa là response API.
- [ ] Đọc cùng người dùng một tình huống thiếu dữ liệu để chốt cách diễn đạt; checkpoint là bộ tình huống có kết quả mong đợi rõ ràng.

### Task 2U — Tự thiết kế Database, hợp đồng API và quyền (U, 3–5 giờ; điểm dừng)

**Files:** `docs/architecture.md`, `docs/api.md`; dự kiến `backend/app/models/*.py`, `backend/app/schemas/*.py`, `frontend/src/types/api.ts` ở giai đoạn triển khai tương ứng.

**Consumes:** Bộ tình huống 2A. **Produces:** ERD, bảng trạng thái, hợp đồng phiên bản đầu và ma trận quyền đã được người dùng thiết kế/duyệt.

- [ ] Người dùng thiết kế 13 entity trong spec: users, roles, recruitment_analyses, recruitment_sources, extracted_job_information, risk_indicators, analysis_indicators, verified_employers, employer_sources, recruitment_reports, report_evidence, moderation_actions, saved_analyses. Agent giải thích PK/FK, constraint, index và quan hệ theo luồng sản phẩm.
- [ ] Người dùng xác định snapshot rule/đánh giá, nguồn và thời điểm xác minh, cờ demo, ownership guest/user, TTL, dữ liệu được giữ/xóa; thêm public_warnings riêng cho cảnh báo được xuất bản ở G10. Không lưu mật khẩu rõ hoặc nhân bản ảnh thô không cần thiết.
- [ ] Người dùng thiết kế request/response cho nhóm auth, analysis/extraction/risk, employer, history/save/profile, report/moderation, admin/statistics/warnings. Chốt status/error envelope, pagination, ID và tên trường; ghi rõ phần nào chưa triển khai ở từng giai đoạn.
- [ ] Người dùng lập ma trận guest/user/admin theo thao tác; chọn cơ chế phiên, quyền truy cập kết quả guest, CSRF khi dùng cookie, retention và consent trước OCR/LLM bên ngoài. Chưa dùng UI guard như bằng chứng API đã được bảo vệ.
- [ ] Người dùng gửi ERD và hợp đồng không chứa secret. **Đạt khi:** từng trường trên trang kết quả có nguồn dữ liệu; mỗi thao tác có owner/quyền; trạng thái rủi ro/xác minh/báo cáo không lẫn nhau; có vòng đời ảnh, text, kết quả guest và báo cáo.

**Điểm cần thống nhất:** risk gồm Low/Moderate/High/Insufficient Information; verification gồm Matched/Conflicting/Not Verified/Insufficient Data; report gồm Pending/Under Review/Insufficient Evidence/Verified Warning/Rejected. Mã wire và nhãn tiếng Việt do người dùng chốt tại đây rồi dùng thống nhất. “Verified Warning” của báo cáo chưa đồng nghĩa cảnh báo công khai đã xuất bản.

**Vì sao kết thúc ở đây:** G3 cần schema và quyền để làm DB/auth; G4 cần dạng dữ liệu nghiệp vụ đã chốt; G5 cần hợp đồng thật để tích hợp.

**Hành động nhỏ lúc bắt đầu:** chọn một tình huống “thiếu thông tin” để lần theo các trường cần lưu.

## 7. G3 — PostgreSQL, migration và tài khoản thật

**Mục tiêu:** Backend có cơ sở dữ liệu và quyền truy cập thật trước khi lưu phân tích hoặc báo cáo.

**Đầu vào:** G2 đạt, đã chốt phiên truy cập và quyền guest/user/admin.

### Task 3A — Giao diện đăng ký/đăng nhập độc lập (A, 60–90 phút)

**Files:** `frontend/src/components/auth/auth-form.tsx`, `frontend/src/app/(public)/login/page.tsx`, `frontend/src/app/(public)/register/page.tsx`, `frontend/src/components/layout/header.tsx`.

**Consumes:** Nội dung và trường hiển thị đã chốt; chưa tiêu thụ auth API. **Produces:** Form có label, keyboard focus, trạng thái pending/lỗi được truyền qua props và callback trình bày.

- [ ] Viết component chỉ thu giá trị và gọi callback được truyền vào; không lưu token, không viết thuật toán mật khẩu, không gọi API.
- [ ] Viết nội dung tiếng Việt, nhãn trường, lỗi hiển thị và liên kết hai trang; không thông báo “đã đăng nhập” nếu chưa có dữ liệu phiên thật.
- [ ] Kiểm tra bàn phím, màn hình nhỏ và lỗi không chỉ phân biệt bằng màu.
- [ ] Kiểm tra component với callback giả trong test; không gắn callback giả vào đường chạy ứng dụng.
- [ ] Hoàn tất giao diện để người dùng có điểm nối ở task 3U.

### Task 3U — Tự dựng DB nền và authentication (U, 6–8 giờ; điểm dừng)

**Files:** `backend/app/db/{base,session}.py`, `backend/app/models/{users,analyses,indicators,employers,saved_analyses}.py`, migration `0001_initial.py`, `backend/app/seed/{load.py,demo_data.json}`, `backend/app/{main.py,api/router.py}`, auth/users routes và schemas, `backend/app/core/{config,security,privacy}.py`, `backend/app/api/{dependencies,errors}.py`, `frontend/src/{lib/api-client.ts,hooks/use-auth.ts,providers/auth-provider.tsx}`, các test authentication/authorization/privacy, `docs/development.md`.

**Consumes:** Thiết kế 2U, form 3A. **Produces:** DB thật, migration nền, dữ liệu demo nền, API đăng ký/đăng nhập/đăng xuất/profile tối thiểu, danh tính và quyền được kiểm tra phía backend.

- [ ] Người dùng chọn PostgreSQL local hoặc container PostgreSQL đơn lẻ; nếu dùng Docker, học image/tag/ARM64, port mapping và named volume ngay khi tạo DB. Chưa cần build image ứng dụng hay Compose đầy đủ.
- [ ] Người dùng viết model/session và migration nền cho tài khoản, phân tích, rule, employer, saved_analyses; kiểm tra constraint/transaction trên DB phát triển. Báo cáo/public warnings có migration riêng ở G9/G10.
- [ ] Người dùng tạo seed tổng hợp, nạp lặp không nhân đôi, có nhãn demo; user/admin demo dùng mật khẩu do người dùng thiết lập, không đưa secret vào fixture. Kiểm tra nguồn demo chỉ được dùng trong ngữ cảnh demo.
- [ ] Người dùng triển khai auth, hashing, session/logout, kiểm soát quyền và nối form thật; viết/chạy test đăng ký trùng, sai mật khẩu, phiên hết hạn, user gọi admin, dữ liệu user khác và chính sách guest đã chốt.
- [ ] Người dùng gửi kết quả migration, test và thao tác trình duyệt đã loại secret. **Đạt khi:** đăng ký → login → logout thật; credential lưu an toàn; DB còn dữ liệu sau restart; backend từ chối sai quyền, seed không giả danh nguồn thật.

**Không đảo thứ tự:** chưa lưu phân tích riêng tư trước khi biết kết quả thuộc user/guest nào. Kiểm tra quyền và vòng đời guest thuộc G3, không dồn tất cả bảo mật tới G11.

**Hành động nhỏ lúc bắt đầu:** mở ERD của G2 và chỉ ra bảng users liên kết với analyses như thế nào.

## 8. G4 — Phân tích văn bản bằng rule và nguồn đã có

**Mục tiêu:** Xây luồng text đầu tiên chạy thật, không phụ thuộc OCR hoặc LLM.

**Đầu vào:** DB/auth nền G3 và quy ước dữ liệu G2.

### Task 4A — Logic trích xuất, rule, score, đối chiếu thuần (A, 3–5 giờ)

**Files:** `backend/app/services/{domain,extraction,rule_engine,risk_assessment,employer_verification}.py`; `backend/tests/test_{extraction,rule_engine,risk_assessment,employer_verification,missing_information}.py`; fixture nghiệp vụ 2A.

**Consumes:** Text và bộ rule/nguồn do caller đưa vào; không query DB, không đọc env, không gọi mạng. **Produces:** Các hàm thuần và dữ liệu giải thích dưới đây; tên field được căn theo thiết kế 2U trước khi code.

Giao diện nghiệp vụ dự kiến để G4 tự kiểm tra được:

```python
extract_job_information(text: str) -> ExtractedJob
detect_indicators(text: str, rules: tuple[DetectionRule, ...]) -> tuple[TriggeredIndicator, ...]
assess_risk(job: ExtractedJob, indicators: tuple[TriggeredIndicator, ...], policy: ScoringPolicy) -> RiskAssessment
compare_employer(job: ExtractedJob, employers: tuple[EmployerRecord, ...]) -> VerificationFinding
```

`domain.py` định nghĩa `ExtractedJob` gồm company_name, job_title, salary, location, employment_type, contact_email, contact_phone, recruitment_website, application_requirements, required_payments, suspicious_instructions; trường không trích xuất được là `None`. `DetectionRule` gồm code, enabled, weight, phrases và explanation_vi; `TriggeredIndicator` gồm rule_code, weight, matched_quote, explanation_vi. `ScoringPolicy` gồm version, moderate_min, high_min; `RiskAssessment` gồm level, score, reasons, rule_version lấy từ policy.version. `EmployerRecord` gồm name, official_domains, official_recruitment_pages, official_contacts, sources, verified_at, is_demo; `VerificationFinding` gồm status, confidence, findings, sources, verified_at, is_demo. confidence mô tả mức hỗ trợ của nguồn bằng nhãn định tính, không phải xác suất tin tuyển dụng thật. Đây là kiểu nghiệp vụ thuần, không thay cho hợp đồng API do người dùng thiết kế.

- [ ] Viết test từ tình huống 2A trước: đóng phí → có trích đoạn kích hoạt; thiếu trường → `None`; tên công ty trùng không đủ để xác minh; thiếu thông tin không thành low risk mặc định.
- [ ] Chạy từng nhóm test bằng Pytest sau khi môi trường G1 đạt; xác nhận fail vì hành vi chưa có, không vì thiếu công cụ.
- [ ] Viết extractor và matcher tối thiểu: chuẩn hóa khoảng trắng/chữ hoa thường, giữ nguyên trích đoạn gốc, không suy đoán email/domain/salary khi text không có. Bao phủ tám nhóm dấu hiệu trong spec và câu phủ định như “không thu phí”.
- [ ] Viết scoring/đối chiếu: cùng dữ liệu và snapshot rule cho cùng score; score không phải xác suất; thiếu thông tin có trạng thái riêng; nguồn trùng tên chưa xác minh tin; contact xung đột được giải thích từ nguồn có sẵn.
- [ ] Chạy test thuần, kiểm tra fixture demo; lưu checkpoint gồm tên test đạt và các hàm/kiểu mà 4U sẽ gọi. Không viết logic lưu DB vào service thuần.

**Chính sách MVP đề xuất để test được cụ thể:** policy `rules-v1`, ngưỡng moderate 20, high 50; cộng trọng số mỗi rule_code một lần, chặn tổng ở 100. Trọng số: phí tuyển dụng trước 50, đặt cọc trước phỏng vấn 50, hứa thu nhập phi thực tế 20, nạp tiền để làm nhiệm vụ 50, yêu cầu dữ liệu nhạy cảm bất thường 30, yêu cầu chuyển tiền 50, kênh liên hệ đáng ngờ 20, chỉ dấu mạo danh 30. Câu “không thu phí” không kích hoạt phí; quảng cáo mức lương cao một mình chưa đủ kích hoạt hứa thu nhập phi thực tế; từ “CCCD” một mình chưa đủ kích hoạt yêu cầu nhạy cảm bất thường. Tình huống phải chứa ngữ cảnh yêu cầu/hứa cụ thể, không chỉ từ khóa chung.

Score đạt 50 trở lên cho high; đạt 20–49 cho moderate. Dưới 20 nhưng thiếu company_name, job_title hoặc mọi kênh contact/website thì insufficient_information; dưới 20 và đủ những trường này mới low. Low luôn kèm nhãn “Ít dấu hiệu theo quy tắc hiện tại”, không “Đã chứng minh an toàn”. VerificationFinding có trạng thái/confidence riêng, không cộng điểm an toàn vào score chỉ vì doanh nghiệp tồn tại. Trọng số/ngưỡng là chính sách heuristic đề xuất, không phải thông số thống kê được hiệu chuẩn; ghi bảng và kỳ vọng fixture vào `docs/architecture.md` trước code. Nếu người dùng điều chỉnh chính sách, cập nhật policy/version/test cùng nhau; config động được người dùng lưu ở 4U.

Ví dụ test kiểm tra một bất biến, dùng đúng giao diện đã định nghĩa:

```python
from app.services.extraction import extract_job_information
from app.services.risk_assessment import assess_risk
from app.services.domain import ScoringPolicy

POLICY = ScoringPolicy(version="rules-v1", moderate_min=20, high_min=50)

def test_empty_input_is_not_low_risk():
    job = extract_job_information("")
    result = assess_risk(job, (), POLICY)
    assert result.level == "insufficient_information"

def test_same_input_and_rules_produce_same_assessment():
    job = extract_job_information("Tin tuyển dụng chưa có thông tin vị trí và liên hệ")
    assert assess_risk(job, (), POLICY) == assess_risk(job, (), POLICY)
```

Mã trạng thái trong ví dụ phải được 2U chốt trước; nếu wire dùng mã khác, kiểu domain vẫn phải có mapping duy nhất. Test tính tái lập không thay thế test ngưỡng/rule; cần thêm tình huống phí, phủ định, xung đột liên hệ và thiếu nguồn như các bước ở trên.

### Task 4U — Tự nối engine với Database và API (U, 3–4 giờ; điểm dừng)

**Files:** `backend/app/services/analysis.py`, analyses/employers/risk routes và schemas, `backend/app/api/errors.py`, models analyses/indicators, `backend/app/core/rate_limit.py`, `backend/tests/conftest.py`, test API tương ứng; `docs/api.md`.

**Consumes:** DB G3 và hàm thuần 4A. **Produces:** Backend text → kết quả lưu thật; employer verification độc lập; API read kết quả có quyền truy cập.

- [ ] Người dùng viết orchestration lấy rule và nguồn từ DB, gọi các hàm thuần, lưu source/extracted fields/indicators/score/explanations/snapshot trong transaction.
- [ ] Người dùng triển khai analysis/risk/employer API theo 2U, validation, structured errors và OpenAPI; trường thiếu không bị biến thành chuỗi chứng minh an toàn.
- [ ] Người dùng áp dụng giới hạn chi phí đầu vào, rate limiting và quyền đọc kết quả guest/user; ID ngẫu nhiên một mình không thay thế quyền truy cập.
- [ ] Người dùng viết/chạy integration test trên DB test biệt lập: đủ/thiếu text, rule disabled/changed, contact xung đột, nguồn demo, rollback khi lưu lỗi và kết quả cũ giữ được cách giải thích sau khi đổi rule.
- [ ] Người dùng gửi test/output mẫu không có dữ liệu cá nhân. **Đạt khi:** response và DB khớp; có ID thật; đọc lại kết quả được; nguồn không có trả “chưa xác minh”; không key AI vẫn chạy.

**Vì sao kết thúc ở đây:** UI G5 cần response thật và trạng thái lỗi thật; không tích hợp một API giả rồi viết lại khi DB có sau.

**Hành động nhỏ lúc bắt đầu:** chạy một test nghiệp vụ thuần đã có trong G4A.

## 9. G5 — Giao diện công khai và vòng phân tích hoàn chỉnh

**Mục tiêu:** Guest sử dụng được từ trình duyệt đến backend/DB; trọng tâm là trang kết quả.

**Đầu vào:** API text và employer G4 đã đạt.

### Task 5A — Các trang công khai và kết quả có cấu trúc (A, 4–6 giờ)

**Files:** public pages landing/analyze/analysis/[id]/verify-employer/safety; root layout/globals; components layout, analysis, employers; `frontend/tests/{analysis-results,recruitment-input-form}.test.tsx`.

**Consumes:** Dữ liệu hợp đồng đã được người dùng xác nhận ở G4. **Produces:** Component trình bày nhận dữ liệu thật qua props, form có callback; không tự viết fetch/hooks gọi backend.

- [ ] Viết test trang kết quả thể hiện risk, giải thích, từng indicator, bằng chứng, trạng thái xác minh, thời điểm nguồn, hạn chế và hành động khuyến nghị; thiếu nguồn phải có nhãn rõ.
- [ ] Làm shell responsive, landing và safety tiếng Việt; form text là đường chính, không giả vờ ảnh/URL đã được hỗ trợ trước G6.
- [ ] Làm trang kết quả bằng component hiện có: risk-summary, indicator-list, verification-findings, evidence-list, recommended-actions. Score hiển thị là điểm heuristic, không `% xác suất lừa đảo`.
- [ ] Làm employer form và trạng thái loading/empty/error/retry qua props; tên doanh nghiệp tồn tại không đồng nghĩa tin đăng thật. Không dùng raw HTML từ nguồn bên ngoài.
- [ ] Chạy frontend unit tests và kiểm tra màn hình nhỏ/bàn phím; dữ liệu fixture chỉ trong test, ứng dụng chờ dữ liệu thật từ 5U.

### Task 5U — Tự tích hợp frontend–backend (U, 2–3 giờ; điểm dừng)

**Files:** `frontend/src/types/api.ts`, `frontend/src/lib/{api-client,validations}.ts`, `frontend/src/hooks/{use-analyses,use-employers}.ts`, query/auth providers, public page data wiring, `frontend/e2e/{analysis,employer-verification}.spec.ts`, CORS/config backend nếu cần.

**Consumes:** API 4U và UI 5A. **Produces:** Luồng browser text → DB → kết quả và employer verification thật.

- [ ] Người dùng triển khai API client theo contract: error envelope, cancellation và query state; cấu hình origin/cookie/CORS theo cơ chế auth đã chọn. Secret backend không vào bundle Next.js.
- [ ] Người dùng nối TanStack Query/form với text analysis và employer verification; xử lý ID không tồn tại, phiên guest hết hạn và request lỗi bằng thông báo tiếng Việt.
- [ ] Người dùng kiểm tra direct URL kết quả theo quyền guest/user, frontend không công khai text/ảnh chỉ vì nằm trong route group `(public)`; cấu hình cache cho dữ liệu riêng theo policy.
- [ ] Người dùng viết/chạy Playwright sáu tình huống cốt lõi: tin đủ thông tin, đóng phí, mạo danh liên hệ, thiếu dữ liệu, nghi ngờ chưa có chứng cứ, backend lỗi. Test xác minh riêng phải kiểm tra cả matched/conflicting/not verified/insufficient data.
- [ ] Người dùng gửi kết quả test và một ID demo trong DB. **Đạt khi:** refresh còn kết quả đúng quyền; UI phản ánh API/DB thật; request thất bại không thành kết quả thành công giả.

**Mốc sản phẩm:** kết thúc G5 có luồng văn bản end-to-end đầu tiên. Đây là checkpoint nội bộ, chưa hoàn tất MVP vì còn ảnh/URL, báo cáo và quản trị.

**Hành động nhỏ lúc bắt đầu:** nhập một mẫu đóng phí tổng hợp vào trang `/analyze`.

## 10. G6 — Đầu vào ảnh/URL và đường sửa văn bản

**Mục tiêu:** Mở rộng hai đầu vào mới mà vẫn dùng engine G4 và UI G5.

**Đầu vào:** Luồng text G5 hoạt động; chính sách lưu/truy cập/xóa dữ liệu đầu vào G2 đã chốt.

### Task 6A — Trình bày đầu vào và fallback (A, 1–2 giờ)

**Files:** `recruitment-input-form.tsx`, `extracted-job-editor.tsx`, analyze page, `frontend/tests/recruitment-input-form.test.tsx`.

**Consumes:** Trạng thái extraction được 2U thiết kế. **Produces:** Chọn text/image/URL, preview text có thể sửa, thông báo bị chặn/không đọc được; submit text sau khi người dùng xác nhận.

- [ ] Viết test OCR trả không có text → hiện editor và hướng dẫn dán văn bản; không hiện kết quả phân tích bịa.
- [ ] Làm ba chế độ đầu vào và trạng thái extraction bằng props; UI validation chỉ giúp người nhập, không thay kiểm tra upload/URL phía backend.
- [ ] Làm editor hiển thị text trích xuất để người dùng sửa trước đánh giá; đường text luôn sử dụng được.
- [ ] Làm lỗi timeout/không hỗ trợ/ảnh không đọc được; gợi ý hành động nhỏ “Dán nội dung tuyển dụng”.
- [ ] Chạy test component; bàn giao UI và các trạng thái cho 6U, chưa bật kết nối nguồn ngoài.

### Task 6U — Tự làm upload, OCR và URL extraction an toàn (U, 5–7 giờ; điểm dừng)

**Files:** extraction routes/schemas, `backend/app/services/{ocr,url_extraction,extraction,analysis}.py`, `backend/app/core/{upload_validation,url_safety,privacy,rate_limit}.py`, frontend request wiring; tests upload/url/privacy/extraction_failures; `frontend/e2e/analysis-inputs.spec.ts`.

**Consumes:** Engine text, UI editor và policy G2. **Produces:** Ảnh/URL → extraction hoặc lỗi có cấu trúc → người dùng sửa → text analysis; dữ liệu đầu vào được bảo vệ.

- [ ] Người dùng chọn OCR thực chạy được trên ARM64; ưu tiên đường không cần credential cho demo. Nếu chọn dịch vụ ngoài, có thông báo/consent và chế độ dán text khi không cấu hình. Không giả lập OCR thành công.
- [ ] Người dùng thiết lập kiểm tra kích thước/định dạng thực của ảnh, nội dung hỏng, quyền lấy tệp, thời hạn lưu/xóa và lỗi an toàn; tên file không quyết định tệp được chấp nhận.
- [ ] Người dùng viết URL fetch chỉ HTTP(S) công khai, kiểm tra DNS/IP và mỗi redirect, chặn loopback/private/link-local và metadata, hạn chế kích thước/timeout. Không vượt login/CAPTCHA hoặc lấy trang cần quyền riêng.
- [ ] Người dùng viết/chạy test ảnh hợp lệ/hỏng/quá lớn, URL private/redirect-to-private/DNS thay đổi, trang bị chặn/không hỗ trợ, OCR rỗng và extraction timeout; dùng nguồn test kiểm soát được, không gọi website thật trong unit test.
- [ ] Người dùng gửi test và kết quả demo. **Đạt khi:** thất bại trở lại editor/text; upload/URL được backend kiểm tra; không rò tệp qua ID khác; ba đầu vào dùng cùng scoring.

**Vì sao kết thúc ở đây:** bảo mật phải có trước khi nhận dữ liệu ngoài. G7 chỉ nhận text đã xác nhận, không mở thêm một luồng gửi ảnh nhạy cảm thẳng tới LLM.

**Hành động nhỏ lúc bắt đầu:** thử một ảnh demo không đọc được để kiểm tra editor fallback.

## 11. G7 — AI hỗ trợ, không-key và hạn chế rõ ràng

**Mục tiêu:** Thêm diễn giải ngữ cảnh bằng ít nhất một provider cấu hình được; luồng core không phụ thuộc provider đó.

**Đầu vào:** G6 đạt; đã có rule engine, kết quả có cấu trúc và consent policy.

### Task 7A — Trình bày trạng thái AI và nguồn giải thích (A, 45–90 phút)

**Files:** `analysis-results.tsx`, `risk-summary.tsx`, `indicator-list.tsx`, `evidence-list.tsx`, `frontend/tests/analysis-results.test.tsx`.

**Consumes:** Trạng thái AI và phân biệt nguồn rule/AI do người dùng chốt. **Produces:** Nhãn AI tắt/không khả dụng/hoạt động, giới hạn bằng tiếng Việt; AI inference không thành bằng chứng xác minh.

- [ ] Viết test trạng thái không-key vẫn hiển thị score/indicator và hạn chế rule-only.
- [ ] Thêm nguồn của giải thích, tách “suy luận hỗ trợ” khỏi trích đoạn/nguồn được kiểm chứng; không cho AI tự tạo nhãn verified.
- [ ] Thêm thông báo dữ liệu có thể gửi provider trước thao tác bật AI theo consent policy; không ngầm coi mở trang là đồng ý.
- [ ] Kiểm tra rendering AI lỗi/không-key không xóa findings của rule engine.
- [ ] Chạy component tests và bàn giao UI cho provider wiring U.

### Task 7U — Tự làm provider và ranh giới dữ liệu (U, 3–5 giờ; điểm dừng)

**Files:** `backend/app/services/ai/{base,llm_provider,prompts}.py`, config/privacy, `analysis.py`, extraction/analysis schemas nếu contract G2 cần mở rộng có version; test_ai_fallback/privacy/extraction, frontend consent/request wiring và env examples.

**Consumes:** Text đã xác nhận và evidence/rule findings có thật. **Produces:** Provider abstraction, một provider cấu hình qua env, output kiểm tra cấu trúc, fallback và nguồn giải thích lưu rõ.

- [ ] Người dùng chọn một provider, đọc tài liệu chính thức tại lúc tích hợp, cấu hình env và interface; không đặt key ở frontend hay request log.
- [ ] Người dùng tối thiểu hóa dữ liệu gửi đi, triển khai consent, timeout hữu hạn và phản hồi lỗi; không-key không thử gọi mạng. Giải thích chi phí trước khi người dùng tự chạy test provider thật.
- [ ] Người dùng kiểm tra output LLM bằng schema, chống nội dung tuyển dụng ra lệnh cho hệ thống, không tin domain/bằng chứng AI bịa; ghi nguồn AI khác nguồn đã xác minh.
- [ ] Người dùng giữ score cuối dựa trên dữ liệu/rule/version rõ ràng. Nếu AI hỗ trợ extraction, lưu dữ liệu đầu vào scoring đã dùng; cùng dữ liệu có cấu trúc và cùng rule phải tái tạo được score. Không yêu cầu hai lần gọi LLM cho cùng text luôn ra cùng JSON.
- [ ] Người dùng chạy test không-key, timeout, malformed output, provider lỗi, nội dung prompt injection, AI bịa nguồn và consent bị từ chối. **Đạt khi:** tất cả về rule-only an toàn; một provider cấu hình được; không cần API trả phí để nghiệm thu core/demo.

**Không-key là điểm dừng hợp lệ:** test adapter bằng provider giả trong test chứng minh hợp đồng và xử lý lỗi; không tuyên bố đã kiểm chứng kết nối provider thật nếu chưa gọi thật. Việc test trả phí là tùy người dùng.

**Hành động nhỏ lúc bắt đầu:** tắt AI bằng cấu hình bạn quản lý và chạy lại một mẫu text.

## 12. G8 — Lịch sử, lưu kết quả, dashboard và hồ sơ

**Mục tiêu:** User sử dụng dữ liệu cá nhân thật trên nền auth và analysis đã có.

**Đầu vào:** G3 auth và G5/G7 luồng phân tích đã đạt; G8 không cần key AI.

### Task 8A — Các trang cá nhân và thống kê hiển thị (A, 2–3 giờ)

**Files:** `(user)/{layout,dashboard/page,history/page,saved/page,profile/page}.tsx`, `sidebar.tsx`, `risk-statistics.tsx`, `profile-form.tsx`.

**Consumes:** Dữ liệu list/profile/statistics do hợp đồng U cung cấp; không tự query backend. **Produces:** Lịch sử, saved list, profile, recent analyses và thống kê có empty/loading/error.

- [ ] Làm list lịch sử/lưu với thời điểm, risk và link đúng kết quả; danh sách trống có hành động “Phân tích tin tuyển dụng”.
- [ ] Làm dashboard biểu đồ/phân bố kèm số đếm và nhãn; không biến tần suất risk thành xác suất người dùng bị lừa.
- [ ] Làm profile form trình bày, thông báo lưu thành công/lỗi qua props; không thêm chức năng đổi mật khẩu chưa có yêu cầu cụ thể.
- [ ] Kiểm tra component/list với dữ liệu rỗng, nhiều trang và tên dài; không thêm khả năng truy cập dữ liệu user khác.
- [ ] Bàn giao các điểm nối U; route group không có ý nghĩa phân quyền tự động.

### Task 8U — Tự nối API dữ liệu riêng và pagination (U, 2–3 giờ; điểm dừng)

**Files:** users/saved_analyses/analyses/statistics routes và schemas, models saved_analyses, `services/statistics.py`, frontend use-analyses/use-auth/api-client/auth-provider/user layout wiring; backend tests authorization/privacy/statistics; `frontend/e2e/user-dashboard.spec.ts`.

**Consumes:** Ownership G2, auth G3, analyses G4 và UI 8A. **Produces:** Save/unsave/history/profile/dashboard thật, query theo user và phân trang.

- [ ] Người dùng làm save/unsave có constraint không trùng; read history/profile/statistics luôn theo user backend xác định, không tin owner ID do client gửi.
- [ ] Người dùng bổ sung pagination/sort ổn định và dữ liệu dashboard từ DB; profile chỉ cập nhật trường được phép, không tự nâng role.
- [ ] Người dùng nối API vào trang, bảo vệ truy cập và xử lý cache khi logout/chuyển tài khoản; không để dữ liệu tài khoản trước hiện trong phiên sau.
- [ ] Người dùng chạy test lưu lặp, ID user khác, pagination, profile cố đổi role, phiên hết hạn, logout/login tài khoản khác và refresh dữ liệu đã lưu.
- [ ] Người dùng gửi test và bằng chứng DB. **Đạt khi:** user thấy đúng dữ liệu mình; save sống qua restart; API từ chối truy cập chéo; thống kê khớp dữ liệu.

**Vì sao kết thúc ở đây:** báo cáo G9 sẽ dùng cùng danh tính, quyền, query cache và pagination; không thiết kế một cơ chế quyền mới riêng cho báo cáo.

**Hành động nhỏ lúc bắt đầu:** lưu một kết quả demo rồi refresh trang `/saved`.

## 13. G9 — Báo cáo, bằng chứng và kiểm duyệt

**Mục tiêu:** User gửi báo cáo riêng tư, admin duyệt; chưa tự xuất bản cảnh báo công khai.

**Đầu vào:** Tài khoản và không gian cá nhân G8 đạt, upload policy G6 có thể tái sử dụng.

### Task 9A — UI báo cáo và quy tắc chuyển trạng thái thuần (A, 2–3 giờ)

**Files:** `components/reports/{report-form,report-status}.tsx`, `components/admin/moderation-form.tsx`, user reports/new và reports pages, admin/reports page; `services/report_moderation.py`; test_report_transitions.py, frontend report-form/report-status tests.

**Consumes:** Status G2 và dữ liệu report/moderation được truyền vào; U quyết định quyền và persistence. **Produces:** Form, tracking và hàm kiểm tra chuyển trạng thái thuần.

Giao diện thuần: `allowed_report_targets(current_status: str) -> tuple[str, ...]`; mã trạng thái theo G2. `pending` được chuyển tới `under_review`; `under_review` được chuyển tới `insufficient_evidence`, `verified_warning` hoặc `rejected`; `insufficient_evidence` được chuyển lại `under_review` khi có bổ sung; trạng thái kết thúc không tự mở lại. Không có hàm thuần này đồng nghĩa caller được phép kiểm duyệt.

- [ ] Viết test các cạnh hợp lệ và không hợp lệ; `pending → verified_warning` bị chặn; `verified_warning → pending` bị chặn; `insufficient_evidence → under_review` được phép.
- [ ] Viết hàm bảng chuyển tối thiểu, không DB và không role check; caller U phải kiểm tra quyền và evidence trước khi lưu.
- [ ] Làm report form và tracking hiển thị năm trạng thái tiếng Việt, notes phù hợp người gửi; UI không công khai báo cáo riêng tư.
- [ ] Làm moderation view hiển thị evidence, quyết định và lịch sử nhận từ API; không đặt nút “Công khai” trên mọi báo cáo.
- [ ] Chạy test thuần/component; bàn giao hàm và UI cho DB/API U.

Ví dụ kiểm tra chuyển trạng thái:

```python
from app.services.report_moderation import allowed_report_targets

def test_pending_cannot_be_verified_directly():
    assert "verified_warning" not in allowed_report_targets("pending")

def test_insufficient_evidence_can_return_to_review():
    assert "under_review" in allowed_report_targets("insufficient_evidence")
```

### Task 9U — Tự làm Database/API báo cáo và quyền bằng chứng (U, 4–6 giờ; điểm dừng)

**Files:** models reports, migration `0002_reporting.py`, reports/admin routes và schemas, report_moderation persistence caller, privacy/upload validation, frontend use-reports/use-admin và wiring; tests reports/moderation/authorization/privacy, e2e reports/admin-moderation.

**Consumes:** G8 danh tính, G6 upload, G9A transitions. **Produces:** Submit → Pending → Under Review → outcome; evidence riêng tư, moderation_actions không mất lịch sử.

- [ ] Người dùng làm migration cho recruitment_reports/report_evidence/moderation_actions, constraint và chỉ mục phù hợp; mỗi quyết định lưu actor/time/notes và version kiểm tra cập nhật.
- [ ] Người dùng triển khai gửi báo cáo từ kết quả hoặc tin khác, bằng chứng text/file, tracking theo owner; dùng lại kiểm tra upload/quyền/retention, không mở đường tải evidence công khai.
- [ ] Người dùng triển khai admin review, bắt buộc đủ chứng cứ và notes khi verified_warning; kết hợp transition thuần với role check và transaction. Chặn cập nhật stale khi hai admin cùng quyết định.
- [ ] Người dùng nối UI và chạy test submit thiếu field, pending ban đầu, truy cập chéo, user cố duyệt, evidence URL riêng, thiếu chứng cứ, cập nhật lặp/stale, notes lịch sử và rejected/insufficient_evidence không công khai.
- [ ] Người dùng gửi test và lịch sử demo đã che dữ liệu riêng. **Đạt khi:** user theo dõi được; admin duyệt được; mỗi quyết định có audit; không report nào tự thành public warning.

**Vì sao kết thúc ở đây:** G10 chỉ xuất bản được sau khi có quy trình tạo và kiểm chứng quyết định; không làm public warning từ nút submit report.

**Hành động nhỏ lúc bắt đầu:** gửi một báo cáo demo có bằng chứng text và kiểm tra trạng thái Pending.

## 14. G10 — Quản trị nguồn, rule, thống kê và cảnh báo

**Mục tiêu:** Admin quản lý dữ liệu vận hành sản phẩm; cảnh báo công khai có bằng chứng và bản đã lược dữ liệu riêng.

**Đầu vào:** Engine/nguồn G4, dữ liệu cá nhân G8 và kiểm duyệt G9.

### Task 10A — Giao diện quản trị và cảnh báo công khai (A, 2–3 giờ)

**Files:** `(admin)/admin/{layout,page,employers/page,rules/page}.tsx`, employer-form/rule-form, risk-statistics; `(public)/safety/page.tsx`; frontend presentation tests phù hợp.

**Consumes:** Admin/source/rule/statistics/warning data từ contract U. **Produces:** UI quản lý nguồn và rule, bảng thống kê, public warning có nguồn/ngày/hạn chế.

- [ ] Làm form nguồn employer: domain, contact, evidence, thời điểm xác minh và nhãn demo; không tự đề xuất nguồn chính phủ giả.
- [ ] Làm rule form biểu thị code, enabled, weight và giải thích; cảnh báo thay đổi rule ảnh hưởng phân tích mới, không đổi kết quả lịch sử.
- [ ] Làm admin dashboard: tổng analyses, queue cần duyệt, phân bố risk và moderation history; empty state và quyền được nối tại U.
- [ ] Làm safety page hiển thị public warning đã được API công khai cung cấp; chỉ dữ liệu đã lược riêng tư, không raw report/evidence riêng.
- [ ] Kiểm tra UI tiếng Việt, trạng thái thiếu nguồn và demo; không dùng số liệu hardcode ngoài unit test.

### Task 10U — Tự làm Admin API và quy trình xuất bản (U, 3–5 giờ; điểm dừng)

**Files:** admin/employers/statistics/warnings routes và schemas, models warnings, migration `0003_public_warnings.py`, rule/employer persistence, statistics service, seed bổ sung; frontend use-admin và wiring; backend authorization/moderation/privacy/employer/risk/statistics tests, e2e/admin-management.spec.ts.

**Consumes:** RBAC G3, moderation_actions G9, snapshot rule G4. **Produces:** CRUD nguồn/rule có audit, thống kê thật, warning publication riêng có điều kiện.

- [ ] Người dùng tạo public_warnings gắn nguồn/chứng cứ/decision, lưu bản public đã lược riêng tư; quyết định verified_warning chưa tự xuất bản. Chốt withdraw/correction và giữ lịch sử khi cảnh báo được sửa.
- [ ] Người dùng làm admin source/rule APIs, validation, RBAC và audit thay đổi; deactivate/version rule, giữ snapshot và reference của phân tích cũ, không xóa dây chuyền chứng cứ lịch sử.
- [ ] Người dùng làm statistics từ DB, pagination queue/history; tách stats user và admin, không đưa số liệu riêng user vào API công khai.
- [ ] Người dùng nối UI và chạy test non-admin bị chặn, source thiếu bằng chứng, rule đổi không đổi score cũ, publish pending bị chặn, publish đủ evidence thành công, private fields không có trong public response, cảnh báo demo có nhãn và số liệu thống kê khớp DB.
- [ ] Người dùng gửi test và thao tác demo. **Đạt khi:** admin quản lý được ba lĩnh vực; public warning chỉ từ quy trình có chứng cứ; toàn bộ chức năng trong prompt có đường chạy thật.

**Vì sao kết thúc ở đây:** đóng gói G11 sẽ gói ứng dụng đã đủ chức năng và có test; không dùng Docker để che một module còn response giả.

**Hành động nhỏ lúc bắt đầu:** đổi trạng thái enabled của một rule demo rồi đối chiếu kết quả cũ và mới.

## 15. G11 — Kiểm tra toàn luồng và Docker vận hành local

**Mục tiêu:** Người dùng tự đóng gói, chạy và phục hồi dữ liệu của một MVP hoàn chỉnh trên ARM64.

**Đầu vào:** G10 đạt; backend/frontend chạy local bằng môi trường đã ghi tại G1. Không cần AI trả phí.

### Task 11A — Chốt bộ nghiệm thu và tài liệu sản phẩm (A, 1–2 giờ)

**Files:** `docs/acceptance.md`, README phần walkthrough sản phẩm/demo; frontend component tests và backend test thuần đã tạo.

**Consumes:** Bằng chứng G1–G10. **Produces:** Checklist nghiệm thu có expected result, tài liệu demo và các test thuần đạt.

- [ ] Lập checklist guest → text/image/URL → result → verification; user → login → save/history/profile → report; admin → moderate → source/rule → warning/statistics.
- [ ] Gắn từng item với test cụ thể trong mục 17; bổ sung tình huống thiếu dữ liệu, nghi ngờ chưa có chứng cứ, mạo danh và extraction/AI fallback nếu chưa được kiểm tra.
- [ ] Chạy test nghiệp vụ thuần và frontend component bằng công cụ đã có; không tự chạy API/auth/migration hoặc dựng DB test thay người dùng.
- [ ] Viết walkthrough demo tiếng Việt chỉ dùng dữ liệu có nhãn tổng hợp, có đường không-key, nêu đây là hỗ trợ đánh giá rủi ro.
- [ ] Kiểm tra README không tuyên bố lệnh Docker/migration đã thành công khi chưa có kết quả U; bàn giao checklist để 11U nghiệm thu stack thật.

### Task 11U — Tự học Docker và kiểm chứng toàn stack (U, 6–8 giờ; điểm dừng cuối)

**Files:** Dockerfile/.dockerignore frontend/backend, compose.yaml, env examples, core config, main/API health endpoint do người dùng viết nếu chọn dùng health check; README phần install/env/start/migration/seed/test/AI, docs/development và docs/api.

**Consumes:** Ứng dụng thật + manifest/lockfile G1 + migrations/seed + checklist 11A. **Produces:** Images ARM64, container/network/volume/Compose, tài liệu tái chạy được và bằng chứng nghiệm thu.

Chia phần U thành năm buổi; kết quả mỗi buổi được dùng ngay ở buổi sau:

1. **Image và đóng gói — 60–90 phút:** người dùng viết hai Dockerfile và `.dockerignore`, hiểu build context, layer/cache/tag và ARM64; tự build frontend/backend. Phân biệt public config Next.js tại build-time với secret backend tại run-time. Kiểm tra image đúng kiến trúc, không chứa `.env` thật hay tệp upload.
2. **Container — 60–90 phút:** tự tạo/chạy/liệt kê/dừng/start/restart/logs/exec/inspect/xóa container ứng dụng; hiểu process và port mapping. Frontend/backend boot được; lỗi thiếu env có thông báo đủ chẩn đoán và không lộ secret.
3. **Volume — 90 phút:** phân biệt bind mount code với named volume PostgreSQL; tự tạo lại container DB nhưng giữ dữ liệu. Tự backup và restore vào DB/volume thử nghiệm riêng; kiểm tra users/analyses/reports và liên kết, không chỉ kiểm tra file backup tồn tại. Xác nhận trước mọi thao tác xóa dữ liệu.
4. **Network — 60–90 phút:** nối frontend/backend/PostgreSQL, phân biệt DNS service, port nội bộ/host và localhost. Trình duyệt dùng origin host; lời gọi server/container dùng tên service theo cấu hình. Kiểm tra kết nối từ đúng vị trí, không dùng hostname `backend` như URL mà trình duyệt trên host phải tự phân giải.
5. **Compose, troubleshooting và nghiệm thu — 90–120 phút:** người dùng viết compose, health/readiness và thứ tự start, áp dụng migration/seed theo quy trình đã ghi; tự up/status/logs/rebuild/down và xử lý backend/DB chưa sẵn sàng. Chạy toàn bộ backend API/security tests và Playwright với stack thật, không-key, sau đó repeat walkthrough sau restart.

- [ ] Người dùng hoàn thành buổi 1–2 và gửi bằng chứng images/containers; agent đọc và giải thích lỗi, không build/chạy thay.
- [ ] Người dùng hoàn thành buổi 3–4 và gửi bằng chứng persistence/restore/network đã loại dữ liệu riêng; bản backup thử nghiệm không thay thế policy backup production.
- [ ] Người dùng hoàn thành buổi 5; tests và kiểm tra sống qua restart đều đạt; fallback OCR/URL/AI vẫn hiện đúng.
- [ ] Người dùng cập nhật docs với lệnh thật đã kiểm chứng, env example không-secret, OpenAPI và schema/migration thực tế; kiểm tra bắt đầu từ môi trường sạch hoặc ghi rõ điều kiện máy cần có.
- [ ] **Đạt khi:** đầy đủ tiêu chí mục 18; không hardcoded backend response; rule-only/demo không cần credential; backup/restore đã được kiểm tra; mọi điểm dừng trước có bằng chứng.

**Giám sát vừa đủ:** operational logs có request context nhưng không log text/ảnh/credential, và health/readiness phục vụ chẩn đoán Compose. Người dùng triển khai các phần này trong U. Không thêm Prometheus/Grafana, dashboard giám sát hoặc CI/CD vì prompt không yêu cầu.

**Tác động cần giải thích trong bài học:** container khác image; xóa container khác xóa volume; restart khác rebuild; startup order khác ready; `docker compose down -v` có thể xóa dữ liệu volume của stack nên không đưa vào bài thực hành như lệnh dọn dẹp mặc định.

**Hành động nhỏ lúc bắt đầu:** mở Dockerfile frontend và xác định app cần những file nào trong build context.

## 16. Quy chuẩn cho bài hướng dẫn tại mỗi điểm dừng U

Agent soạn bài hướng dẫn khi tới đúng checkpoint, dựa trên file và phiên bản thật lúc đó. Không bỏ qua phần học vì kế hoạch đã liệt kê đầu ra.

Mỗi bài hướng dẫn phải có:

1. **Mục tiêu, trạng thái và điều kiện:** giai đoạn hiện tại, kết quả đầu vào đã kiểm tra, việc người dùng cần làm; file nào vẫn rỗng và công cụ nào đã có.
2. **Khái niệm gắn với JobShield:** dữ liệu đi qua file nào; lựa chọn và lý do; các tham số và ranh giới host/container/client/server nếu có.
3. **Các bước 2–5 phút:** một hành động mỗi bước; đường dẫn chính xác, vị trí sửa, nội dung cần nhập/lệnh cần chạy, working directory, thời gian; code/config chỉ là nội dung hướng dẫn để người dùng tự áp dụng, agent không ghi vào file thực thi.
4. **Kết quả và chẩn đoán:** output mong đợi chứng minh điều gì; lỗi thường gặp, cách phân biệt nguyên nhân; tác động tới dữ liệu/chi phí/quyền. Secret dùng giá trị minh họa; không yêu cầu dán key/session/ảnh có thông tin cá nhân vào chat.
5. **Điểm kiểm tra và bước nhỏ:** người dùng gửi output đã làm sạch, agent giải thích rồi mới chuyển tiếp. Với thao tác phá hủy: nêu rõ dữ liệu mất, backup/hoàn tác và yêu cầu xác nhận trước bước đó.

Không biến mỗi checkbox ở kế hoạch giai đoạn thành một lệnh chạy hàng giờ. Checklist ở đây là các đầu ra để theo dõi; buổi học mở chúng thành bước ngắn và dừng tại bằng chứng rõ ràng.

**Quy tắc kiểm tra và commit:** phần A logic mới có test nhỏ, fail vì hành vi thiếu → code tối thiểu → pass; không tạo test chỉ lặp lại cấu trúc code. Phần U do người dùng tự viết/chạy test và xem diff. Sau mỗi deliverable đã đạt, lưu một commit có phạm vi rõ; không commit source rỗng như thể đã hoàn thành, không stage env/credential, không thay quyền/DB trong một commit chỉ mô tả UI. Lệnh commit cụ thể dùng danh sách file thật ở thời điểm thực hiện, không `git add .` mù quáng.

## 17. Bảng phủ yêu cầu và kiểm tra

| Yêu cầu trong prompt | Giai đoạn sở hữu | Bằng chứng nghiệm thu |
| --- | --- | --- |
| Kiến trúc và stack tương thích ARM64 | G1, G11 | requirements/architecture, runtime/lockfile, image architecture |
| DB chuẩn hóa, PK/FK/constraint/index/timestamp/migrations | G2, G3, G9, G10 | ERD, schema thật, migration/test DB |
| Auth và ba vai trò | G3, G8–G10 | test_authentication.py, test_authorization.py, e2e/auth.spec.ts |
| Trích xuất text và 11 trường nghiệp vụ | G4 | test_extraction.py, fixture đủ/thiếu trường |
| Tám nhóm indicator, configurable rules, triggered evidence | G4, G10 | test_rule_engine.py, rule management E2E |
| Score giải thích/tái lập, không phải xác suất, confidence tách biệt | G4, G5, G7 | test_risk_assessment.py, test_missing_information.py, analysis-results.test.tsx |
| Employer DB: domains/pages/contacts/evidence/timestamps | G2–G4, G10 | seed/model, test_employer_verification.py, employer-management E2E |
| Matched/conflicting/not verified/insufficient data, không suy ra tin thật | G4, G5, G10 | test_employer_verification.py, employer-verification.spec.ts |
| OCR, text editing fallback | G6 | test_extraction_failures.py, analysis-inputs.spec.ts |
| Public URL extraction, blocked/unsupported, không vượt hạn chế | G6 | test_url_safety.py, test_extraction_failures.py, analysis-inputs.spec.ts |
| LLM abstraction, một provider, env config, no-key/failure fallback | G7 | test_ai_fallback.py, env example, kết quả rule-only |
| Không bịa chứng cứ/domain/nguồn, input injection không nâng quyền | G4, G7, G10 | extraction/fallback/moderation tests, snapshot kết quả |
| Public pages: landing/analyze/results/verify/safety/login/register | G3, G5, G6, G7, G10 | component tests và walkthrough public |
| User pages: dashboard/history/saved/reports/new/reports/profile | G8, G9 | user-dashboard.spec.ts, reports.spec.ts |
| Admin pages: dashboard/moderation/employers/rules | G9, G10 | admin-moderation.spec.ts, admin-management.spec.ts |
| Reports/evidence/five statuses/notes/audit | G9 | test_reports.py, test_moderation.py, test_report_transitions.py |
| Evidence-backed public warnings, không tự public report | G9, G10 | moderation/privacy tests, public warning response |
| Total analyses, queue, risk distribution, moderation history | G8, G10 | test_statistics.py, DB đối chiếu stats, dashboard E2E |
| API validation/errors/pagination/OpenAPI | G2–G10 | contract/docs/api.md, integration tests theo module |
| Hashing/session/RBAC/secure errors/secrets | G3 và mọi API mới | authentication/authorization/privacy tests |
| Upload size/type, SSRF/URL safety, rate limits | G4, G6 | upload/url tests và kiểm tra giới hạn API |
| Personal-data access, retention, minimize external data, disclosure | G2, G3, G6–G10 | test_privacy.py, expiry/cleanup tests do người dùng bổ sung, UI consent |
| Synthetic advertisements/companies/sources/indicators/reports | G2, G3, G9, G10 | fixture/seed demo có nhãn, nạp lại không trùng |
| Test sáu tình huống spec và không tự xác nhận gian lận | G4–G7, G9–G11 | unit/integration/E2E kết quả có expected statuses |
| Full source/front/back/DB/API/AI/Docker/env/seed/tests/docs | G1–G11 | checklist mục 18, repository không còn module bắt buộc chỉ là khung |
| README install/env/start/migration/seed/tests/demo/AI | G1, G3, G7, G11 | người dùng thực hiện đúng lệnh đã ghi và báo kết quả |

Các test nghiệp vụ còn khung hoặc todo; G1 chỉ có self-check toolchain/shell/config và regression 404 thực thi. Bảng này phân bổ coverage sản phẩm sẽ thực hiện, không tuyên bố các case đó đã đạt. Trong G3/G6/G8/G9, người dùng bổ sung case TTL/cleanup/backup theo policy G2 vào `test_privacy.py` và test DB tương ứng; agent không tự chạy xóa dữ liệu để kiểm tra.

## 18. Tiêu chí hoàn thành dự án

Chỉ đánh dấu sau G11 khi có bằng chứng; mỗi nhóm có tối đa năm tiêu chí để dễ theo dõi.

**Luồng sản phẩm**

- [ ] Đăng ký/login/logout thật; guest phân tích và đọc kết quả đúng quyền.
- [ ] Text/ảnh/URL cho kết quả hoặc fallback rõ; score/indicator/explanation/evidence có cấu trúc.
- [ ] Xác minh employer phân biệt nguồn khớp, xung đột, chưa xác minh và thiếu dữ liệu.
- [ ] User lưu/lịch sử/profile/dashboard, gửi và theo dõi report; admin duyệt/nguồn/rule/thống kê.
- [ ] Cảnh báo public có chứng cứ, không public report riêng; mọi màn hình tiếng Việt và responsive.

**Dữ liệu và an toàn**

- [ ] PostgreSQL lưu dữ liệu thật qua restart; migration và seed được người dùng kiểm chứng.
- [ ] Dữ liệu demo có nhãn, không đóng vai nguồn xác minh thực tế hoặc vụ gian lận đã xác nhận.
- [ ] Auth/RBAC/ownership/upload/SSRF/rate-limit/retention/privacy tests đạt.
- [ ] Score tái tạo được từ dữ liệu có cấu trúc và rule snapshot; confidence khác risk; thiếu dữ liệu không thành an toàn.
- [ ] Không key AI vẫn chạy core và demo; failure không bịa chứng cứ; gửi dữ liệu ngoài có consent và giảm dữ liệu riêng.

**Khả năng chạy và bàn giao**

- [ ] Unit/component, backend integration/security và Playwright có kết quả thật phù hợp chủ sở hữu A/U.
- [ ] Images ARM64, Compose và network hoạt động; phân biệt startup/ready, build-time/run-time.
- [ ] Có kiểm tra named volume và backup/restore vào môi trường thử nghiệm; không xóa volume thật để chứng minh bài học.
- [ ] README đủ install/env/start/migration/seed/tests/demo/AI; architecture/API docs khớp phần đã triển khai.
- [ ] Không frontend/backend response giả thay chức năng bắt buộc; các file khung không dùng vẫn được giải thích hoặc bỏ khi không cần.

## 19. Tự rà soát kế hoạch và phạm vi chưa làm

**Coverage:** mục 17 bao phủ module, trang, entity, API/security, test, demo và deliverable của `prompt.txt`; mỗi giai đoạn kết thúc ở U. G1–G3 tương ứng thiết kế/nền backend, G4 phân tích, G5 frontend, G6–G7 mở rộng phân tích, G8–G10 báo cáo/quản trị/tích hợp, G11 test/đóng gói. Test được làm cùng chức năng thay vì dồn toàn bộ tới cuối.

**Phụ thuộc:** không integration trước contract; không lưu riêng trước quyền; không upload/URL trước kiểm tra an toàn; không LLM trước rule-only; không xuất bản trước moderation; không Compose toàn stack trước ứng dụng đủ chức năng. Docker PostgreSQL ở G3 chỉ là lựa chọn phục vụ DB; bài build ứng dụng nằm ở G11.

**Interfaces:** chữ ký thuần 4A/9A có chủ sở hữu rõ. DB/API shapes chỉ được người dùng chốt ở G2; nếu đổi khi triển khai, cập nhật tài liệu, caller và test liên quan trong cùng task, không để UI tự đoán. Các milestone U sinh output cụ thể cho milestone sau, không ghi “tích hợp sau” không có điểm nghiệm thu.

**Review Focus:** thiếu dữ liệu và mạo danh được kiểm tra G4/G5; quyền ID/guest ở G3/G5/G8/G9; lỗi OCR/URL/LLM ở G6/G7; thiếu evidence/concurrent moderation/publication ở G9/G10.

**Chưa làm trong lần lập kế hoạch:** chưa cài/chọn phiên bản thực tế, viết/chạy app hoặc tests, thiết kế hợp đồng triển khai thay người dùng, tích hợp provider thật, build Docker, deploy, CI/CD hoặc hệ giám sát riêng. Hoàn thành G11 chỉ xác nhận MVP local theo prompt; chưa đồng nghĩa đã nghiệm thu vận hành production công khai.

**Bước tiếp theo:** đọc bảng giai đoạn ở mục 3 trong 2 phút và xác nhận thứ tự cùng điểm dừng tự học phù hợp; sau đó bắt đầu G1, không triển khai toàn bộ kế hoạch trong một lượt.
