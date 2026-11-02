"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  ShieldAlert,
  Building2,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  FileSearch,
  ChevronRight,
  Activity,
  Zap,
} from "lucide-react";

export default function HomePage() {
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCheckApi = async () => {
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
      const res = await fetch(`${baseUrl}/ready`);
      const data = await res.json();
      setResult(`HTTP ${res.status}: ${data.detail?.message_vi || `${data.status} (DB: ${data.database})`}`);
    } catch {
      setResult("Lỗi: Không thể kết nối tới backend");
    } finally {
      setLoading(false);
    }
  };

  const sampleScenarios = [
    {
      badge: "Cảnh báo cao",
      title: "Bẫy giật đơn Shopee nạp tiền",
      desc: "Tuyển CTV xử lý đơn hàng online, làm nhiệm vụ nạp tiền nhận hoa hồng 20-30%, liên hệ qua Telegram.",
      risk: "danger",
      queryText: "Tuyển cộng tác viên xử lý đơn hàng online Shopee, Lazada tại nhà. Thu nhập 500k - 1tr/ngày. Yêu cầu có tài khoản ngân hàng để nhận tiền hoa hồng sau mỗi đơn. Liên hệ ngay qua Telegram @tuyendung_shopee2026 để nhận nhiệm vụ.",
    },
    {
      badge: "Cảnh báo cao",
      title: "Thu phí phỏng vấn & đồng phục",
      desc: "Yêu cầu đóng trước 500.000đ tiền hồ sơ, giữ chân và đồng phục trước khi vào thử việc.",
      risk: "danger",
      queryText: "Công ty TNHH Vận tải & Thương mại cần tuyển 05 nhân viên trực hotline. Lương 10 triệu/tháng. Ứng viên mang theo CCCD và nộp lệ phí xét duyệt hồ sơ cùng phí đồng phục 500.000 đồng khi đến phỏng vấn tại văn phòng.",
    },
    {
      badge: "Hợp lệ",
      title: "Tin tuyển dụng chuẩn mực",
      desc: "Mô tả công việc rõ ràng, pháp nhân minh bạch, quy trình phỏng vấn chuẩn không yêu cầu bất kỳ khoản phí nào.",
      risk: "safe",
      queryText: "Công ty Cổ phần Công nghệ An Toàn Việt tuyển dụng Kỹ sư Frontend (React/Next.js). Địa điểm: Tầng 6, Tòa nhà Tech, Cầu Giấy, Hà Nội. Lương 20 - 30 triệu/tháng. Đầy đủ BHXH, không thu bất kỳ chi phí xét tuyển nào. Gửi CV về: hr@antoanviet.vn.",
    },
  ];

  return (
    <div className="relative overflow-hidden">
      {/* Background radial glow accents */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -z-10 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-gradient-to-tr from-sky-400/20 via-blue-500/15 to-transparent blur-3xl dark:from-sky-900/30" />
      <div className="pointer-events-none absolute top-96 -left-40 -z-10 size-96 rounded-full bg-emerald-400/10 blur-3xl dark:bg-emerald-950/20" />

      {/* Hero Section */}
      <section className="mx-auto max-w-6xl px-4 pt-12 pb-16 sm:px-6 lg:pt-20 lg:pb-24">
        <div className="mx-auto max-w-3xl text-center">
          {/* Top trust pill */}
          <div className="inline-flex items-center gap-2 rounded-full border border-sky-200/80 bg-sky-50/80 px-3.5 py-1.5 text-xs font-semibold text-sky-800 shadow-sm backdrop-blur dark:border-sky-900/60 dark:bg-sky-950/50 dark:text-sky-300">
            <span className="flex size-2 rounded-full bg-sky-500 animate-pulse" />
            <span>Công nghệ AI & Quy tắc đối chiếu thông minh</span>
            <span className="text-sky-400 dark:text-sky-600">•</span>
            <span className="text-slate-600 dark:text-slate-300">100% Miễn phí</span>
          </div>

          <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-slate-950 sm:text-5xl lg:text-6xl dark:text-white">
            Lá chắn an toàn trước bẫy{" "}
            <span className="bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 bg-clip-text text-transparent dark:from-sky-400 dark:via-blue-400 dark:to-indigo-300">
              lừa đảo việc làm
            </span>
          </h1>

          <p className="mt-6 text-lg leading-relaxed text-slate-600 sm:text-xl dark:text-slate-300">
            JobShield tự động bóc tách dấu hiệu thu phí ẩn, nhiệm vụ nạp tiền, mạo danh doanh nghiệp lớn và kiểm tra chéo pháp nhân tin tuyển dụng trong vài giây.
          </p>

          {/* Primary Action Buttons */}
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
            <Link
              href="/analyze"
              className="group flex w-full items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-sky-600 to-blue-700 px-6 py-3.5 text-base font-semibold text-white shadow-lg shadow-sky-600/25 transition-all hover:from-sky-500 hover:to-blue-600 hover:shadow-sky-600/35 focus-visible:outline-2 focus-visible:outline-sky-600 sm:w-auto"
            >
              <Sparkles className="size-5 transition-transform group-hover:scale-110" />
              <span>Phân tích tin tuyển dụng</span>
              <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
            </Link>

            <Link
              href="/verify-employer"
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white/90 px-6 py-3.5 text-base font-semibold text-slate-800 shadow-sm backdrop-blur transition-all hover:bg-slate-50 hover:text-slate-950 focus-visible:outline-2 focus-visible:outline-blue-600 sm:w-auto dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800"
            >
              <Building2 className="size-5 text-slate-500 dark:text-slate-400" />
              <span>Xác minh nhà tuyển dụng</span>
            </Link>
          </div>

          {/* Mini system status check (keeps existing API test capability) */}
          <div className="mt-8 flex flex-col items-center justify-center gap-2">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={handleCheckApi}
                disabled={loading}
                className="text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400"
              >
                <Activity className="size-3 text-emerald-500" />
                {loading ? "Đang kiểm tra kết nối..." : "Nút kiểm tra giao diện"}
              </Button>
            </div>
            {result && (
              <p className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800 dark:bg-slate-800 dark:text-slate-200">
                {result}
              </p>
            )}
          </div>
        </div>

        {/* 3 Interactive Quick-Scan Sample Cards */}
        <div className="mt-14">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              ⚡ Thử nghiệm nhanh với các mẫu tin thực tế:
            </h2>
            <span className="text-xs text-slate-400">Bấm để phân tích tức thì</span>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            {sampleScenarios.map((item, idx) => (
              <div
                key={idx}
                className="group relative flex flex-col justify-between rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition-all hover:-translate-y-1 hover:border-sky-300 hover:shadow-md dark:border-slate-800 dark:bg-slate-900/90 dark:hover:border-sky-700"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span
                      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                        item.risk === "danger"
                          ? "bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300"
                          : "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300"
                      }`}
                    >
                      {item.badge}
                    </span>
                    <span className="text-xs font-medium text-slate-400">Mẫu #{idx + 1}</span>
                  </div>
                  <h3 className="mt-3 text-base font-bold text-slate-900 group-hover:text-sky-600 dark:text-slate-100 dark:group-hover:text-sky-400">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    {item.desc}
                  </p>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                  <Link
                    href={`/analyze?sample=${encodeURIComponent(item.queryText)}`}
                    className="inline-flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-700 dark:text-sky-400 dark:hover:text-sky-300"
                  >
                    <span>Phân tích mẫu này</span>
                    <ChevronRight className="size-3.5 transition-transform group-hover:translate-x-1" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Bento Grid: 4 Core Capabilities */}
      <section className="border-y border-slate-200/80 bg-slate-100/50 py-16 dark:border-slate-800 dark:bg-slate-900/40">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-xs font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400">
              Cơ chế phòng vệ thông minh
            </h2>
            <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl dark:text-white">
              Bảo vệ toàn diện trước mọi biến tướng
            </p>
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">
              Không chỉ dự đoán bằng cảm tính, JobShield kết hợp phân tích ngôn ngữ tự nhiên và đối chiếu dữ liệu căn cứ pháp lý đã xác minh.
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
            {/* Bento Card 1 */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex size-11 items-center justify-center rounded-xl bg-rose-50 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400">
                <AlertTriangle className="size-6" />
              </div>
              <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-slate-100">
                Phát hiện bẫy cọc tiền & thu phí
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Tự động nhận diện các yêu cầu đóng tiền đồng phục, tiền giữ chân, phí hồ sơ hoặc ép mua khóa đào tạo khi tuyển dụng.
              </p>
            </div>

            {/* Bento Card 2 */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex size-11 items-center justify-center rounded-xl bg-amber-50 text-amber-600 dark:bg-amber-950/50 dark:text-amber-400">
                <Zap className="size-6" />
              </div>
              <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-slate-100">
                Nhận diện bẫy làm nhiệm vụ
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Cảnh báo chiêu trò tuyển cộng tác viên Shopee, giật đơn hàng online, nạp tiền mở khóa tài khoản qua Telegram hay Zalo ẩn danh.
              </p>
            </div>

            {/* Bento Card 3 */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex size-11 items-center justify-center rounded-xl bg-sky-50 text-sky-600 dark:bg-sky-950/50 dark:text-sky-400">
                <Building2 className="size-6" />
              </div>
              <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-slate-100">
                Đối chiếu nguồn doanh nghiệp
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Kiểm tra chéo mã số thuế, domain email, website tuyển dụng và tài khoản thụ hưởng với cơ sở dữ liệu đã kiểm duyệt.
              </p>
            </div>

            {/* Bento Card 4 */}
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
              <div className="flex size-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400">
                <FileSearch className="size-6" />
              </div>
              <h3 className="mt-4 text-base font-bold text-slate-900 dark:text-slate-100">
                Minh bạch trích đoạn nguyên văn
              </h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Mọi kết luận đều dẫn nguồn câu chữ vi phạm trong bài đăng kèm giải thích căn cứ và danh sách việc cần hỏi lại nhà tuyển dụng.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 3 Step Workflow */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:py-24">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-xs font-bold uppercase tracking-wider text-sky-600 dark:text-sky-400">
            Quy trình trực quan
          </h2>
          <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950 sm:text-4xl dark:text-white">
            Chỉ 3 bước để kiểm tra một tin tuyển dụng
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 gap-8 md:grid-cols-3">
          <div className="relative flex flex-col items-center text-center">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-sky-600 text-xl font-bold text-white shadow-lg shadow-sky-600/30">
              1
            </div>
            <h3 className="mt-5 text-base font-bold text-slate-900 dark:text-slate-100">
              Dán nội dung hoặc tải ảnh
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              Dán văn bản tin tuyển dụng, tải ảnh chụp màn hình tin nhắn hoặc nhập đường link bài viết cần kiểm tra.
            </p>
          </div>

          <div className="relative flex flex-col items-center text-center">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-sky-600 text-xl font-bold text-white shadow-lg shadow-sky-600/30">
              2
            </div>
            <h3 className="mt-5 text-base font-bold text-slate-900 dark:text-slate-100">
              Rà quét và đối chiếu dữ liệu
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              Hệ thống kích hoạt tập hợp luật phát hiện dấu hiệu lừa đảo và so khớp thông tin với cơ sở dữ liệu xác minh.
            </p>
          </div>

          <div className="relative flex flex-col items-center text-center">
            <div className="flex size-14 items-center justify-center rounded-2xl bg-emerald-600 text-xl font-bold text-white shadow-lg shadow-emerald-600/30">
              3
            </div>
            <h3 className="mt-5 text-base font-bold text-slate-900 dark:text-slate-100">
              Nhận kết quả và khuyến nghị
            </h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              Nhận báo cáo mức độ rủi ro, phân tích căn cứ nguyên văn và các bước hành động an toàn cần thực hiện ngay.
            </p>
          </div>
        </div>
      </section>

      {/* Safety Notice & Community Callout */}
      <section className="bg-gradient-to-br from-slate-900 to-slate-950 py-16 text-white">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:flex lg:items-center lg:justify-between">
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 rounded-full bg-rose-500/20 px-3 py-1 text-xs font-semibold text-rose-300">
              <ShieldAlert className="size-3.5" />
              <span>Cảnh giác cao độ</span>
            </div>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Nhận thấy dấu hiệu nghi vấn?
            </h2>
            <p className="mt-3 text-sm text-slate-300 leading-relaxed">
              Hãy kiểm tra ngay trước khi chuyển bất kỳ khoản tiền nào hoặc cung cấp thông tin định danh cá nhân. Mọi kiểm tra tại JobShield đều hoàn toàn miễn phí và bảo mật.
            </p>
          </div>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row lg:mt-0">
            <Link
              href="/analyze"
              className="inline-flex items-center justify-center rounded-xl bg-sky-500 px-6 py-3.5 text-sm font-semibold text-white shadow-lg shadow-sky-500/25 transition-all hover:bg-sky-400 hover:shadow-sky-500/35"
            >
              Phân tích tin ngay
            </Link>
            <Link
              href="/safety"
              className="inline-flex items-center justify-center rounded-xl border border-slate-700 bg-slate-800/80 px-6 py-3.5 text-sm font-semibold text-slate-200 backdrop-blur transition-all hover:bg-slate-800 hover:text-white"
            >
              Xem các thủ đoạn phổ biến
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
