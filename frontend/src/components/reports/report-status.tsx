import React from "react";
import { ModerationAction } from "@/types/api";

interface ReportStatusBadgeProps {
  status: "pending" | "under_review" | "verified" | "rejected" | string;
}

export function ReportStatusBadge({ status }: ReportStatusBadgeProps) {
  let label = "Chờ duyệt";
  let colorClasses = "bg-amber-50 text-amber-800 border-amber-200";

  if (status === "under_review") {
    label = "Đang xử lý";
    colorClasses = "bg-blue-50 text-blue-800 border-blue-200";
  } else if (status === "verified") {
    label = "Đã xác minh dấu hiệu";
    colorClasses = "bg-rose-50 text-rose-800 border-rose-200";
  } else if (status === "rejected") {
    label = "Đã từ chối";
    colorClasses = "bg-slate-100 text-slate-700 border-slate-200";
  }

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${colorClasses}`}
    >
      {label}
    </span>
  );
}

interface ReportModerationTimelineProps {
  actions: ModerationAction[];
}

export function ReportModerationTimeline({ actions }: ReportModerationTimelineProps) {
  if (!actions || actions.length === 0) {
    return (
      <p className="text-sm text-slate-500 italic">
        Chưa có hành động kiểm duyệt nào từ ban quản trị.
      </p>
    );
  }

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {actions.map((act, idx) => (
          <li key={act.id}>
            <div className="relative pb-8">
              {idx !== actions.length - 1 && (
                <span
                  className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-slate-200"
                  aria-hidden="true"
                />
              )}
              <div className="relative flex space-x-3 items-start">
                <div>
                  <span className="h-8 w-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center ring-8 ring-white text-xs font-bold text-slate-600">
                    {idx + 1}
                  </span>
                </div>
                <div className="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      Quyết định:{" "}
                      <span className="font-semibold text-slate-800">
                        {act.decision_summary}
                      </span>
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Trạng thái chuyển: <span className="font-mono">{act.from_status}</span> →{" "}
                      <span className="font-mono font-semibold">{act.to_status}</span>
                    </p>
                  </div>
                  <div className="text-right text-xs whitespace-nowrap text-slate-500">
                    <time dateTime={act.created_at}>
                      {new Date(act.created_at).toLocaleString("vi-VN")}
                    </time>
                  </div>
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
