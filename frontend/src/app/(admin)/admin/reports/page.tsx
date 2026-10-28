"use client";

import React, { useState } from "react";
import { useAdminReports } from "@/hooks/use-admin";
import { ReportStatusBadge } from "@/components/reports/report-status";
import { ModerationForm } from "@/components/admin/moderation-form";
import { ReportAdmin } from "@/types/api";

const STATUS_FILTERS = [
  { value: "", label: "Tất cả" },
  { value: "pending", label: "Chờ duyệt" },
  { value: "under_review", label: "Đang xử lý" },
  { value: "verified", label: "Đã xác minh" },
  { value: "rejected", label: "Đã từ chối" },
];

export default function AdminReportsPage() {
  const [selectedStatus, setSelectedStatus] = useState<string>("");
  const [page, setPage] = useState(1);
  const [moderatingReport, setModeratingReport] = useState<ReportAdmin | null>(null);

  const { data, isLoading, isError, error, refetch } = useAdminReports(
    selectedStatus || undefined,
    page,
    10
  );

  const reports = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 10) || 1;

  const handleFilterChange = (status: string) => {
    setSelectedStatus(status);
    setPage(1);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Hàng đợi kiểm duyệt báo cáo
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Đánh giá bằng chứng, ghi nhận ghi chú nội bộ và quyết định trạng thái báo cáo cộng đồng.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto border-b border-slate-200 pb-2">
        {STATUS_FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            onClick={() => handleFilterChange(filter.value)}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
              selectedStatus === filter.value
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="py-16 text-center text-sm text-slate-500">
          Đang tải danh sách báo cáo kiểm duyệt...
        </div>
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
        <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-500">
          Không có báo cáo nào trong hàng đợi này.
        </div>
      )}

      {!isLoading && !isError && reports.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase">
              <tr>
                <th className="px-4 py-3">Lý do & Mô tả</th>
                <th className="px-4 py-3">Người báo cáo</th>
                <th className="px-4 py-3">Thời gian</th>
                <th className="px-4 py-3">Trạng thái</th>
                <th className="px-4 py-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {reports.map((report) => (
                <tr key={report.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-4 py-3 max-w-xs">
                    <p className="font-bold text-slate-900 truncate">{report.reason}</p>
                    <p className="text-slate-500 line-clamp-1 mt-0.5">{report.description}</p>
                    {report.evidences?.length > 0 && (
                      <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded mt-1 inline-block">
                        {report.evidences.length} bằng chứng
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <p className="font-medium text-slate-800">{report.reporter_name || "N/A"}</p>
                    <p className="text-slate-400">{report.reporter_email || "Ẩn danh"}</p>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-500">
                    <time dateTime={report.created_at}>
                      {new Date(report.created_at).toLocaleDateString("vi-VN")}
                    </time>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <ReportStatusBadge status={report.status} />
                    <span className="ml-1.5 text-[10px] text-slate-400 font-mono">
                      v{report.version}
                    </span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <button
                      type="button"
                      onClick={() => setModeratingReport(report)}
                      className="rounded-lg bg-slate-900 px-3 py-1.5 font-semibold text-white hover:bg-slate-800 transition-colors"
                    >
                      Kiểm duyệt
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 bg-white">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 disabled:opacity-40"
              >
                Trước
              </button>
              <span className="text-xs text-slate-500">
                Trang {page} / {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 disabled:opacity-40"
              >
                Sau
              </button>
            </div>
          )}
        </div>
      )}

      {/* Moderation Modal */}
      {moderatingReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 overflow-y-auto">
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between border-b border-slate-200 pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Kiểm duyệt báo cáo: {moderatingReport.reason}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Người gửi: {moderatingReport.reporter_name} ({moderatingReport.reporter_email})
                </p>
              </div>
              <button
                type="button"
                onClick={() => setModeratingReport(null)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                <span className="font-bold text-slate-700 uppercase">Mô tả của người báo cáo:</span>
                <p className="mt-1 text-slate-800 whitespace-pre-wrap">{moderatingReport.description}</p>
              </div>

              {moderatingReport.evidences?.length > 0 && (
                <div>
                  <span className="font-bold text-slate-700 uppercase">Bằng chứng đính kèm:</span>
                  <ul className="mt-1 space-y-1">
                    {moderatingReport.evidences.map((ev) => (
                      <li key={ev.id} className="p-2 bg-white rounded border border-slate-200 flex items-center gap-2">
                        <span className="font-bold text-slate-500">[{ev.evidence_type}]</span>
                        <span className="truncate">
                          {ev.evidence_type === "url" ? (
                            <a href={ev.source_url || "#"} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">
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

              {moderatingReport.moderation_actions?.length > 0 && (
                <div>
                  <span className="font-bold text-slate-700 uppercase">Lịch sử kiểm duyệt trước đó:</span>
                  <ul className="mt-1 space-y-1">
                    {moderatingReport.moderation_actions.map((act) => (
                      <li key={act.id} className="p-2 bg-white rounded border border-slate-200 text-slate-700">
                        <p className="font-semibold">{act.decision_summary}</p>
                        {act.private_note && (
                          <p className="text-rose-700 italic mt-0.5">Note nội bộ: {act.private_note}</p>
                        )}
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          Duyệt bởi: {act.moderator_name || "Admin"} • {new Date(act.created_at).toLocaleString("vi-VN")}
                        </p>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <ModerationForm
              report={moderatingReport}
              onSuccess={() => {
                setModeratingReport(null);
                refetch();
              }}
              onCancel={() => setModeratingReport(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
