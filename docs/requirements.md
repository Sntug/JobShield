# JobShield — yêu cầu sản phẩm

Đọc ba luồng sử dụng ở mục 3 trước khi triển khai một chức năng.

**Nguồn:** nội dung `prompt.txt` đã đọc trong phiên lập kế hoạch ngày 14/10/2026; quy tắc dự án do người dùng cung cấp trong chat; [kế hoạch xây dựng](superpowers/plans/2026-10-14-jobshield-phased-build.md).

**Trạng thái nguồn tại G1:** `prompt.txt` và `AGENTS.md` hiện không có trên đĩa. Đây là bản yêu cầu được tổng hợp từ nội dung đã đọc, không phải bản sao nguyên văn của một file vừa được kiểm tra. Khi các file nguồn được cung cấp lại, đối chiếu thay đổi trước khi cập nhật phạm vi.

**Phạm vi lần thực hiện hiện tại:** chỉ G1. Tài liệu này mô tả đích sản phẩm của cả dự án; việc một yêu cầu xuất hiện ở đây không cho phép tự triển khai giai đoạn sau.

## 1. Mục tiêu và giới hạn của đánh giá

JobShield giúp người tìm việc phân tích thông tin tuyển dụng, phát hiện dấu hiệu đáng ngờ, đối chiếu nguồn nhà tuyển dụng và quyết định những bước xác minh cần làm trước khi ứng tuyển. Người dùng chính gồm sinh viên, người mới tốt nghiệp, người tìm thực tập, việc bán thời gian và người tìm việc trực tuyến; nhóm hỗ trợ gồm trung tâm nghề nghiệp, người quản trị tuyển dụng và kiểm duyệt viên.

Đây là công cụ hỗ trợ đánh giá rủi ro. Không kết luận một doanh nghiệp hoặc tin tuyển dụng chắc chắn gian lận khi chưa có bằng chứng được kiểm chứng đầy đủ. Mọi kết quả phải phân biệt thông tin đã xác minh, dấu hiệu đáng ngờ, thông tin chưa xác minh và cảnh báo có nguồn đáng tin cậy.

Doanh nghiệp tồn tại không chứng minh tin tuyển dụng mang tên doanh nghiệp đó là thật. Người khác có thể mạo danh qua email, điện thoại, domain hoặc hướng dẫn chuyển tiền.

## 2. Vai trò

| Vai trò | Hành vi cần hỗ trợ |
| --- | --- |
| Khách | Phân tích tuyển dụng, đọc kết quả được phép truy cập, xem thông tin an toàn công khai |
| Người dùng đăng ký | Mọi hành vi của khách; lưu kết quả, lịch sử, gửi/theo dõi báo cáo, quản lý hồ sơ |
| Quản trị viên | Duyệt báo cáo, quản lý nguồn nhà tuyển dụng, quy tắc phát hiện và cảnh báo công khai; xem thống kê |

Quyền được kiểm tra ở backend. Layout hoặc việc ẩn nút trên frontend không thay thế phân quyền. Kết quả của khách cũng có thể chứa dữ liệu riêng; thiết kế cách truy cập và thời hạn lưu tại G2, triển khai tại G3–G5.

## 3. Ba luồng sử dụng

### 3.1. Phân tích tin tuyển dụng

1. Người dùng dán văn bản, chọn ảnh hoặc nhập URL tuyển dụng.
2. Hệ thống trích xuất thông tin; nếu ảnh/URL không đọc được, cho sửa hoặc dán văn bản thủ công.
3. Backend nhận diện trường dữ liệu, chạy rule, đối chiếu nguồn employer đã có; AI hỗ trợ khi được cấu hình và người dùng đồng ý gửi dữ liệu theo chính sách.
4. Kết quả trình bày risk, indicator, trích đoạn, nguồn, trạng thái xác minh, hạn chế và hành động cần làm.
5. Người dùng đăng ký có thể lưu kết quả; dữ liệu được lưu PostgreSQL và chỉ truy cập đúng quyền.

Các trường cần trích xuất: tên công ty, vị trí, lương, địa điểm, hình thức việc làm, email, điện thoại, website tuyển dụng, yêu cầu ứng tuyển, khoản thanh toán được yêu cầu và hướng dẫn đáng ngờ. Trường chưa có dữ liệu phải thể hiện là chưa biết; không tự bổ sung doanh nghiệp, domain hoặc bằng chứng.

### 3.2. Xác minh nhà tuyển dụng

Người dùng nhập thông tin employer; hệ thống đối chiếu kho nguồn được quản trị, gồm tên, domain, trang tuyển dụng chính thức, kênh liên hệ, chứng cứ và thời điểm xác minh. Kết quả giải thích sự khớp hoặc xung đột từ dữ liệu có sẵn, đồng thời giữ sự khác nhau giữa xác minh doanh nghiệp và xác minh tin cụ thể. Không dựng kết nối tới cơ sở dữ liệu chính phủ.

### 3.3. Báo cáo và kiểm duyệt

Người dùng đăng ký gửi báo cáo kèm bằng chứng. Hệ thống lưu trạng thái chờ duyệt; admin đọc bằng chứng, ghi notes và cập nhật quyết định có lịch sử. Người gửi theo dõi được kết quả. Báo cáo không tự biến thành cảnh báo đã xác minh hoặc nội dung công khai.

## 4. Các module bắt buộc

| Module | Kết quả cần có |
| --- | --- |
| Trích xuất | Text, ảnh/OCR và URL công khai; sửa văn bản khi OCR lỗi; xử lý trang bị chặn/không hỗ trợ; không vượt đăng nhập, CAPTCHA hoặc hạn chế truy cập |
| Rule và AI | Hai lớp hỗ trợ nhau; rule vẫn chạy khi không có key AI; ít nhất một LLM provider cấu hình được, có abstraction và fallback |
| Đánh giá rủi ro | Rule có thể cấu hình; lưu dấu hiệu kích hoạt và lý do; score giải thích/tái tạo được; không diễn đạt thành xác suất gian lận đã hiệu chuẩn |
| Employer verification | Kho nguồn, domain, trang tuyển dụng, contact, evidence, timestamps; admin thêm/cập nhật; đối chiếu trả trạng thái rõ |
| Báo cáo cộng đồng | Gửi bằng chứng, theo dõi trạng thái, notes và moderation history; bảo vệ dữ liệu cá nhân |
| Không gian người dùng | Phân tích gần đây, lịch sử, kết quả đã lưu, thống kê risk, báo cáo/trạng thái và hồ sơ |
| Quản trị | Tổng analyses, queue cần duyệt, phân bố risk, nguồn employer, rules, lịch sử kiểm duyệt và public warnings có chứng cứ |

Rule phải xét tám nhóm dấu hiệu: phí tuyển dụng trước, đặt cọc trước phỏng vấn, hứa thu nhập phi thực tế, nhiệm vụ có nạp/chi tiền, yêu cầu dữ liệu cá nhân nhạy cảm, chuyển tiền, kênh giao tiếp đáng ngờ và mạo danh tổ chức. Cần xét ngữ cảnh/phủ định, không chỉ thấy từ “phí” hoặc “CCCD” rồi khẳng định có rủi ro tương ứng.

## 5. Trạng thái và cách trình bày

| Loại | Trạng thái sản phẩm |
| --- | --- |
| Risk | Ít dấu hiệu rủi ro; rủi ro vừa; rủi ro cao; không đủ thông tin |
| Verification | Khớp nguồn đã xác minh; thông tin xung đột; chưa xác minh; không đủ dữ liệu |
| Report | Chờ duyệt; đang xem xét; chưa đủ bằng chứng; cảnh báo đã xác minh; bị từ chối |

Mã trạng thái truyền qua API được người dùng thiết kế tại G2. Nhãn người dùng phải bằng tiếng Việt. Risk và độ chắc chắn của xác minh là hai khía cạnh riêng; thiếu thông tin không phải bằng chứng an toàn. Quyết định report “cảnh báo đã xác minh” không tự cấp phép công khai nội dung riêng tư.

Trang kết quả là trang ưu tiên. Phải có các phần độc lập: đánh giá tổng thể, lý do, từng dấu hiệu và trích đoạn kích hoạt, kết quả đối chiếu, evidence/source/time, hạn chế của phương pháp và hành động xác minh đề xuất. Không chỉ trả một đoạn văn AI.

## 6. Toàn bộ trang cần có

| Nhóm | Trang | Vị trí file hiện có |
| --- | --- | --- |
| Công khai | Trang chủ | `frontend/src/app/(public)/page.tsx` |
| Công khai | Phân tích tuyển dụng | `frontend/src/app/(public)/analyze/page.tsx` |
| Công khai | Kết quả phân tích | `frontend/src/app/(public)/analysis/[id]/page.tsx` |
| Công khai | Xác minh nhà tuyển dụng | `frontend/src/app/(public)/verify-employer/page.tsx` |
| Công khai | Thông tin an toàn/cảnh báo đã xuất bản | `frontend/src/app/(public)/safety/page.tsx` |
| Công khai | Đăng nhập | `frontend/src/app/(public)/login/page.tsx` |
| Công khai | Đăng ký | `frontend/src/app/(public)/register/page.tsx` |
| Người dùng | Dashboard | `frontend/src/app/(user)/dashboard/page.tsx` |
| Người dùng | Lịch sử | `frontend/src/app/(user)/history/page.tsx` |
| Người dùng | Kết quả đã lưu | `frontend/src/app/(user)/saved/page.tsx` |
| Người dùng | Gửi báo cáo | `frontend/src/app/(user)/reports/new/page.tsx` |
| Người dùng | Báo cáo của tôi | `frontend/src/app/(user)/reports/page.tsx` |
| Người dùng | Hồ sơ | `frontend/src/app/(user)/profile/page.tsx` |
| Quản trị | Dashboard | `frontend/src/app/(admin)/admin/page.tsx` |
| Quản trị | Kiểm duyệt báo cáo | `frontend/src/app/(admin)/admin/reports/page.tsx` |
| Quản trị | Quản lý employer | `frontend/src/app/(admin)/admin/employers/page.tsx` |
| Quản trị | Quản lý rules | `frontend/src/app/(admin)/admin/rules/page.tsx` |

Giao diện cần sạch, dễ đọc, nhất quán, responsive và tiếp cận được bằng bàn phím. Trạng thái cần nhãn văn bản, không chỉ màu. Route group `(public)`, `(user)`, `(admin)` không xuất hiện trong URL và không tự bảo vệ quyền đọc dữ liệu.

## 7. Stack và ràng buộc kỹ thuật

| Phần | Công nghệ bắt buộc |
| --- | --- |
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui, React Hook Form, Zod, TanStack Query |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| Database | PostgreSQL, thiết kế quan hệ chuẩn hóa, constraint/index/timestamps và migration |
| AI/extraction | LLM API cấu hình được, rule engine, OCR |
| Hạ tầng local | Docker, Docker Compose; macOS Apple Silicon ARM64 |
| Kiểm tra | Pytest, frontend unit tests, Playwright end-to-end tests |

Dùng phiên bản stable tương thích. Yêu cầu mới nhất: Python mới nhất chỉ được cài trong venv, không cài ngoài venv hoặc đổi Python toàn máy. Backend G1 đã chốt CPython 3.15.0 ARM64 trong backend/.venv, pin .python-version cho project; toàn bộ dependency imports và settings tests đạt 12 passed. Python toàn máy vẫn 3.9.6. Ngoại lệ frontend/backend chỉ áp dụng cho thiết lập môi trường G1; các lĩnh vực tự học khác vẫn theo quy tắc đã cung cấp.

Các entity theo nguồn yêu cầu: users, roles, recruitment_analyses, recruitment_sources, extracted_job_information, risk_indicators, analysis_indicators, verified_employers, employer_sources, recruitment_reports, report_evidence, moderation_actions, saved_analyses. Có thể tinh chỉnh và bổ sung public_warnings khi thiết kế G2; tài liệu này không định nghĩa schema SQL hoặc migration.

API REST phải bao phủ authentication, recruitment analysis, OCR/extraction, risk assessment, employer verification, saved analyses, reports, administration và statistics. Có validation, lỗi có cấu trúc, pagination, authorization, rate limiting ở thao tác tốn chi phí và FastAPI OpenAPI. Hợp đồng cụ thể do người dùng tự thiết kế ở G2.

## 8. Bảo mật, dữ liệu và AI

| Ranh giới | Yêu cầu |
| --- | --- |
| Tài khoản | Hash mật khẩu an toàn, xác thực và phân quyền thực, admin APIs có role check |
| Đầu vào | Validation; kích thước/định dạng upload; URL an toàn và SSRF protection; rate limiting |
| Dữ liệu riêng | Quyền owner, ảnh/báo cáo không public mặc định, giữ dữ liệu tối thiểu, retention rõ |
| Secrets/errors | Secret qua môi trường; không lộ credential hoặc dữ liệu cá nhân trong lỗi/logs |
| Bên thứ ba | Thông báo dữ liệu có thể được gửi OCR/LLM; giảm dữ liệu nhạy cảm; consent theo thiết kế; timeout/fallback |

Không bịa bằng chứng, employer records, official domains hoặc kết quả xác minh bên ngoài. LLM hỗ trợ ngữ nghĩa và giải thích; không tự quyết định nguồn nào đã được kiểm chứng. Không có key hoặc provider không khả dụng thì rule engine vẫn hoạt động, đồng thời hiển thị hạn chế.

## 9. Test và demo

| Nhóm kiểm tra | Các trường hợp cần có |
| --- | --- |
| Nghiệp vụ | Extraction, rule matching, risk scoring, employer verification, thiếu thông tin, tính tái lập |
| Tài khoản/quyền | Register/login, auth/authorization, owner khác, admin-only, phiên khách/người dùng |
| Báo cáo | Submit Pending, moderation, evidence chưa đủ, lịch sử, không tự xuất bản |
| Đầu vào/provider | OCR/URL lỗi, upload/SSRF, no-key, LLM lỗi/timeout/output không hợp lệ |
| Giao diện/end-to-end | Component structured result và các luồng browser → API → PostgreSQL thật |

Các tình huống sản phẩm bắt buộc: tin trông hợp lệ; tin yêu cầu đóng phí; mạo danh công ty; tin không đầy đủ; tin đáng ngờ chưa có chứng cứ đã xác minh; OCR hoặc URL extraction thất bại. Không tình huống nào được tự nâng thông tin chưa xác minh thành gian lận đã xác nhận.

Seed/demo dùng tin tuyển dụng, doanh nghiệp, nguồn, indicator và report tổng hợp có nhãn rõ. Không gọi doanh nghiệp giả hoặc ví dụ là vụ gian lận đã xác minh ngoài đời. Demo phải chạy được không có external API credential; ảnh/URL không trích xuất được phải cho dán/sửa text, không tạo extraction response giả.

## 10. Deliverables và tiêu chí hoàn thành

| Nhóm bàn giao | Nội dung |
| --- | --- |
| Mã nguồn/chức năng | Source đầy đủ, frontend và backend hoạt động, API thật, business logic thật, auth và AI tùy chọn |
| Dữ liệu | PostgreSQL schema/migrations, seed tổng hợp và dữ liệu tồn tại qua khởi động lại |
| Môi trường | Docker Compose, Dockerfile, env examples không-secret, hướng dẫn chạy local |
| Kiểm chứng | Unit/component, API/DB/security và Playwright cho luồng quan trọng |
| Tài liệu | README install/env/start/migration/seed/test/demo/AI, architecture và API docs |

Hoàn thành khi người dùng đăng ký/login, gửi tin, nhận kết quả có giải thích, xác minh employer, xem/lưu kết quả, gửi/theo dõi report; admin duyệt và quản lý được; dữ liệu lưu PostgreSQL; frontend gọi backend thật; core hoạt động không AI trả phí; test quan trọng và lệnh local được kiểm chứng. Không dùng response hardcode để giả backend, không dừng ở UI hoặc cấu trúc file.

MVP local là đích nghiệm thu hiện tại. Không thêm cloud deployment, CI/CD, registry hoặc hệ Grafana/Prometheus nếu chưa có yêu cầu riêng.

## 11. Ai được thực hiện phần nào

| Agent được làm trực tiếp | Người dùng tự làm, agent chỉ hướng dẫn |
| --- | --- |
| Yêu cầu/kiến trúc sản phẩm, nội dung tiếng Việt, UI/component, trình bày dữ liệu đã có | Infrastructure, dependency/environment configuration, Docker và triển khai |
| Logic thuần không mạng/DB/quyền: extraction text, matching/scoring, đối chiếu nguồn được đưa vào, bảng chuyển trạng thái | Database/model/schema/SQL/Alembic/seed/backup/restore |
| Test của logic thuần và component khi có môi trường | API/schema request-response, frontend-backend integration, OCR/LLM providers |
| Rà soát read-only và giải thích kết quả | Authentication/authorization/secret/upload/URL/SSRF/rate limit/privacy/retention; operational logging/metrics/health và CI/CD |

Ranh giới xét theo hành vi, không theo đuôi file hoặc frontend/backend. Khi phần agent phụ thuộc bước người dùng chưa đạt, ghi phụ thuộc và chờ bằng chứng; không làm thay bằng script hay agent khác.

**Điểm dừng G1:** yêu cầu/kiến trúc và toolchain đã có bằng chứng theo hai ngoại lệ người dùng cho phép agent thiết lập môi trường. Frontend shell, TypeScript, Vitest/Chromium và build đã kiểm tra; backend import/Pytest/config đạt, Python 3.15.0 chỉ trong venv. Snapshot và kế hoạch có ngoại lệ Git ignore để được theo dõi; chưa commit. G1 không nghiệm thu chức năng sản phẩm, API/Database hoặc Docker. Các lĩnh vực tự học ở giai đoạn sau vẫn do người dùng thực hiện.
