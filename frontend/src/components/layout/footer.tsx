import React from "react";
import Link from "next/link";
import { ShieldAlert, ShieldCheck } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white text-slate-600 transition-colors dark:border-slate-800 dark:bg-slate-950 dark:text-slate-400">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="grid grid-cols-1 gap-8 md:grid-cols-4">
          {/* Cột 1: Thương hiệu & Sứ mệnh */}
          <div className="space-y-4 md:col-span-1">
            <Link href="/" className="inline-flex items-center gap-2.5 text-lg font-bold tracking-tight text-slate-950 dark:text-slate-100">
              <span className="flex size-8 items-center justify-center rounded-lg bg-sky-600 text-white shadow-sm shadow-sky-600/30">
                <ShieldCheck className="size-5" />
              </span>
              <span>JobShield</span>
            </Link>
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Hệ thống phòng vệ và đối chiếu tin tuyển dụng thông minh. Bóc tách dấu hiệu lừa đảo, kiểm tra chéo pháp nhân và bảo vệ ứng viên trước khi ứng tuyển.
            </p>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Hệ thống giám sát an toàn hoạt động
            </div>
          </div>

          {/* Cột 2: Tính năng cốt lõi */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-slate-200">
              Công cụ kiểm tra
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/analyze" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Phân tích tin tuyển dụng
                </Link>
              </li>
              <li>
                <Link href="/verify-employer" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Xác minh nhà tuyển dụng
                </Link>
              </li>
              <li>
                <Link href="/safety" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Thư viện cảnh báo an toàn
                </Link>
              </li>
              <li>
                <Link href="/reports/new" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Gửi báo cáo lừa đảo mới
                </Link>
              </li>
            </ul>
          </div>

          {/* Cột 3: Người dùng & Pháp lý */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-slate-200">
              Tài khoản & Dịch vụ
            </h4>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/dashboard" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Bảng điều khiển cá nhân
                </Link>
              </li>
              <li>
                <Link href="/history" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Lịch sử phân tích
                </Link>
              </li>
              <li>
                <Link href="/saved" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Tin tuyển dụng đã lưu
                </Link>
              </li>
              <li>
                <Link href="/reports" className="hover:text-sky-600 dark:hover:text-sky-400 transition-colors">
                  Theo dõi báo cáo đã gửi
                </Link>
              </li>
            </ul>
          </div>

          {/* Cột 4: Nguyên tắc an toàn & Miễn trừ */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-900 dark:text-slate-200">
              Khuyến cáo an toàn
            </h4>
            <div className="rounded-lg border border-amber-200 bg-amber-50/70 p-3 text-[11px] leading-relaxed text-amber-900 dark:border-amber-900/40 dark:bg-amber-950/30 dark:text-amber-200">
              <p className="font-semibold mb-1 flex items-center gap-1.5 text-amber-950 dark:text-amber-100">
                <ShieldAlert className="size-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                Nguyên tắc bất di bất dịch:
              </p>
              Tuyệt đối không đóng phí xét tuyển, không chuyển khoản làm nhiệm vụ nạp tiền và không giao ảnh 2 mặt CCCD qua mạng xã hội ẩn danh.
            </div>
            <p className="text-[11px] text-slate-500 leading-normal">
              * Khớp nguồn thông tin không bảo đảm tin an toàn 100%. Luôn liên hệ trực tiếp qua số tổng đài chính thức của doanh nghiệp.
            </p>
          </div>
        </div>

        {/* Dòng đáy bản quyền & chứng nhận */}
        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-slate-100 pt-6 text-xs text-slate-400 sm:flex-row dark:border-slate-800">
          <p>© {new Date().getFullYear()} JobShield. Dự án bảo vệ ứng viên tìm việc phi lợi nhuận.</p>
          <div className="flex items-center gap-4">
            <Link href="/safety" className="hover:text-slate-600 dark:hover:text-slate-300 transition-colors">
              Quy tắc cộng đồng
            </Link>
            <span>•</span>
            <span className="text-slate-400">Tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
