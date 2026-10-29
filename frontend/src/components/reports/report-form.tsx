"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useSubmitReport } from "@/hooks/use-reports";
import { EvidenceType, ReportEvidenceCreate } from "@/types/api";

const PRESET_REASONS = [
  "Phí tuyển dụng trước (đồng phục, tài liệu, hồ sơ)",
  "Đặt cọc trước phỏng vấn",
  "Nhiệm vụ có nạp tiền / giật đơn ảo",
  "Yêu cầu chuyển tiền qua tài khoản cá nhân",
  "Chỉ dấu mạo danh doanh nghiệp uy tín",
  "Yêu cầu dữ liệu nhạy cảm (ảnh CCCD hai mặt, mã OTP)",
  "Hứa hẹn thu nhập phi thực tế",
  "Khác",
];

interface ReportFormProps {
  initialAnalysisId?: string;
}

export function ReportForm({ initialAnalysisId = "" }: ReportFormProps) {
  const router = useRouter();
  const submitMutation = useSubmitReport();

  const [selectedPreset, setSelectedPreset] = useState(PRESET_REASONS[0]);
  const [customReason, setCustomReason] = useState("");
  const [description, setDescription] = useState("");
  const [analysisId, setAnalysisId] = useState(initialAnalysisId);
  const [evidences, setEvidences] = useState<ReportEvidenceCreate[]>([]);
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("text");
  const [evidenceInput, setEvidenceInput] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);

  const finalReason = selectedPreset === "Khác" ? customReason.trim() : selectedPreset;

  const handleAddEvidence = () => {
    const val = evidenceInput.trim();
    if (!val) return;

    if (evidenceType === "url") {
      if (!val.startsWith("http://") && !val.startsWith("https://")) {
        setFormError("Liên kết bằng chứng phải bắt đầu bằng http:// hoặc https://");
        return;
      }
      setEvidences((prev) => [...prev, { evidence_type: "url", source_url: val }]);
    } else {
      setEvidences((prev) => [...prev, { evidence_type: "text", content: val }]);
    }

    setEvidenceInput("");
    setFormError(null);
  };

  const handleRemoveEvidence = (index: number) => {
    setEvidences((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!finalReason) {
      setFormError("Vui lòng chọn hoặc nhập lý do báo cáo.");
      return;
    }

    if (description.trim().length < 5) {
      setFormError("Mô tả chi tiết phải chứa ít nhất 5 ký tự.");
      return;
    }

    try {
      const res = await submitMutation.mutateAsync({
        reason: finalReason,
        description: description.trim(),
        analysis_id: analysisId.trim() || undefined,
        evidences,
      });
      setSuccessId(res.id);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Đã có lỗi xảy ra khi gửi báo cáo.";
      setFormError(message);
    }
  };

  if (successId) {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
        <h3 className="text-lg font-bold text-emerald-900">Gửi báo cáo thành công!</h3>
        <p className="mt-2 text-sm text-emerald-700">
          Cảm ơn bạn đã đóng góp thông tin. Báo cáo của bạn đã được ghi nhận và đưa vào hàng đợi kiểm duyệt của ban quản trị.
        </p>
        <div className="mt-6 flex justify-center gap-4">
          <button
            type="button"
            onClick={() => router.push("/reports")}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors"
          >
            Xem danh sách báo cáo của tôi
          </button>
          <button
            type="button"
            onClick={() => {
              setSuccessId(null);
              setDescription("");
              setCustomReason("");
              setEvidences([]);
            }}
            className="rounded-lg border border-emerald-300 bg-white px-4 py-2 text-sm font-medium text-emerald-800 hover:bg-emerald-50 transition-colors"
          >
            Gửi báo cáo khác
          </button>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {formError && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          {formError}
        </div>
      )}

      <div>
        <label htmlFor="report-reason-select" className="block text-sm font-semibold text-slate-900">
          Lý do báo cáo <span className="text-rose-500">*</span>
        </label>
        <select
          id="report-reason-select"
          value={selectedPreset}
          onChange={(e) => setSelectedPreset(e.target.value)}
          className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-slate-500 focus:outline-none"
        >
          {PRESET_REASONS.map((reason) => (
            <option key={reason} value={reason}>
              {reason}
            </option>
          ))}
        </select>

        {selectedPreset === "Khác" && (
          <input
            type="text"
            placeholder="Nhập lý do cụ thể..."
            value={customReason}
            onChange={(e) => setCustomReason(e.target.value)}
            className="mt-2 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800 focus:border-slate-500 focus:outline-none"
            aria-label="Lý do cụ thể"
            required
          />
        )}
      </div>

      <div>
        <label htmlFor="report-description" className="block text-sm font-semibold text-slate-900">
          Mô tả chi tiết sự việc <span className="text-rose-500">*</span>
        </label>
        <p className="text-xs text-slate-500 mt-0.5">
          Mô tả tình huống, cách thức đối tượng liên hệ, số tiền đòi thu hoặc các yêu cầu đáng ngờ.
        </p>
        <textarea
          id="report-description"
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Ví dụ: Đối tượng tự xưng là tuyển dụng của công ty A, yêu cầu đóng 300.000 VNĐ vào tài khoản cá nhân để nhận hồ sơ..."
          className="mt-1.5 block w-full rounded-lg border border-slate-300 bg-white p-3 text-sm text-slate-800 focus:border-slate-500 focus:outline-none"
          required
        />
      </div>

      <div>
        <label htmlFor="report-analysis-id" className="block text-sm font-medium text-slate-700">
          Mã phân tích liên quan (tùy chọn)
        </label>
        <input
          id="report-analysis-id"
          type="text"
          value={analysisId}
          onChange={(e) => setAnalysisId(e.target.value)}
          placeholder="Ví dụ: 8e1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d"
          className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 focus:border-slate-500 focus:outline-none"
        />
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
        <label className="block text-sm font-semibold text-slate-900 mb-2">
          Đính kèm bằng chứng (tùy chọn, tối đa 10 mục)
        </label>

        <div className="flex flex-col sm:flex-row gap-2">
          <select
            value={evidenceType}
            onChange={(e) => setEvidenceType(e.target.value as EvidenceType)}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 focus:outline-none"
            aria-label="Loại bằng chứng"
          >
            <option value="text">Đoạn tin nhắn / Văn bản</option>
            <option value="url">Liên kết (URL)</option>
          </select>
          <input
            type="text"
            value={evidenceInput}
            onChange={(e) => setEvidenceInput(e.target.value)}
            placeholder={
              evidenceType === "url"
                ? "https://facebook.com/trang-tuyen-dung-gia-mao"
                : "Nội dung trích dẫn tin nhắn, số tài khoản nhận tiền..."
            }
            className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-800 focus:outline-none"
            aria-label="Nội dung bằng chứng"
          />
          <button
            type="button"
            onClick={handleAddEvidence}
            className="rounded-lg bg-slate-800 px-3.5 py-1.5 text-sm font-medium text-white hover:bg-slate-700 transition-colors"
          >
            Thêm
          </button>
        </div>

        {evidences.length > 0 && (
          <ul className="mt-3 divide-y divide-slate-200 border-t border-slate-200 pt-2 text-sm">
            {evidences.map((ev, idx) => (
              <li key={idx} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-slate-200 px-2 py-0.5 text-xs font-semibold uppercase text-slate-700">
                    {ev.evidence_type}
                  </span>
                  <span className="text-slate-800 break-all">
                    {ev.evidence_type === "url" ? ev.source_url : ev.content}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveEvidence(idx)}
                  className="text-xs text-rose-600 hover:text-rose-800 font-medium ml-2"
                >
                  Xóa
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="pt-2 flex justify-end">
        <button
          type="submit"
          disabled={submitMutation.isPending}
          className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
        >
          {submitMutation.isPending ? "Đang gửi báo cáo..." : "Gửi báo cáo"}
        </button>
      </div>
    </form>
  );
}
