# JobShield — thực hành G1

G1 đã đạt checkpoint kiến trúc/toolchain. Frontend chạy lại theo mục 10; backend theo mục 11. Python 3.15.0 chỉ nằm trong backend/.venv theo ràng buộc mới nhất; Python toàn máy không đổi. Mục 8 vẫn tạm hoãn 7 high braces; chưa chuyển G2.

## 1. Trạng thái và mục tiêu

**G1A:** tài liệu đã đạt. **G1U:** frontend và backend toolchain đã được thiết lập/kiểm tra theo hai ngoại lệ người dùng xác nhận. Backend Python mới nhất chỉ được cài trong venv; không đổi Python/PATH/alias toàn máy. Các bài thực hành cũ bên dưới lưu lại lịch sử; hướng dẫn hiện tại là mục 10–11. API, Database, auth và Docker chưa triển khai.

Rà soát lại G1: Vitest 1 passed/3 todo, Chromium 2 passed, TypeScript và build frontend đạt. Backend: Python 3.15.0 ARM64, SDK import/config tests 12 passed, manifest/lockfile khớp và pip check 30 packages đạt. Đây là nghiệm thu môi trường/shell G1, chưa nghiệm thu tính năng sản phẩm. 7 high braces frontend vẫn hoãn.

**Checkpoint chặng 1:** người dùng gửi `npm ls --depth=0`; kiểm tra chỉ đọc trên đĩa thấy manifest, lockfile và các package đã cài khớp. Phiên bản: Next 16.4.0; React/React DOM 19.3.0; TypeScript 7.0.2; @types/node 26.6.5; @types/react/@types/react-dom 19.3.0. Đây là bằng chứng cài package, không phải kết quả build/test.

**Thời gian:** 10–15 phút nếu kết nối npm registry bình thường. Cần trình soạn thảo, Terminal và Internet để tải package. Không cần DB, Docker engine, API key hoặc backend đang chạy.

Quan sát chỉ đọc ngày 14/10/2026:

| Công cụ | Output quan sát | Ý nghĩa |
| --- | --- | --- |
| Kiến trúc | `arm64` | Máy hiện chạy native Apple Silicon |
| Node.js | `v24.8.0` | Đã có runtime JS; đáp ứng floor Node 20.9 của Next hiện tại |
| npm | `11.6.0` | Dùng npm đã có, không thêm package manager Node thứ hai |
| uv | `0.11.14` | Đã có công cụ Python; chưa cài Python/backend dependencies |
| Docker CLI | `29.8.2` | Chỉ biết CLI hiện diện, chưa biết daemon/stack chạy được |

Yêu cầu Node tối thiểu và cách cài Next thủ công đã đối chiếu [tài liệu Next.js](https://nextjs.org/docs/app/getting-started/installation). Dòng Node 24 nằm trong LTS theo [lịch release chính thức](https://nodejs.org/en/about/previous-releases); phiên bản cụ thể đang cài không được coi là bản vá LTS mới nhất.

## 2. Manifest, dependency và lockfile là gì?

`frontend/package.json` mô tả frontend JobShield: tên project, lệnh khởi động/build và thư viện cần dùng. Trước chặng 1 file rỗng nên npm không thể đọc như JSON; hiện manifest đã được người dùng tạo hợp lệ.

`dependencies` gồm thư viện để ứng dụng hoạt động, như Next/React. `devDependencies` gồm công cụ phát triển/kiểm tra như TypeScript và kiểu dữ liệu của React/Node. npm ghi phiên bản vào manifest sau khi cài.

`package-lock.json` ghi toàn bộ cây dependency đã resolve; giữ file này trong Git để lần cài tiếp theo có thể tái tạo bằng `npm ci`. `node_modules/` là các package tải về, không phải mã nguồn cần commit. Ở chặng này dùng `--save-exact` để manifest ghi số phiên bản cụ thể; `@latest` chọn release theo tag npm tại lúc bạn cài, không tự chọn `canary` hoặc `beta`.

Các hành vi install/save/lockfile được mô tả trong [tài liệu npm install](https://docs.npmjs.com/cli/v11/commands/npm-install/). Tải package dùng mạng và dung lượng ổ đĩa; có thể chạy lifecycle script của dependency. Không gửi dữ liệu tuyển dụng hoặc credential JobShield trong các lệnh dưới đây.

## 3. Chặng thực hành — nền frontend

### Bước 1: vào đúng thư mục (1 phút)

Trong Terminal của bạn chạy:

```bash
cd /Users/sontung/Documents/GitHub/JobShield/frontend
pwd
node --version
npm --version
```

**Mong đợi:** `pwd` đúng thư mục frontend; Node/npm có phiên bản như bảng hoặc bản bạn đang dùng trong Terminal. Kết quả khác Terminal của agent có thể do PATH khác; nếu không có Node/npm thì dừng chặng và gửi lỗi, không cài dependency vào thư mục khác.

### Bước 2: nhập manifest tối thiểu (2–3 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/package.json`. File đã được kiểm tra đang rỗng; nhập toàn bộ nội dung:

```json
{
  "name": "jobshield-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  }
}
```

`private: true` ngăn publish package nhầm. `dev` chạy môi trường phát triển, `build` tạo bản build, `start` chạy bản đã build; chúng mới là tên lệnh, chưa chứng minh app có thể chạy.

Vẫn trong thư mục frontend, kiểm tra JSON bằng Node đã có:

```bash
node -e 'const fs = require("node:fs"); const p = JSON.parse(fs.readFileSync("package.json", "utf8")); console.log(p.name, p.private, p.scripts.dev)'
```

**Mong đợi:** `jobshield-frontend true next dev`. Điều này chứng minh file có cú pháp JSON hợp lệ và các trường vừa nhập đọc được. Nếu `Unexpected end` thì file chưa lưu hoặc đang trống; nếu lỗi gần dấu phẩy thì sửa cú pháp JSON, không chạy install trước khi kiểm tra này đạt.

### Bước 3: cài thư viện ứng dụng (2–5 phút)

Trong `/Users/sontung/Documents/GitHub/JobShield/frontend`, chạy:

```bash
npm install --save-exact next@latest react@latest react-dom@latest
```

Next làm routing/rendering/build; React/React DOM là nền component và hiển thị. Cách cài ba package này dùng [manual installation của Next.js](https://nextjs.org/docs/app/getting-started/installation#manual-installation).

**Mong đợi:** lệnh thoát thành công; có `dependencies` với phiên bản số cụ thể trong manifest, `package-lock.json` và `node_modules/`. Số package phụ thuộc có thể thay đổi; không đối chiếu bằng một số lượng cố định. Nếu có `ERESOLVE`, dừng và gửi lỗi dependency; không dùng `--force` hoặc `--legacy-peer-deps` để che xung đột.

### Bước 4: cài công cụ TypeScript (2–5 phút)

Vẫn trong frontend:

```bash
npm install --save-dev --save-exact typescript @types/node @types/react @types/react-dom
```

TypeScript kiểm tra kiểu; ba package `@types` cung cấp thông tin kiểu cho Node và React. `--save-dev` đặt chúng trong `devDependencies`, `--save-exact` giữ phiên bản cụ thể.

**Mong đợi:** lệnh thành công; manifest có bốn devDependencies và lockfile được cập nhật. Đây chưa phải cấu hình TypeScript hoàn chỉnh: `tsconfig.json` hiện rỗng và sẽ được người dùng thiết lập ở chặng sau.

### Bước 5: gửi bằng chứng package tree (1 phút)

Vẫn trong frontend:

```bash
npm ls --depth=0
git status --short
```

**Mong đợi:** thấy next, react, react-dom, typescript và ba package @types, không có `invalid`/`UNMET DEPENDENCY`. `git status` phản ánh manifest/lockfile đã thay đổi. Nếu node_modules xuất hiện là untracked, không stage nó; người dùng sẽ bổ sung ignore cho output môi trường ở chặng cấu hình. Không dùng `git add .` ở đây.

Gửi output `npm ls --depth=0`. Agent sẽ đọc kết quả, ghi phiên bản thật và hướng dẫn chặng cấu hình Next/TypeScript/Tailwind/shadcn và test runner theo các package đã cài. Chưa chạy `npm run dev`, `build` hoặc kết luận G1 hoàn tất vì layout/page/config hiện vẫn là file khung.

## 4. Lỗi thường gặp trong chặng này

| Lỗi | Chẩn đoán và cách xử lý |
| --- | --- |
| `EJSONPARSE` | Manifest rỗng hoặc sai JSON; chạy kiểm tra ở bước 2 và sửa chỗ parser báo |
| `ENOENT package.json` hoặc đường dẫn lạ | `pwd` sai; trở về frontend JobShield trước khi chạy npm |
| `ERESOLVE` | Peer dependencies xung đột; gửi output và phiên bản, không bỏ qua bằng force |
| `ENOTFOUND`/timeout registry | Kết nối DNS/mạng hoặc registry; kiểm tra lại mạng và `npm config get registry`, không đổi nguồn tải tùy tiện |
| `EACCES` | Thư mục/cache có quyền không phù hợp; gửi đường dẫn lỗi đã loại thông tin riêng, không dùng sudo để cài package project |

## 5. Phần G1 còn phải kiểm chứng

| Chặng | Bằng chứng cần có | Trạng thái |
| --- | --- | --- |
| Nền frontend | Manifest/lockfile và package tree hợp lệ | Đạt: output người dùng và file trên đĩa khớp |
| Next/TypeScript/Tailwind và shadcn | Trang shell có styles; component shadcn nạp được | Đạt: browser test kiểm tra heading, CSS và Tab focus |
| Vitest/Playwright | Self-check component và browser kiểm tra shell/route khung | Đạt: 1 unit và 2 browser tests; 3 test nghiệp vụ còn todo |
| Python/backend/Pytest | Phiên bản được người dùng chọn, environment/import và self-check Pytest | Đạt: Python 3.15.0 chỉ trong venv, 12 tests passed |
| Environment/secret convention | Public frontend config khác backend secret, env examples, ignore và lỗi thiếu config | Đạt: examples/ignore, required DATABASE_URL và SecretStr; chưa kết nối DB |

Tài liệu chặng sau đối chiếu [Vitest với Next.js](https://nextjs.org/docs/app/guides/testing/vitest) và [Tailwind với Next.js](https://tailwindcss.com/docs/installation/framework-guides/nextjs). Theo mặc định người dùng tự thiết lập environment; hai ngoại lệ G1 đã cho phép agent làm frontend/backend, không mở rộng sang các lĩnh vực tự học ở giai đoạn sau.

## 6. Chặng 2 — chạy trang shell Next.js và Tailwind

**Mục tiêu:** mở `/` thấy trang kiểm tra môi trường JobShield bằng tiếng Việt, Tailwind có hiệu lực và refresh được. Đây là trang shell kiểm tra toolchain; chưa có phân tích, backend hoặc dữ liệu sản phẩm.

**Trạng thái lúc bắt đầu chặng 2:** chặng 1 đạt; các config, root layout, public home page và CSS còn rỗng. **Checkpoint hiện đã đạt:** các file này có nội dung, `.next` đã được sinh; người dùng đã sửa lỗi chép Markdown vào layout và xác nhận trang `/` có styles. Các bước dưới đây lưu lại bài thực hành đã làm; tiếp tục chặng 3 ở mục 7.

**Điều kiện khi thực hành chặng 2:** Node/npm dùng được, Internet để tải Tailwind và không chạy trùng dev server JobShield. Khoảng **25–35 phút** cho cả chặng, chia thành hai phần dưới đây. Khi nhập nội dung code vào file, chỉ chép phần bên trong khối mã; các dòng Markdown mở/đóng khối như ` ```tsx ` và ` ``` ` không thuộc source code.

Next đã cài cần Node >=20.9; Node 24 đang có đáp ứng floor này. React/React DOM 19.3.0 khớp peer dependencies trên đĩa. Next 16.4 hỗ trợ [TypeScript 7 qua project-local CLI](https://nextjs.org/docs/app/api-reference/config/typescript#using-typescript-7); giữ TypeScript 7.0.2. Không thêm cấu hình bỏ qua lỗi type để làm bước kiểm tra thành công.

### Phần A — dependency và cấu hình (12–18 phút)

#### Bước 1: bổ sung ignore cho output môi trường (2 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/.gitignore`; thêm đoạn sau vào cuối, giữ nguyên những dòng hiện có:

```gitignore
/frontend/node_modules/
/frontend/.next/
/frontend/out/
/frontend/coverage/
/frontend/playwright-report/
/frontend/test-results/
*.tsbuildinfo
.env.*
!.env.example
```

`node_modules` là thư viện tải về, `.next` là output/cache Next, các thư mục test sẽ được dùng ở chặng kiểm tra. File môi trường local không vào Git; ngoại lệ giữ `.env.example` chứa giá trị minh họa. **Giữ dòng `.env` đã có bên cạnh `.env.*`: `.env.*` không khớp tên file đúng `.env`.** Không đổi nội dung env hoặc đưa secret vào file example trong chặng này.

Trong Terminal, từ gốc dự án chạy:

```bash
cd /Users/sontung/Documents/GitHub/JobShield
git check-ignore frontend/node_modules/ frontend/.next/
git check-ignore .env frontend/.env.local
git status --short
```

**Mong đợi:** hai lệnh check-ignore lần lượt in các đường dẫn output và `.env`/`frontend/.env.local`; node_modules không còn xuất hiện như thư mục untracked. `frontend/package.json` và `frontend/package-lock.json` vẫn là thay đổi cần giữ. Ignore không xóa package đã tải và không tự bỏ tracking của file đã commit trước đó.

#### Bước 2: cài Tailwind và căn kiểu Node theo runtime (2–5 phút)

Trong frontend chạy:

```bash
cd /Users/sontung/Documents/GitHub/JobShield/frontend
npm install --save-dev --save-exact tailwindcss@4 @tailwindcss/postcss@4 postcss @types/node@24
```

Tailwind 4 tạo CSS từ class trên component; PostCSS đưa bước xử lý đó vào Next. `@types/node@24` căn các khai báo API Node với runtime Node 24 đang dùng; nó không nâng/hạ runtime Node. `--save-exact` giữ số phiên bản patch được resolve trong manifest/lockfile.

**Mong đợi:** lệnh thành công, thêm ba package CSS, @types/node thuộc major 24. Nếu có lỗi resolve/download, dừng và gửi lỗi đầu tiên; không đi tiếp với package chưa cài được. Cấu hình CSS dưới đây theo [hướng dẫn Tailwind 4 cho Next](https://tailwindcss.com/docs/installation/framework-guides/nextjs).

#### Bước 3: thiết lập TypeScript (3–5 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/tsconfig.json`; file hiện rỗng, nhập:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "react-jsx",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts",
    ".next/dev/types/**/*.ts"
  ],
  "exclude": ["node_modules"]
}
```

`strict` kiểm tra kiểu chặt; `noEmit` để Next xử lý build thay vì TypeScript tự xuất JS; `bundler` giải quyết import theo bundler; alias `@/` trỏ `src/`; `react-jsx` dùng React automatic runtime. Include giữ types Next tự sinh. Không cần `baseUrl` cho mapping này.

Trong frontend kiểm tra cú pháp:

```bash
node -e 'const fs = require("node:fs"); const c = JSON.parse(fs.readFileSync("tsconfig.json", "utf8")); console.log(c.compilerOptions.strict, c.compilerOptions.moduleResolution)'
```

**Mong đợi:** `true bundler`. Đây là kiểm tra JSON/giá trị cấu hình, chưa là type check toàn dự án. Cấu hình được đối chiếu với default của Next 16.4 đã cài và [tài liệu TypeScript Next](https://nextjs.org/docs/app/api-reference/config/typescript).

#### Bước 4: nhập cấu hình Next tối thiểu (2 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/next.config.ts`; nhập:

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {};

export default nextConfig;
```

Next nhận default export làm cấu hình. Object rỗng nghĩa là dùng defaults; chưa có proxy API, auth hoặc biến môi trường backend. Giữ tên file khung hiện có; không tạo thêm next.config.js song song.

**Mong đợi:** file có đúng một default export, không bị để trống. Khả năng Next nạp file được kiểm tra lúc khởi động ở phần B.

#### Bước 5: nối Tailwind qua PostCSS (2 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/postcss.config.mjs`; nhập:

```javascript
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

`.mjs` là module JS dùng export; plugin PostCSS của Tailwind 4 sẽ xử lý CSS ở bước render/build. Không dùng cú pháp plugin Tailwind 3 với package Tailwind 4.

Trong frontend kiểm tra module:

```bash
node --input-type=module -e 'const { default: c } = await import("./postcss.config.mjs"); console.log(Object.keys(c.plugins))'
```

**Mong đợi:** danh sách chứa `@tailwindcss/postcss`. Lệnh chứng minh config JS nạp được, chưa chứng minh CSS đã render.

### Phần B — trang shell và kiểm tra trình duyệt (10–15 phút)

#### Bước 6: nhập CSS đầu vào (1 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/src/app/globals.css`; nhập:

```css
@import "tailwindcss";
```

Đây là CSS gốc dùng cho toàn frontend; plugin ở bước 5 xử lý import này. Cú pháp theo Tailwind 4. Hiệu lực được kiểm tra bằng layout và màu của trang shell ở bước 10.

#### Bước 7: nhập root layout (2–3 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/src/app/layout.tsx`; nhập:

```tsx
import type { ReactNode } from "react";
import "./globals.css";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
```

Root layout bọc mọi trang; import CSS đưa styles vào ứng dụng; `lang="vi"` giúp trình duyệt và công cụ hỗ trợ nhận biết tiếng Việt. Chưa viết user/admin layout hoặc guard trong chặng này.

**Mong đợi:** root layout có `<html>`, `<body>` và render children, đáp ứng [yêu cầu root layout của Next](https://nextjs.org/docs/app/getting-started/installation#create-the-app-directory).

#### Bước 8: nhập trang chủ kiểm tra môi trường (2–3 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/src/app/(public)/page.tsx`; nhập:

```tsx
export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <p className="text-sm font-medium text-emerald-700">
        Kiểm tra môi trường frontend
      </p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight">JobShield</h1>
      <p className="mt-4 text-base text-slate-700">
        Next.js, React và Tailwind đang được kiểm tra trong G1.
      </p>
      <p className="mt-2 text-sm text-slate-600">
        Các chức năng phân tích và xác minh chưa được triển khai.
      </p>
    </main>
  );
}
```

`(public)` chỉ là route group nên trang này nằm ở `/`, không phải `/(public)`. Class Tailwind tạo độ rộng, khoảng cách, kích thước chữ và màu; đây là dấu hiệu dễ thấy để kiểm tra CSS. Không thêm trang `src/app/page.tsx` thứ hai trùng route `/`.

#### Bước 9: tự khởi động dev server (1–2 phút)

Trong Terminal, từ frontend chạy:

```bash
npm run dev
```

**Mong đợi:** Next nạp config, thông báo ready và URL local. Giữ Terminal này mở; đọc đúng URL/port Next in ra nếu 3000 đang bận. Next tự sinh `next-env.d.ts` và `.next` khi cần; không tự viết types generated này. Chúng là output toolchain, không bằng chứng hoàn thành sản phẩm.

Nếu port 3000 báo bận, dùng port Next chọn hoặc dừng dev server cũ do bạn quản lý; không kill tiến trình khác chỉ để lấy port. Nếu Next báo parse/config error, gửi lỗi đầu tiên kèm tên file được nêu, không tắt type check hay validation.

#### Bước 10: kiểm tra trang và gửi kết quả (2 phút)

Mở URL local Next đã in trong trình duyệt của bạn; truy cập `/`. **Mong đợi:** tiêu đề JobShield lớn, nhãn “Kiểm tra môi trường frontend” màu xanh, nội dung có khoảng cách; không có màn hình error overlay. Refresh một lần; trang vẫn hiển thị, Terminal trả request `/` thành công.

Sau khi kiểm tra, dừng server bằng `Ctrl+C` trong Terminal đã chạy nó. Từ frontend chạy:

```bash
npm ls --depth=0
```

Gửi đoạn startup/request `/` trong Terminal và output package tree; ghi một câu xác nhận trang có styles hay gặp lỗi. Không cần dán `.env`, cookie hoặc dữ liệu cá nhân.

**Giới hạn kiểm tra:** các route khác vẫn là file khung, nên chưa dùng `npm run build` hoặc việc `/` hiển thị làm bằng chứng cả frontend hoàn thành. Không bỏ qua lỗi build/type của route khung; chúng sẽ được triển khai và nghiệm thu đúng giai đoạn.

### Chẩn đoán nếu chưa đạt

| Hiện tượng | Kiểm tra cụ thể |
| --- | --- |
| Parse error ở tsconfig/postcss | Chạy lại lệnh kiểm tra bước 3/5; xem file đã lưu đúng nội dung chưa |
| Không tìm thấy @tailwindcss/postcss | `npm ls --depth=0` có package không; đã chạy install trong frontend chưa |
| Trang có text nhưng không có styles | globals có import Tailwind, root layout có import globals, PostCSS đúng plugin; restart server sau khi sửa config |
| Trang `/` yêu cầu default export/layout | Kiểm tra đúng root layout và `(public)/page.tsx`, không tạo home page trùng route |
| Trình duyệt không vào được | Dùng URL/port trong startup output; Terminal server còn chạy, không mở service name của container |

**Điểm kiểm tra hiện tại:** trang shell `/` chạy có styles và output startup/package tree. Sau khi đạt, học tiếp shadcn/ui, form/query dependencies và Vitest/Playwright self-check. G1U vẫn cần backend/Python và quy ước environment trước khi được đánh dấu hoàn tất.

**Hành động tiếp theo dưới 2 phút:** thêm ignore ở bước 1 của chặng 2; giữ manifest và lockfile.

## 7. Chặng 3 — shadcn/ui, form và query dependencies

**Mục tiêu:** thêm được một Button của shadcn vào trang shell; manifest có React Hook Form, Zod và TanStack Query cho các giai đoạn sau. Chưa nối API, chưa thiết lập auth và chưa làm form sản phẩm trong chặng này.

**Đầu vào đã đạt:** Next 16.4.0, React/React DOM 19.3.0, TypeScript 7.0.2; Tailwind/@tailwindcss/postcss 4.3.3, postcss 8.5.30 và @types/node 24.19.2; trang `/` có styles theo xác nhận người dùng. Ignore đã bao phủ `.env`, `.env.local` và outputs, vẫn cho phép `.env.example`.

**Thời gian:** 15–20 phút. Cần Internet để CLI tải package/component. Nếu dev server còn chạy, dừng bằng `Ctrl+C` trong Terminal bạn đã chạy nó trước khi cập nhật toolchain; mở lại ở bước cuối.

shadcn đưa mã component vào `src/components/ui/`; CLI chuẩn bị cấu hình, utility `cn` và CSS tokens. React Hook Form quản lý trạng thái form; Zod mô tả/kiểm tra dữ liệu; TanStack Query quản lý trạng thái request/cache khi tích hợp thật tại G5. Cài package hiện tại chưa chứng minh các luồng API tương lai đã hoạt động.

### Bước 1: chuyển file cấu hình rỗng sang bản lưu (1 phút)

`/Users/sontung/Documents/GitHub/JobShield/frontend/components.json` hiện 0 byte, không phải JSON cấu hình hợp lệ. Trong frontend chạy:

```bash
cd /Users/sontung/Documents/GitHub/JobShield/frontend
mv -n components.json components.scaffold.json
ls -l components.scaffold.json
```

`mv` giữ file khung dưới tên khác để CLI có thể tạo cấu hình thật; `-n` không ghi đè file đích đã có. **Mong đợi:** có `components.scaffold.json` 0 byte và tên `components.json` được dành cho bước init. Nếu file đích đã tồn tại khiến move không thực hiện, dừng và gửi tình trạng file; không thêm `--force`.

Đây chỉ là file khung rỗng được giữ lại, không có dữ liệu ứng dụng bị xóa. File scaffold không cần stage cùng cấu hình thật.

### Bước 2: khởi tạo shadcn trong frontend hiện có (2–5 phút)

Từ frontend chạy:

```bash
npx shadcn@latest init --defaults
```

`npx` chạy CLI được tải về; `init` chuẩn bị project hiện có; `--defaults` chọn cấu hình mặc định/preset Nova theo [tài liệu CLI hiện tại](https://ui.shadcn.com/docs/cli#init). Không tạo project Next mới hoặc monorepo; frontend hiện tại đã có Tailwind và alias `@/*` trỏ `src/*`.

CLI có thể sửa `package.json`, lockfile, `src/app/globals.css`, tạo `components.json` và ghi utility `src/lib/utils.ts`. Nếu hỏi ghi đè utility, file utils đã được kiểm tra đang rỗng nên có thể cho phép ghi utility đó. Đọc tên file được hỏi trước khi trả lời, không chấp nhận ghi đè tất cả file tùy ý.

**Mong đợi:** init thành công, `components.json` là JSON có cấu hình; utils có hàm `cn`; CSS vẫn có import Tailwind và thêm tokens phục vụ component. Nếu CLI không nhận Next/Tailwind/alias, gửi lỗi đầu tiên, giữ lại các file đang chạy được từ chặng 2. Các bước tích hợp project hiện có được đối chiếu [hướng dẫn shadcn cho Next](https://ui.shadcn.com/docs/installation/next#existing-project).

### Bước 3: cài ba thư viện còn lại của stack frontend (2–5 phút)

Từ frontend chạy:

```bash
npm install --save-exact react-hook-form zod @tanstack/react-query
```

**Mong đợi:** ba tên xuất hiện trong `dependencies` với phiên bản cụ thể; lockfile cập nhật. `--save-exact` ghi phiên bản resolve để kiểm tra ở checkpoint. Chưa viết API client, provider auth hoặc query gọi backend trong bước này.

Nếu có `ERESOLVE`, gửi lỗi trước khi thử thay phiên bản; không dùng `--force` hoặc `--legacy-peer-deps` để vượt xung đột.

### Bước 4: thêm một Button và dùng trong trang shell (3–5 phút)

Trong frontend chạy:

```bash
npx shadcn@latest add button
```

**Mong đợi:** có `/Users/sontung/Documents/GitHub/JobShield/frontend/src/components/ui/button.tsx`; CLI chỉ thêm component cần kiểm tra. Không thêm toàn bộ thư viện component.

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/src/app/(public)/page.tsx`. Thêm import này ở đầu file:

```tsx
import { Button } from "@/components/ui/button";
```

Thêm đoạn sau ngay trước `</main>`, giữ nội dung trang đã chạy ở chặng 2:

```tsx
<div className="mt-6">
  <Button type="button">Nút kiểm tra giao diện</Button>
</div>
```

Đây là kiểm tra import/component, style và focus; nút chưa gắn hành vi sản phẩm. Vị trí import dùng alias `@/components/ui` từ cấu hình hiện có. Chỉ chép nội dung bên trong khối mã, không chép các dòng Markdown đánh dấu khối.

### Bước 5: kiểm tra trong trình duyệt và gửi checkpoint (2–3 phút)

Trong frontend chạy:

```bash
npm run dev
```

Mở URL local Next in ra và vào `/`. **Mong đợi:** nội dung JobShield còn hiển thị, nút có style, dùng `Tab` tới nút thấy focus; không có lỗi module `button` hoặc `utils`. Màu theme có thể đổi theo preset, vì vậy không dùng màu xanh của nhãn cũ làm tiêu chí duy nhất cho chặng này.

Sau khi kiểm tra, dừng server bằng `Ctrl+C` rồi chạy:

```bash
npm ls --depth=0
```

Gửi output package tree và xác nhận nút hiển thị/có focus, hoặc lỗi đầu tiên. Agent sẽ đọc cấu hình CLI đã sinh và phiên bản thật trước khi hướng dẫn Vitest/Playwright. Chưa dùng bước này làm bằng chứng production build hoặc API integration đã đạt.

### Hai package extraneous trong output chặng 2

Output người dùng có `@img/sharp-wasm32@0.35.5` và `@emnapi/runtime@1.11.3` extraneous. Theo [định nghĩa npm](https://docs.npmjs.com/cli/v11/commands/npm-prune/), cờ này chỉ package có trên đĩa nhưng không nằm trong danh sách dependency npm nhận diện cho cây đang xét.

Read-only check thấy cả hai entry optional trong lockfile và liên kết qua các nhánh WebAssembly của sharp; các package sharp native darwin-arm64 cũng có trên đĩa. Không có `invalid` hoặc `UNMET DEPENDENCY` ở output được gửi; trang `/` được xác nhận có styles. Vì vậy giữ chúng trong chặng này, không thêm vào dependencies chỉ để xóa nhãn extraneous. Nếu chúng gây lỗi cụ thể hoặc cần làm sạch môi trường, kiểm tra bằng dry-run trước khi hướng dẫn thay đổi; không xóa node_modules để xử lý một nhãn.

**Điểm kiểm tra hiện tại:** Button shadcn hiển thị/focus và package tree có ba thư viện form/query. **Hành động tiếp theo dưới 2 phút:** chuyển file components.json rỗng sang components.scaffold.json ở bước 1.

## 8. Chặng bảo mật đã tạm hoãn — tách CSS khỏi dependency CLI shadcn

**Quyết định hiện tại ngày 14/10/2026:** người dùng hỏi “kệ 7 braces đó đi được không” và chọn tiếp tục G1 local. Chưa làm các bước dưới đây; không cần làm mục này trước mục 9. Giữ nguyên dependency và CSS import hiện có, không chạy `npm audit fix --force` hoặc đổi cách báo cáo để che cảnh báo.

7 mục high vẫn là nợ bảo mật chưa xử lý. Kiểm tra source hiện có chưa thấy dữ liệu tuyển dụng được truyền vào braces; đây là giới hạn của kiểm tra hiện tại, không phải bằng chứng mọi đường gọi an toàn. Trước khi triển khai công khai, đánh giá lại dependency và khả năng dữ liệu không tin cậy đi tới parser. Phần hướng dẫn bên dưới được giữ để người dùng quay lại khi xử lý nhánh này.

**Mục tiêu:** giữ nguyên styles và Button đã tạo, loại dependency CLI kéo nhánh braces bị cảnh báo khỏi cây dependency của ứng dụng. Người dùng tự sửa/cài/gỡ theo quy tắc tự học; agent chỉ đọc file và hướng dẫn.

**Trạng thái ngày 14/10/2026:** shadcn 4.21.4 nằm trong dependencies; globals.css dòng 3 import `shadcn/tailwind.css`; Button dùng `@base-ui/react`, class-variance-authority và `cn`, không import JavaScript từ shadcn. CSS của shadcn có sẵn tại `node_modules/shadcn/dist/tailwind.css`, tự chứa các rules, không có import/url ra file khác; package có `LICENSE.md`. Các file local styles được hướng dẫn tạo bên dưới chưa tồn tại lúc kiểm tra.

**Điều kiện trước khi bắt đầu:** đứng trong frontend, giữ nguyên version/component hiện có; dev server đã được người dùng dừng bằng `Ctrl+C`. Khoảng **5–10 phút**. Không cần xóa toàn bộ node_modules, đổi Node/Python hoặc sửa Button.

### Vì sao audit báo 7 mục?

Báo cáo chỉ ra braces 3.0.3 và sáu package phụ thuộc bị ảnh hưởng theo chuỗi shadcn/registry/ts-morph → fast-glob → micromatch → braces. Đây là bảy mục có liên hệ trong dependency tree, không đủ cơ sở gọi chúng là bảy lỗ hổng độc lập trong mã JobShield.

[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) mô tả DoS: brace pattern lồng quá sâu có thể làm tràn call stack và dừng process Node. Advisory hiện liệt kê affected <=3.0.3, patched versions None. Không pin braces 3.0.3 rồi coi đã vá, và không dùng audit fix --force để hạ shadcn về 1.0.0 theo gợi ý của npm.

CSS là dữ liệu build mà project đang cần từ package này. Chép nguyên CSS và license sang source local trước, đổi import sang file local, sau đó người dùng mới gỡ CLI. Không copy JavaScript dễ bị ảnh hưởng vào ứng dụng; không xóa styles để làm audit trông sạch.

### Bước 1: giữ CSS và license local (1–2 phút)

Từ Terminal chạy:

```bash
cd /Users/sontung/Documents/GitHub/JobShield/frontend
mkdir -p src/styles
cp -n node_modules/shadcn/dist/tailwind.css src/styles/shadcn.css
cp -n node_modules/shadcn/LICENSE.md src/styles/shadcn.LICENSE.md
cmp node_modules/shadcn/dist/tailwind.css src/styles/shadcn.css
```

`mkdir -p` tạo thư mục nếu cần; `cp -n` giữ file đích đã có, không ghi đè; `cmp` kiểm tra bản CSS giống hệt nguồn. **Mong đợi:** hai file local có nội dung, cmp không in khác biệt và thoát thành công. Nếu source không còn, copy thất bại hoặc cmp báo khác biệt, dừng và gửi lỗi; chưa gỡ package CLI.

Giữ nguyên license đã kèm package. Bản CSS được lấy từ shadcn 4.21.4 đã cài, chưa được chỉnh sửa hay rút bớt rules.

### Bước 2: đổi đúng một import CSS (1 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/src/app/globals.css`. Thay dòng 3:

```css
@import "shadcn/tailwind.css";
```

bằng:

```css
/* shortcut: CSS từ shadcn 4.21.4; cập nhật bản local khi đổi phiên bản hoặc upstream tách CSS khỏi CLI. */
@import "../styles/shadcn.css";
```

Giữ các import Tailwind/tw-animate-css, theme variables, dark mode và base rules phía dưới. Đường dẫn đi từ `src/app/globals.css` sang `src/styles/shadcn.css`.

Từ frontend kiểm tra diff:

```bash
git diff -- src/app/globals.css
```

**Mong đợi:** import package được thay bằng import local và comment phiên bản; không xóa cả theme hoặc phần CSS đã dùng ở chặng trước. Đây là kiểm tra thay đổi source, chưa chứng minh browser đã render đúng.

### Bước 3: tự gỡ package CLI khỏi project (1–2 phút)

Chỉ thực hiện khi copy/đổi import ở bước 1–2 đạt. Từ frontend chạy:

```bash
npm uninstall shadcn
```

Lệnh gỡ package khai báo và cập nhật manifest/lockfile; npm có thể dọn các dependency gián tiếp chỉ còn được CLI sử dụng. Component trong src, CSS local, `cn`, Base UI và các thư viện form/query được giữ. Hành vi uninstall được mô tả trong [tài liệu npm](https://docs.npmjs.com/cli/v11/commands/npm-uninstall/).

**Mong đợi:** shadcn không còn được khai báo trong package.json; các file source/component không bị xóa. Không dùng --force hoặc cài shadcn 1.0.0. Không coi số lượng package npm gỡ là bằng chứng audit đã đạt.

### Bước 4: kiểm tra lại đúng nhánh vulnerability (1 phút)

Từ frontend chạy:

```bash
npm audit
npm ls --depth=0
```

**Mong đợi:** report không còn chuỗi braces/micromatch/fast-glob/registry/ts-morph/shadcn nêu ở trên; package tree vẫn có cn, Base UI, React Hook Form, Zod, TanStack Query và nền Next/Tailwind. Nếu vẫn còn warning, gửi report mới để tìm referrer còn lại; không đổi ngưỡng audit hoặc dùng --omit=dev để giả đã vá nhánh này.

Kết quả `found 0 vulnerabilities` nếu có chỉ là kết quả audit ở thời điểm chạy, không chứng minh toàn bộ bảo mật sản phẩm đã hoàn tất.

### Bước 5: xác nhận giao diện vẫn hoạt động (1–2 phút)

Từ frontend chạy:

```bash
npm run dev
```

Mở URL local Next in ra và vào `/`. **Mong đợi:** nội dung và Button còn hiển thị, styles/focus hoạt động; không có lỗi Cannot resolve shadcn/tailwind.css hoặc lỗi CSS local. Dừng server bằng Ctrl+C sau kiểm tra.

Gửi output audit mới và xác nhận giao diện/Button. Nếu lỗi resolve package CSS, kiểm tra đã sửa import đúng file chưa; nếu lỗi relative CSS, kiểm tra bản local từ bước 1 và `../styles/shadcn.css` từ bước 2. Không chữa bằng cách bỏ toàn bộ styles.

### Giới hạn và hoàn tác

Đây là loại nhánh CLI khỏi dependencies ứng dụng, không vá bản thân CLI. Khi thêm component bằng CLI sau này, kiểm tra phiên bản/advisory và xem nó có thêm lại dependency hoặc CSS import cũ không; chưa tuyên bố công cụ CLI đã an toàn vì audit project sạch.

Bản CSS local phải được giữ cùng license và phiên bản nguồn. Nếu cần hoàn tác vì styles chưa hoạt động, người dùng có thể cài lại đúng `npm install --save-exact shadcn@4.21.4` và đổi import về `@import "shadcn/tailwind.css";`; bước đó khôi phục cách dùng cũ và đưa warning cũ trở lại. Giữ file local để chẩn đoán, không xóa dữ liệu/source tùy ý.

**Điểm kiểm tra khi quay lại xử lý:** audit không còn nhánh đã báo và Button/styles vẫn hoạt động. **Hành động nhỏ khi quay lại:** copy CSS và license theo bước 1; chưa chạy uninstall trước khi bản local được kiểm tra. Hiện tiếp tục mục 9.

## 9. Chặng 4A — Vitest kiểm tra trang shell

**Bắt đầu:** mở Terminal tại `/Users/sontung/Documents/GitHub/JobShield/frontend` và thực hiện bước 1 dưới đây. Khoảng **10–15 phút** nếu tải package bình thường.

**Mục tiêu:** chạy được một test render trang JobShield thật, tìm tiêu đề và Button theo tên người dùng đọc được. Đây là checkpoint test runner của G1U, tạo nền kiểm tra component và logic thuần ở các giai đoạn sau.

**Trạng thái trước chặng:** trang home đã import Button; manifest có shadcn, React Hook Form, Zod và TanStack Query. Chưa cài Vitest/Testing Library/jsdom; `vitest.config.ts` và `tests/setup.ts` còn rỗng, test mới bên dưới chưa tồn tại. 7 cảnh báo high được tạm hoãn, chưa vá. Python/backend vẫn để lại theo yêu cầu.

**Điều kiện:** Node/npm dùng được và có Internet để tải package. Bạn tự nhập cấu hình/cài dependency theo quy tắc học môi trường trong AGENTS. Nếu dev server của bạn đang chạy, dừng bằng `Ctrl+C` tại Terminal đó; Vitest không cần server, DB, Docker hoặc API key.

Vitest tìm và chạy test; React Testing Library render component và tìm phần tử theo role/tên; jsdom cung cấp DOM trong Node, chưa phải trình duyệt thật. `@vitejs/plugin-react` biên dịch JSX; `@testing-library/jest-dom` bổ sung các assertion như `toBeInTheDocument`. Theo [hướng dẫn Next.js](https://nextjs.org/docs/app/guides/testing/vitest), test component đồng bộ dùng được; component server `async` cần kiểm tra E2E. Home hiện tại là hàm đồng bộ.

### Bước 1: cài công cụ kiểm tra (2–5 phút)

Trong Terminal chạy:

```bash
cd /Users/sontung/Documents/GitHub/JobShield/frontend
npm install --save-dev --save-exact vitest @vitejs/plugin-react@5.2.0 jsdom @testing-library/react @testing-library/dom @testing-library/jest-dom
npm ls vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/dom @testing-library/jest-dom --depth=0
```

`--save-dev` ghi công cụ kiểm tra vào devDependencies; `--save-exact` giữ phiên bản resolve cụ thể. Testing Library yêu cầu cài cùng [peer dependency DOM Testing Library](https://testing-library.com/docs/react-testing-library/intro/#installation). Phiên bản mới nhất được npm chọn lúc bạn chạy; gửi output để đối chiếu số phiên bản thật. [Vitest hiện yêu cầu Node >=22.12.0](https://vitest.dev/guide/#adding-vitest-to-your-project); Node 24.8.0 đã quan sát đáp ứng floor này.

**Mong đợi:** lệnh install thoát thành công và sáu tên xuất hiện trong cây package, không có invalid/unmet. Manifest/lockfile thay đổi, thư viện được tải vào node_modules; dependency frontend không chuyển vào venv. Lệnh có dùng mạng/dung lượng và có thể chạy lifecycle script của package; không gửi dữ liệu tuyển dụng hoặc secret JobShield.

Nếu vẫn có 7 cảnh báo braces đã biết, giữ report như quyết định tạm hoãn. Nếu có report khác, `ERESOLVE` hoặc `EBADENGINE`, gửi phần lỗi/cảnh báo mới; không dùng `--force` hoặc `--legacy-peer-deps`.

### Bước 2: cấu hình cách Vitest nạp component (3–4 phút)

File `/Users/sontung/Documents/GitHub/JobShield/frontend/vitest.config.ts` đang rỗng. Từ frontend đổi tên:

```bash
mv -n vitest.config.ts vitest.config.mts
```

`.mts` xác định cấu hình dùng module ESM, phù hợp plugin React; không cần đổi kiểu module của cả frontend. `-n` không ghi đè đích đã có. Nếu `vitest.config.mts` đã có hoặc file nguồn không còn rỗng, dừng để đối chiếu nội dung trước khi nhập, không ghi đè cấu hình bạn đã làm.

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/vitest.config.mts`, nhập nội dung sau. Chỉ chép code, không chép dòng Markdown đánh dấu khối:

```ts
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
  },
});
```

Alias `@` trỏ tới `src`, khớp `@/*` trong tsconfig, để test đọc được import Button giống trang thật. `include` chỉ gom unit test trong tests, giữ test browser trong e2e cho Playwright. `setupFiles` nạp assertion và dọn DOM giữa các test.

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/tests/setup.ts`, nhập:

```ts
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);
```

**Mong đợi:** có đúng một config `vitest.config.mts` với nội dung và setup đã lưu. Việc lưu file chưa chứng minh cấu hình nạp được; bước 5 sẽ kiểm tra config, alias và setup cùng nhau. Nếu xuất hiện parse error tại dấu backtick, kiểm tra bạn có chép dòng Markdown vào file hay không.

### Bước 3: tạo một self-check có dùng trang hiện tại (2 phút)

Tạo `/Users/sontung/Documents/GitHub/JobShield/frontend/tests/toolchain.test.tsx` với nội dung:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import HomePage from "@/app/(public)/page";

test("trang shell hiển thị JobShield và nút kiểm tra", () => {
  render(<HomePage />);

  expect(
    screen.getByRole("heading", { level: 1, name: "JobShield" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Nút kiểm tra giao diện" }),
  ).toBeEnabled();
});
```

Test dùng HomePage và Button thật, không mock UI để vượt lỗi import. Tìm theo role/tên kiểm tra tiêu đề cấp 1 và tên truy cập được của nút. Assertion `toBeEnabled` chứng minh nút không bị disabled; chưa kiểm tra click có nghiệp vụ hoặc CSS đã hiển thị trong trình duyệt.

**Mong đợi:** file có đúng một test, tên nút khớp trang hiện tại. Chưa sửa các file test sản phẩm còn rỗng hoặc viết chức năng phân tích ở G1.

### Bước 4: thêm lệnh chạy test (1 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/package.json`. Chỉ sửa phần `scripts` thành:

```json
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "test": "vitest run"
}
```

Đây là giá trị của trường scripts, không thay toàn bộ manifest bằng khối này. Giữ tên/version/private và các dependencies. `vitest run` chạy một lượt rồi thoát; chế độ này dễ đọc checkpoint hơn một watcher chờ thay đổi liên tục.

Từ frontend kiểm tra JSON và tên script:

```bash
node -e 'const fs = require("node:fs"); const p = JSON.parse(fs.readFileSync("package.json", "utf8")); console.log(p.name, p.scripts.test)'
```

**Mong đợi:** `jobshield-frontend vitest run`. Nếu JSON lỗi, kiểm tra dấu phẩy giữa các script; chưa chạy test trước khi manifest hợp lệ.

### Bước 5: chạy đúng self-check và gửi kết quả (1–2 phút)

Trong frontend chạy:

```bash
npm test -- tests/toolchain.test.tsx
```

`--` chuyển tham số sau nó tới Vitest; đường dẫn chọn riêng bài kiểm tra G1. Các test sản phẩm khác vẫn là file khung và chưa có suite, nên chưa chạy toàn bộ tests để nghiệm thu ứng dụng. Không thay cấu hình để nuốt lỗi hoặc coi không tìm thấy test là đạt.

**Mong đợi:** output chỉ ra `tests/toolchain.test.tsx`, `Test Files 1 passed` và `Tests 1 passed`; lệnh thoát thành công. Điều này chứng minh runner, JSX, alias, setup và import HomePage/Button phối hợp được trong jsdom. Nó chưa chứng minh CSS, keyboard focus, production build hoặc API/backend hoạt động.

| Lỗi đầu tiên | Nguyên nhân/cách kiểm tra |
| --- | --- |
| Không tìm thấy vitest/plugin/jsdom | Bước 1 có cài đủ trong frontend không; xem output npm ls |
| Cannot resolve `@/app` hoặc `@/components` | Config đang là vitest.config.mts trong frontend; alias trỏ src, không trỏ gốc repo |
| Invalid matcher `toBeInTheDocument` | Setup import đúng `@testing-library/jest-dom/vitest` và setupFiles trỏ đúng tests/setup.ts |
| No test suite / No test files found | Lệnh có đúng đường dẫn toolchain.test.tsx, file đã lưu code; không chạy các file khung rỗng |
| Unable to find heading/button | Đọc tên/role thật trong home; gửi lỗi để đối chiếu, không đổi assertion sang luôn đúng |

**Điểm kiểm tra bài thực hành:** self-check chạy được. Agent đã thực hiện checkpoint này theo ngoại lệ; kết quả và lệnh chạy lại ở mục 10. Toàn bộ G1U vẫn cần backend/Pytest và cấu hình backend; chưa chuyển G2.

**Hành động tiếp theo dưới 2 phút:** mở Terminal, chạy `cd /Users/sontung/Documents/GitHub/JobShield/frontend`, rồi bắt đầu lệnh cài ở bước 1.

## 10. Frontend G1 đã thiết lập — chạy lại

**Bắt đầu ngay:** mở Terminal và chạy bước 1, khoảng **1 phút**. Không cài lại các package đang có trên máy này.

Agent đã cài/cấu hình frontend theo ngoại lệ người dùng xác nhận ngày 14/10/2026. Runtime đã kiểm tra: Node 24.8.0, npm 11.6.0, darwin arm64. Manifest ghi engines Node >=24.8.0 <25 và npm 11.x; direct dependencies dùng phiên bản exact. Đây là ràng buộc project, không đổi runtime mặc định toàn máy.

| Nhóm | Phiên bản đã chốt |
| --- | --- |
| Ứng dụng | Next 16.4.0; React/React DOM 19.3.0; TypeScript 7.0.2 |
| CSS | Tailwind/@tailwindcss/postcss 4.3.3; postcss 8.5.30 |
| Form/query | React Hook Form 7.90.0; Zod 4.6.7; TanStack Query 5.104.2 |
| Unit runner | Vitest 5.0.4; plugin-react 5.2.0; jsdom 29.1.1; Testing Library react/dom/jest-dom 16.3.3/10.4.2/7.0.1 |
| Browser runner | Playwright 1.64.0; Chromium 156.0.8078.4 ARM64 |

Plugin React 5.2.0 hỗ trợ Vite 8 và tương thích Babel 7 của shadcn hiện có. Khi thử latest 6.1.2, npm chọn optional Babel plugin sang Babel 8 RC và gặp ERESOLVE; không dùng force/legacy-peer-deps. Lockfile ghi cây dependency đã resolve.

### Bước 1: kiểm tra TypeScript và unit suite (1 phút)

```bash
cd /Users/sontung/Documents/GitHub/JobShield/frontend
npm run typecheck
npm test
```

**Kết quả đã kiểm tra:** cả hai lệnh exit 0; typecheck sinh route types rồi chạy tsc --noEmit; Vitest báo `Tests 1 passed | 3 todo`. Self-check render HomePage/Button thật. Ba file test sản phẩm còn khung được ghi rõ bằng test.todo cho G5/G9; không tính chúng là test đạt. Config vẫn gom toàn bộ tests/**/*.test.ts(x), không chỉ lọc self-check để che file khác. Không cấu hình bỏ qua lỗi TypeScript.

### Bước 2: kiểm tra trang trong Chromium (1 phút)

```bash
npm run test:e2e -- --project=chromium
```

**Điều kiện:** port 3000 rảnh, không có dev server JobShield khác giữ .next/dev/lock. Dừng server do bạn đang chạy bằng Ctrl+C ở Terminal đó; không kill tiến trình không rõ chủ sở hữu.

**Kết quả đã kiểm tra:** exit 0, `2 passed`. Playwright tự chạy Next trên http://127.0.0.1:3000, kiểm tra tiêu đề/font-size 36px, Button inline-flex và Tab focus; test thứ hai kiểm tra 16 route sản phẩm còn khung và một đường dẫn không tồn tại trả 404 tiếng Việt, có link về trang chủ. Server được dừng sau suite; reuseExistingServer=false tránh dùng server cũ. Turbopack root lấy cwd của npm script frontend. Warnings NO_COLOR/FORCE_COLOR đến từ công cụ terminal, không phải error của trang. Cấu hình dựa trên [Playwright webServer](https://playwright.dev/docs/test-webserver).

Chỉ Chromium được cài/chạy ở G1. Đây là kiểm tra shell và regression route khung, chưa là E2E luồng người dùng/backend.

### Bước 3: xem shell thủ công (1 phút để khởi động)

```bash
npm run dev
```

Mở URL Next in ra, truy cập `/`; dừng bằng Ctrl+C khi xong. Layout/font Geist/Button được giữ nguyên. Các route sản phẩm khác dùng default export notFound, hiển thị 404 tiếng Việt từ src/app/not-found.tsx. Layout user/admin chỉ trả children, không xác thực hoặc cấp quyền. Theo [Next notFound](https://nextjs.org/docs/app/api-reference/functions/not-found), hàm này kết thúc render route bằng trạng thái không tìm thấy; nó không dựng chức năng sản phẩm giả.

Build đã kiểm tra bằng `npm run build` trong Terminal macOS của người dùng: compile, TypeScript, thu thập dữ liệu trang và tạo 18 trang đều đạt. Agent cũng chạy `npm run build -- --webpack` thành công. Trong phiên Codex, build Turbopack mặc định báo EPERM ở worker bind port dù Node bind localhost và dev/browser chạy được; đây là giới hạn môi trường đã đối chiếu bằng bản build người dùng, không đổi bundler mặc định hoặc bỏ kiểm tra lỗi. Biểu hiện trùng với [báo cáo Codex #50945](https://github.com/openai/codex/issues/50945). Geist cần mạng để tải font khi cache chưa có. Build đạt chỉ chứng minh shell/placeholder, chưa là sản phẩm hoàn chỉnh.

### Bước 4: tái tạo dependency khi cần (2–5 phút)

Từ frontend dùng `npm ci`. Lệnh tái tạo node_modules từ manifest/lockfile, giữ source và dữ liệu backend. Trên máy chưa có browser, chạy `npm run playwright:install` để tải Chromium; khoảng 285 MiB cho Chrome/Headless Shell cùng FFmpeg, có dùng mạng và dung lượng cache người dùng.

Agent đã chạy npm ci --offline --include=optional từ cache có sẵn: exit 0, sau đó unit/browser đều đạt. Offline chỉ dùng được khi cache đã đủ tarball; máy mới cần npm ci có mạng. Native Rolldown/Tailwind darwin-arm64 có trong lockfile và nạp được. Nếu npm bỏ native optional dependency khi thêm package, kiểm tra platform/lockfile và tái tạo; không thêm binding vào dependency root để che report.

npm ls --depth=0 đạt. Sau npm ci, kiểm tra toàn cây không có missing/invalid peer; hai package optional WebAssembly ở chặng 2 có thể vẫn được npm đánh dấu extraneous. Chúng không thay native ARM64; không prune chỉ để xử lý nhãn khi runner/CSS đang hoạt động.

### Bước 5: hiểu frontend env example và điểm dừng (2 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/frontend/.env.example`. Chỉ có URL công khai minh họa NEXT_PUBLIC_API_BASE_URL=http://localhost:8000. Shell chưa đọc biến này, chưa có API client/request backend; tên/giá trị sẽ được đối chiếu với hợp đồng ở G2/G5. Không tạo env local có secret hoặc validation/API giả để nghiệm thu G1.

NEXT_PUBLIC_* có thể được đóng vào JavaScript gửi tới browser tại build time, theo [Next environment variables](https://nextjs.org/docs/app/guides/environment-variables). Không dùng chúng giữ API key, mật khẩu hoặc DATABASE_URL. Git check-ignore xác nhận frontend/.env và .env.local bị ignore; .env.example vẫn trackable. Backend đã có test thiếu/rỗng DATABASE_URL và SecretStr; chi tiết ở mục 11.

Audit mới vẫn có đúng **7 high nhánh braces**, không có mức severity khác; mục 8 tạm hoãn, chưa audit fix/uninstall. ESLint scaffold chưa cấu hình: stable typescript-eslint hiện yêu cầu TypeScript <6.1, chưa tương thích TS 7.0.2; không hạ compiler hoặc thêm lint script bỏ qua peer errors. Lint không thuộc checkpoint runner của Task 1U; đánh giá lại khi tooling hỗ trợ compiler này.

**Điểm dừng lịch sử của lượt frontend:** lúc đó backend 89 file còn nguyên và chưa được làm. Người dùng sau đó đã cho phép ngoại lệ backend G1; kết quả hiện tại ở mục 11. Chưa chuyển G2.

**Hành động tiếp theo dưới 2 phút:** chạy npm test ở bước 1 để xem 1 passed/3 todo trên Terminal của bạn.

## 11. Backend G1 — Python chỉ trong venv

**Bắt đầu ngay (1 phút):** chạy bước 1. Backend environment đã cài; chưa cần cài lại, tạo DB hoặc chạy server.

Theo xác nhận trực tiếp của người dùng, agent được làm backend G1 nhưng chỉ cài Python mới nhất trong venv. Python [stable mới nhất ngày 14/10/2026 là 3.15.0](https://www.python.org/downloads/release/python-3150/). Cả executable, sys.prefix và sys.base_prefix đã được kiểm tra nằm dưới `/Users/sontung/Documents/GitHub/JobShield/backend/.venv`. Runtime gốc được giữ tại `.venv/.python/cpython-3.15.0-macos-aarch64-none`; venv tham chiếu runtime này ở bên trong, không tới bản Python mới ngoài venv.

Python toàn máy vẫn 3.9.6 và uv toàn máy vẫn 0.11.14; không đổi PATH/alias. uv 0.13.1 bootstrap được đặt tại `.venv/.tools` vì uv toàn máy chỉ biết metadata 3.15 beta. Pin `.python-version=3.15.0` áp dụng cho backend/project, không làm phiên bản mới thành mặc định toàn máy. `python-downloads=never` trong pyproject chặn tự tải Python ra ngoài khi runtime thiếu.

| Nhóm | Phiên bản exact trong pyproject/lockfile |
| --- | --- |
| Web | FastAPI 0.143.0; Uvicorn 0.54.0 |
| Cấu hình/dữ liệu | Pydantic 2.14.1; pydantic-settings 2.15.0 |
| Database SDK | SQLAlchemy 2.1.4; Alembic 1.20.0; psycopg/psycopg-binary 3.3.6 |
| Kiểm tra | Pytest 9.1.1; HTTPX 0.28.1 |
| Runtime | CPython 3.15.0, darwin arm64, chỉ trong .venv |

Manifest là ứng dụng local (`package=false`), chưa đóng gói Python package để publish. Runtime dependency nằm ở dependencies, công cụ kiểm tra ở dev group; uv.lock giữ cả dependency gián tiếp. Psycopg binary có wheel ARM64 tương thích và đã import được, chưa kết nối PostgreSQL. Chưa cài SDK của nhà cung cấp OCR/LLM vì provider/API integration chưa được chọn.

### Bước 1: chạy toàn bộ Pytest (1 phút)

```bash
cd /Users/sontung/Documents/GitHub/JobShield/backend
uv run --frozen pytest
```

**Kết quả đã kiểm tra:** exit 0, **12 passed**: 9 dependency/project-module imports và 3 tests cấu hình. uv toàn máy dùng venv đã có; không cần activation để chạy lệnh này. Các test nghiệp vụ/API/DB còn file khung, không được coi là đã kiểm thử vì chúng không chứa test. Import app.main chỉ xác minh Python namespace/file khung; main chưa có FastAPI app/endpoint nên chưa chạy uvicorn app.main:app.

### Bước 2: kiểm tra Python trong venv (1 phút)

```bash
.venv/bin/python --version
.venv/bin/python -c 'import sys; print(sys.executable); print(sys.prefix); print(sys.base_prefix)'
```

**Mong đợi:** Python 3.15.0 và cả ba đường dẫn dưới backend/.venv. Terminal ngoài venv vẫn dùng Python hệ thống. Nếu muốn lệnh python trong Terminal hiện tại trỏ venv, chạy `source .venv/bin/activate`; `deactivate` trở lại môi trường trước đó, không thay cấu hình shell toàn máy.

### Bước 3: đồng bộ dependency từ lockfile (1–3 phút)

```bash
uv sync --frozen
uv pip check --python .venv/bin/python
uv run --frozen pytest
```

`--frozen` giữ quyết định trong uv.lock, không tự đổi phiên bản. Agent đã kiểm chứng tái cài 30 packages từ lockfile bằng uv sync --frozen --reinstall, rồi pip check và toàn suite đạt; native/runtime vẫn trong venv. Lần --reinstall offline không đủ cache nên chưa coi tái cài offline đã đạt; tải wheel có mạng đã hoàn tất. Pytest frozen/offline riêng đã đạt sau cài. Các lệnh không tạo schema/data hoặc gọi provider.

### Bước 4: hiểu file môi trường (2 phút)

Mở `/Users/sontung/Documents/GitHub/JobShield/backend/.env.example`. DATABASE_URL ở đây là chuỗi minh họa có example-password, không có DB/tài khoản thật. Backend đọc `.env` tại cwd backend khi tạo Settings; agent chưa tạo file secret thật. `Settings(_env_file=".env.example")` đã được kiểm tra nạp example và repr chỉ hiển thị SecretStr('**********').

Settings yêu cầu DATABASE_URL có giá trị, từ chối thiếu/rỗng và ẩn input trong thông báo lỗi. Đây là quy ước env G1, chưa kiểm tra kết nối hay xác minh DSN/schema đúng cho DB thật; bước đó thuộc G2/G3. Frontend NEXT_PUBLIC_API_BASE_URL là cấu hình công khai, DATABASE_URL backend có credential phải giữ riêng. Backend .env/.env.local, venv và caches bị ignore; các .env.example và uv.lock được phép theo dõi. Root .env.example chỉ trỏ tới hai thành phần, chưa có Compose config.

### Bước 5: dựng lại venv trên máy chưa có môi trường (3–5 phút)

Không cần chạy bước này trên máy hiện tại. Nếu phải dựng từ đầu trên macOS ARM64 có uv và Python hệ thống >=3.9, chạy từ backend:

```bash
uv pip install uv==0.13.1 --target .venv/.tools --python /usr/bin/python3 --no-python-downloads --no-config
./.venv/.tools/bin/uv python install 3.15.0 --install-dir .venv/.python --no-bin --no-config
./.venv/.tools/bin/uv venv --allow-existing --python .venv/.python/cpython-3.15.0-macos-aarch64-none/bin/python3.15 --no-python-downloads .venv
uv sync --frozen
uv run --frozen pytest
```

`--target` giữ uv bootstrap trong venv; `--install-dir` giữ runtime mới trong venv; `--no-bin` không tạo shim bên ngoài; `--allow-existing` giữ .python/.tools khi tạo cấu trúc venv. Không dùng --clear vì nó có thể xóa runtime nested. Tải runtime khoảng 26.4 MiB và dependency wheels, có chi phí mạng/dung lượng; không thay Python hệ thống hoặc gửi dữ liệu JobShield.

**Checkpoint G1:** requirements/architecture, frontend shell/runners, backend runtime/import/Pytest/config và env conventions đã có chứng cứ. 80 file source/config frontend giữ nguyên trong lượt backend. G1 hoàn tất ở mức nền tảng; API, Database/migration/seed, auth, OCR/LLM/Docker và luồng sản phẩm chưa triển khai. Không tự chuyển G2.

**Hành động tiếp theo dưới 2 phút:** chạy uv run --frozen pytest ở bước 1 để thấy 12 passed trên Terminal của bạn.

## 12. Rà soát lại toàn bộ G1

Ngày 14/10/2026, đối chiếu từng checkbox Task 1A/1U với file và kết quả chạy mới:

| Phần G1 | Bằng chứng hiện tại |
| --- | --- |
| Yêu cầu và kiến trúc | Ba workflow, ba vai trò, toàn bộ trang, nhóm dữ liệu kết quả, A/U và luồng dữ liệu có trong requirements/architecture; chưa viết schema/API |
| Tài liệu có thể theo dõi | requirements.md và kế hoạch không còn bị ignore; git status liệt kê hai file, chưa commit |
| Runtime/dependency ARM64 | Node 24.8.0/npm 11.6.0 ARM64; Python 3.15.0 và runtime gốc đều trong venv; manifest exact khớp lockfiles; 30 backend packages compatible; frontend không missing/invalid peer |
| Frontend shell/runners | typecheck exit 0, Vitest 1 passed/3 todo, Chromium 2 passed, build Turbopack người dùng và Webpack agent đạt |
| Backend runner/env | Pytest 12 passed, examples chỉ giá trị minh họa; venv/cache/env thật bị ignore; không có request backend/DB/provider |

Sửa hai lỗi thực tế: page/layout rỗng gây TypeScript errors và HTTP 500; Git ignore che snapshot/kế hoạch. Regression test được chạy RED trước sửa (404 mong đợi, thực tế 500), rồi GREEN cho cả 17 đường dẫn. Các đoạn tài liệu còn ghi G1U chưa đạt được cập nhật theo trạng thái mới.

Ngoại lệ đã chấp nhận: 7 high nhánh braces vẫn hoãn; ESLint chưa tương thích TypeScript 7 nên chưa nghiệm thu lint. prompt.txt/AGENTS.md vẫn không có trên đĩa; nguồn snapshot giữ provenance rõ, chưa đối chiếu lại bản gốc. G1 hoàn tất phạm vi nền tảng, chưa tự chuyển G2 hoặc triển khai API, Database, auth, OCR/LLM hay Docker.

**Hành động dưới 2 phút:** chạy `npm run typecheck` trong frontend để kiểm tra các route khung đã hợp lệ.
