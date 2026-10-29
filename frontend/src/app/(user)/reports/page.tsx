"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useMyReports } from "@/hooks/use-reports";
import {
  ReportModerationTimeline,
  ReportStatusBadge,
} from "@/components/reports/report-status";
import { Report } from "@/types/api";

export default function MyReportsPage() {
  const [page, setPage] = useState(1);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const { data, isLoading, isError, error } = useMyReports(page, 10);

  const reports = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 10) || 1;

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Báo cáo của tôi
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Theo dõi tiến độ và quyết định xử lý của các báo cáo bạn đã gửi.
          </p>
        </div>
        <Link
          href="/reports/new"
          className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 transition-colors"
        >
          + Gửi báo cáo mới
        </Link>
      </div>

      {isLoading && (
        <div className="py-12 text-center text-slate-500">Đang tải danh sách báo cáo...</div>
      )}

      {isError && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          {error instanceof Error ? error.message : "Không thể tải danh sách báo cáo."}
        </div>
      )}

      {!isLoading && !isError && reports.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center">
          <p className="text-sm font-medium text-slate-600">
            Bạn chưa gửi báo cáo nào.
          </p>
          <p className="mt-1 text-xs text-slate-400">
            Khi phát hiện tin tuyển dụng đáng ngờ, bạn có thể gửi báo cáo kèm bằng chứng để bảo vệ cộng đồng.
          </p>
          <Link
            href="/reports/new"
            className="mt-4 inline-block text-sm font-semibold text-slate-900 underline hover:text-slate-700"
          >
            Gửi báo cáo ngay
          </Link>
        </div>
      )}

      {!isLoading && !isError && reports.length > 0 && (
        <div className="space-y-4">
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <ul className="divide-y divide-slate-200">
              {reports.map((report) => (
                <li
                  key={report.id}
                  className="p-5 hover:bg-slate-50/70 transition-colors cursor-pointer"
                  onClick={() =>
                    setSelectedReport((prev) => (prev?.id === report.id ? null : report))
                  }
                >
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <span className="font-semibold text-slate-900">
                          {report.reason}
                        </span>
                        <ReportStatusBadge status={report.status} />
                      </div>
                      <p className="text-sm text-slate-600 line-clamp-2">
                        {report.description}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-slate-500 pt-1">
                        <span>
                          Thời gian:{" "}
                          <time dateTime={report.created_at}>
                            {new Date(report.created_at).toLocaleString("vi-VN")}
                          </time>
                        </span>
                        {report.evidences?.length > 0 && (
                          <span>Bằng chứng: {report.evidences.length} mục</span>
                        )}
                        {report.analysis_id && (
                          <span className="font-mono text-slate-400">
                            ID phân tích: {report.analysis_id.slice(0, 8)}...
                          </span>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      className="text-xs font-semibold text-slate-700 underline underline-offset-4 self-start sm:self-center"
                    >
                      {selectedReport?.id === report.id ? "Đóng chi tiết" : "Xem chi tiết"}
                    </button>
                  </div>

                  {selectedReport?.id === report.id && (
                    <div className="mt-4 pt-4 border-t border-slate-200 space-y-4 cursor-default" onClick={(e) => e.stopPropagation()}>
                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                          Nội dung mô tả đầy đủ
                        </h4>
                        <p className="text-sm text-slate-800 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 border border-slate-200">
                          {report.description}
                        </p>
                      </div>

                      {report.evidences?.length > 0 && (
                        <div>
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                            Danh sách bằng chứng
                          </h4>
                          <ul className="space-y-1.5">
                            {report.evidences.map((ev) => (
                              <li
                                key={ev.id}
                                className="text-xs rounded border border-slate-200 p-2 bg-white flex items-center justify-between"
                              >
                                <span className="font-semibold text-slate-600 uppercase mr-2">
                                  [{ev.evidence_type}]
                                </span>
                                <span className="text-slate-800 flex-1 truncate">
                                  {ev.evidence_type === "url" ? (
                                    <a
                                      href={ev.source_url || "#"}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-blue-600 hover:underline"
                                    >
                                      {ev.source_url}
                                    </a>
                                  ) : (
                                    ev.content
                                  )}
                                </span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      <div>
                        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                          Lịch sử xử lý từ ban quản trị
                        </h4>
                        <ReportModerationTimeline actions={report.moderation_actions} />
                      </div>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>

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
  );
}
