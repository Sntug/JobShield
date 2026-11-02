"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePublicWarnings } from "@/hooks/use-admin";
import { ShieldAlert, Flag, ExternalLink } from "lucide-react";

export default function SafetyWarningsPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, error } = usePublicWarnings(page, 10);

  const warnings = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 10) || 1;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Breadcrumb */}
      <nav aria-label="Điều hướng" className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        <Link href="/" className="hover:text-slate-900 dark:hover:text-slate-100 transition-colors">Trang chủ</Link>
        <span>/</span>
        <span className="text-slate-900 dark:text-slate-100 font-semibold">An toàn & Cảnh báo</span>
      </nav>

      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-950 dark:text-white">
          Thông tin An toàn & Cảnh báo Tuyển dụng
        </h1>
        <p className="mt-2 text-sm sm:text-base leading-relaxed text-slate-600 dark:text-slate-400">
          Tổng hợp các thủ đoạn lừa đảo việc làm, hành vi mạo danh doanh nghiệp đã được kiểm chứng và khuyến cáo an toàn cho người tìm việc.
        </p>
      </div>

      {/* 3 Core Safety Principles */}
      <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-6 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/30 space-y-4">
        <h2 className="text-sm font-bold uppercase tracking-wider text-amber-950 dark:text-amber-200 flex items-center gap-2">
          <ShieldAlert className="size-5 text-amber-600" />
          <span>3 Nguyên tắc an toàn cốt lõi khi tìm việc</span>
        </h2>
        <ul className="list-disc list-inside space-y-2 text-sm text-amber-900 dark:text-amber-200 leading-relaxed">
          <li>
            <strong className="text-amber-950 dark:text-amber-100 font-semibold">Tuyệt đối không đóng phí:</strong> Doanh nghiệp chân chính không thu phí xét tuyển, đồng phục, đặt cọc phỏng vấn hay tiền hồ sơ.
          </li>
          <li>
            <strong className="text-amber-950 dark:text-amber-100 font-semibold">Cảnh giác bẫy nhiệm vụ / giật đơn:</strong> Không tham gia các công việc yêu cầu nạp tiền, nạp thẻ hoặc chuyển khoản để nhận hoa hồng.
          </li>
          <li>
            <strong className="text-amber-950 dark:text-amber-100 font-semibold">Bảo vệ dữ liệu cá nhân:</strong> Không gửi ảnh hai mặt CCCD hoặc cung cấp mã OTP ngân hàng cho các liên hệ qua Telegram hoặc Zalo ẩn danh.
          </li>
        </ul>
      </div>

      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">
            Cảnh báo cộng đồng mới nhất ({total})
          </h2>
          <Link
            href="/reports/new"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-800 dark:text-sky-400 hover:underline"
          >
            <Flag className="size-3.5" />
            <span>Phát hiện dấu hiệu mới? Gửi báo cáo ngay →</span>
          </Link>
        </div>

        {isLoading && (
          <div className="rounded-2xl border border-slate-200 bg-white py-16 text-center text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            Đang tải danh sách cảnh báo công khai...
          </div>
        )}

        {isError && (
          <div
            role="alert"
            className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200"
          >
            {error instanceof Error ? error.message : "Không thể tải danh sách cảnh báo."}
          </div>
        )}

        {!isLoading && !isError && warnings.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-500 dark:border-slate-800">
            Hiện chưa có bản cảnh báo công khai nào được ban hành.
          </div>
        )}

        {!isLoading && !isError && warnings.length > 0 && (
          <div className="space-y-4">
            {warnings.map((warning) => (
              <article
                key={warning.id}
                className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                    <Link
                      href={`/safety/${warning.id}`}
                      className="hover:text-sky-600 transition-colors"
                    >
                      {warning.title_vi}
                    </Link>
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-rose-50 border border-rose-200 px-2.5 py-0.5 text-xs font-bold text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/60 dark:text-rose-300">
                      Cảnh báo v{warning.revision}
                    </span>
                    <time
                      dateTime={warning.published_at || warning.created_at}
                      className="text-xs text-slate-500"
                    >
                      {new Date(warning.published_at || warning.created_at).toLocaleDateString(
                        "vi-VN"
                      )}
                    </time>
                  </div>
                </div>

                <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed dark:text-slate-300">
                  {warning.public_summary_vi}
                </p>

                {warning.public_sources_snapshot &&
                  warning.public_sources_snapshot.length > 0 && (
                    <div className="pt-3 border-t border-slate-100 dark:border-slate-800">
                      <p className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
                        Căn cứ xác minh & Nguồn thông báo:
                      </p>
                      <ul className="space-y-1.5 text-xs">
                        {warning.public_sources_snapshot.map((src, idx) => (
                          <li key={idx} className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                            <span className="text-sky-500 font-bold">•</span>
                            <span className="font-medium text-slate-800 dark:text-slate-200">
                              {String(src.label_vi || src.label || "Nguồn thông báo")}
                            </span>
                            {src.url ? (
                              <a
                                href={String(src.url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 text-sky-600 hover:underline truncate max-w-sm dark:text-sky-400"
                              >
                                <span>({String(src.url)})</span>
                                <ExternalLink className="size-3 shrink-0" />
                              </a>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
              </article>
            ))}

            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                >
                  ← Trang trước
                </button>
                <span className="text-xs font-medium text-slate-500">
                  Trang {page} / {totalPages}
                </span>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 disabled:opacity-40 shadow-sm hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
                >
                  Trang sau →
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
