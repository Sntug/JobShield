"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePublicWarnings } from "@/hooks/use-admin";

export default function SafetyWarningsPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading, isError, error } = usePublicWarnings(page, 10);

  const warnings = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 10) || 1;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
          Thông tin An toàn & Cảnh báo Tuyển dụng
        </h1>
        <p className="mt-2 text-base text-slate-600">
          Tổng hợp các thủ đoạn lừa đảo việc làm, hành vi mạo danh doanh nghiệp đã được kiểm chứng và khuyến cáo an toàn cho người tìm việc.
        </p>
      </div>

      <div className="rounded-xl border border-amber-200 bg-amber-50/60 p-6 space-y-3">
        <h2 className="text-base font-bold text-amber-900 flex items-center gap-2">
          <span>⚠️</span> 3 Nguyên tắc an toàn cốt lõi khi tìm việc
        </h2>
        <ul className="list-disc list-inside space-y-1.5 text-sm text-amber-800">
          <li>
            <strong className="text-amber-950">Tuyệt đối không đóng phí:</strong> Doanh nghiệp chân chính không thu phí xét tuyển, đồng phục, đặt cọc phỏng vấn hay tiền hồ sơ.
          </li>
          <li>
            <strong className="text-amber-950">Cảnh giác bẫy nhiệm vụ / giật đơn:</strong> Không tham gia các công việc yêu cầu nạp tiền, nạp thẻ hoặc chuyển khoản để nhận hoa hồng.
          </li>
          <li>
            <strong className="text-amber-950">Bảo vệ dữ liệu cá nhân:</strong> Không gửi ảnh hai mặt CCCD hoặc cung cấp mã OTP ngân hàng cho các liên hệ qua Telegram hoặc Zalo ẩn danh.
          </li>
        </ul>
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-900">
            Cảnh báo cộng đồng mới nhất ({total})
          </h2>
          <Link
            href="/reports/new"
            className="text-xs font-semibold text-slate-700 underline hover:text-slate-900"
          >
            Phát hiện dấu hiệu mới? Gửi báo cáo ngay →
          </Link>
        </div>

        {isLoading && (
          <div className="py-16 text-center text-sm text-slate-500">
            Đang tải danh sách cảnh báo công khai...
          </div>
        )}

        {isError && (
          <div
            role="alert"
            className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
          >
            {error instanceof Error ? error.message : "Không thể tải danh sách cảnh báo."}
          </div>
        )}

        {!isLoading && !isError && warnings.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-500">
            Hiện chưa có bản cảnh báo công khai nào được ban hành.
          </div>
        )}

        {!isLoading && !isError && warnings.length > 0 && (
          <div className="space-y-4">
            {warnings.map((warning) => (
              <article
                key={warning.id}
                className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <h3 className="text-lg font-bold text-slate-900">
                    <Link href={`/safety/${warning.id}`} className="hover:underline">{warning.title_vi}</Link>
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-rose-50 border border-rose-200 px-2 py-0.5 text-xs font-bold text-rose-800">
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

                <p className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed">
                  {warning.public_summary_vi}
                </p>

                {warning.public_sources_snapshot &&
                  warning.public_sources_snapshot.length > 0 && (
                    <div className="pt-2 border-t border-slate-100">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                        Căn cứ xác minh & Nguồn thông báo:
                      </p>
                      <ul className="space-y-1 text-xs">
                        {warning.public_sources_snapshot.map((src, idx) => (
                          <li key={idx} className="flex items-center gap-2 text-slate-600">
                            <span>•</span>
                            <span>{String(src.label_vi || src.label || "Nguồn thông báo")}</span>
                            {src.url ? (
                              <a
                                href={String(src.url)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:underline truncate max-w-sm"
                              >
                                ({String(src.url)})
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
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-40"
                >
                  ← Trang trước
                </button>
                <span className="text-xs text-slate-500">
                  Trang {page} / {totalPages}
                </span>
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 disabled:opacity-40"
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
