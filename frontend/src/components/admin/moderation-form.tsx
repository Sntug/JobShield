"use client";

import React, { useState } from "react";
import { useModerateReport } from "@/hooks/use-admin";
import { ReportAdmin } from "@/types/api";

interface ModerationFormProps {
  report: ReportAdmin;
  onSuccess: () => void;
  onCancel: () => void;
}

export function ModerationForm({ report, onSuccess, onCancel }: ModerationFormProps) {
  const moderateMutation = useModerateReport();

  const [actionType, setActionType] = useState<"review" | "request_evidence" | "verify" | "reject">("verify");
  const [toStatus, setToStatus] = useState<"pending" | "under_review" | "verified" | "rejected">("verified");
  const [decisionSummary, setDecisionSummary] = useState("");
  const [privateNote, setPrivateNote] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleActionChange = (action: "review" | "request_evidence" | "verify" | "reject") => {
    setActionType(action);
    if (action === "review" || action === "request_evidence") {
      setToStatus("under_review");
    } else if (action === "verify") {
      setToStatus("verified");
    } else if (action === "reject") {
      setToStatus("rejected");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!decisionSummary.trim()) {
      setErrorMessage("Vui lòng nhập tóm tắt quyết định kiểm duyệt.");
      return;
    }

    try {
      await moderateMutation.mutateAsync({
        reportId: report.id,
        payload: {
          action_type: actionType,
          to_status: toStatus,
          decision_summary: decisionSummary.trim(),
          private_note: privateNote.trim() || undefined,
          expected_version: report.version,
        },
      });
      onSuccess();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra khi kiểm duyệt.";
      setErrorMessage(msg);
    }
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-4">
      {errorMessage && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800"
        >
          {errorMessage}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-slate-500 bg-slate-50 p-2.5 rounded-lg border border-slate-200">
        <span>
          Báo cáo: <span className="font-mono font-bold text-slate-800">{report.id.slice(0, 8)}...</span>
        </span>
        <span>
          Phiên bản kiểm soát: <span className="font-bold text-slate-800">v{report.version}</span>
        </span>
      </div>

      <div>
        <label className="block text-xs font-semibold text-slate-900 mb-1">
          Hành động kiểm duyệt <span className="text-rose-500">*</span>
        </label>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <button
            type="button"
            onClick={() => handleActionChange("verify")}
            className={`p-2 rounded-lg border text-left font-medium transition-colors ${
              actionType === "verify"
                ? "border-rose-500 bg-rose-50 text-rose-900"
                : "border-slate-200 hover:bg-slate-50 text-slate-700"
            }`}
          >
            ✓ Xác nhận có rủi ro / lừa đảo
          </button>
          <button
            type="button"
            onClick={() => handleActionChange("reject")}
            className={`p-2 rounded-lg border text-left font-medium transition-colors ${
              actionType === "reject"
                ? "border-slate-500 bg-slate-100 text-slate-900"
                : "border-slate-200 hover:bg-slate-50 text-slate-700"
            }`}
          >
            ✕ Từ chối báo cáo
          </button>
          <button
            type="button"
            onClick={() => handleActionChange("review")}
            className={`p-2 rounded-lg border text-left font-medium transition-colors ${
              actionType === "review"
                ? "border-blue-500 bg-blue-50 text-blue-900"
                : "border-slate-200 hover:bg-slate-50 text-slate-700"
            }`}
          >
            ⋯ Đang tiến hành xác minh
          </button>
          <button
            type="button"
            onClick={() => handleActionChange("request_evidence")}
            className={`p-2 rounded-lg border text-left font-medium transition-colors ${
              actionType === "request_evidence"
                ? "border-amber-500 bg-amber-50 text-amber-900"
                : "border-slate-200 hover:bg-slate-50 text-slate-700"
            }`}
          >
            ? Yêu cầu thêm bằng chứng
          </button>
        </div>
      </div>

      <div>
        <label htmlFor="decision-summary" className="block text-xs font-semibold text-slate-900">
          Tóm tắt quyết định (Người báo cáo đọc được) <span className="text-rose-500">*</span>
        </label>
        <textarea
          id="decision-summary"
          rows={3}
          value={decisionSummary}
          onChange={(e) => setDecisionSummary(e.target.value)}
          placeholder="Ví dụ: Đã xác minh tài khoản ngân hàng và kênh Telegram không thuộc quản lý của doanh nghiệp."
          className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-800 focus:outline-none"
          required
        />
      </div>

      <div>
        <label htmlFor="private-note" className="block text-xs font-semibold text-slate-900">
          Ghi chú nội bộ quản trị (Chỉ Admin xem được)
        </label>
        <textarea
          id="private-note"
          rows={2}
          value={privateNote}
          onChange={(e) => setPrivateNote(e.target.value)}
          placeholder="Ghi chú điều tra, đối chiếu IP hoặc danh sách nghi vấn..."
          className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-800 focus:outline-none bg-slate-50/50"
        />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Hủy
        </button>
        <button
          type="submit"
          disabled={moderateMutation.isPending}
          className="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {moderateMutation.isPending ? "Đang lưu quyết định..." : "Lưu quyết định kiểm duyệt"}
        </button>
      </div>
    </form>
  );
}
