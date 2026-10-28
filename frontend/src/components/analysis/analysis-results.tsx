"use client";

import React from "react";
import { AnalysisResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { EvidenceList } from "@/components/analysis/evidence-list";

interface AnalysisResultsProps {
  analysis: AnalysisResponse;
  onReset: () => void;
}

export function AnalysisResults({ analysis, onReset }: AnalysisResultsProps) {
  const {
    risk_label_vi,
    verification_label_vi,
    finding_vi,
    job,
    indicators,
    evidence,
    actions_vi,
    expires_at,
  } = analysis;

  const getRiskBadgeColor = (risk: string) => {
    switch (risk) {
      case "Rủi ro cao":
        return "bg-red-100 text-red-800 border-red-200 dark:bg-red-950/50 dark:text-red-300 dark:border-red-800";
      case "Ít dấu hiệu rủi ro":
        return "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950/50 dark:text-emerald-300 dark:border-emerald-800";
      default:
        return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950/50 dark:text-amber-300 dark:border-amber-800";
    }
  };

  const getVerificationBadgeColor = (verif: string) => {
    switch (verif) {
      case "Khớp nguồn đã xác minh":
        return "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-950/50 dark:text-blue-300 dark:border-blue-800";
      case "Thông tin xung đột":
        return "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-950/50 dark:text-orange-300 dark:border-orange-800";
      default:
        return "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
    }
  };

  const formattedExpiry = expires_at
    ? new Date(expires_at).toLocaleString("vi-VN", {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : null;

  return (
    <div className="w-full space-y-6 break-words">
      {/* Top Banner: Status, Badges & DEMO tag */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${getRiskBadgeColor(
                risk_label_vi
              )}`}
            >
              Mức độ: {risk_label_vi}
            </span>
            <span
              className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${getVerificationBadgeColor(
                verification_label_vi
              )}`}
            >
              Xác minh: {verification_label_vi}
            </span>
            {evidence.is_demo && (
              <span className="inline-flex items-center rounded-full border border-purple-200 bg-purple-100 px-2.5 py-0.5 text-xs font-semibold text-purple-800 dark:border-purple-800 dark:bg-purple-950/50 dark:text-purple-300">
                Dữ liệu DEMO
              </span>
            )}
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onReset}
            className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
          >
            ← Phân tích tin khác
          </Button>
        </div>

        <div className="mt-4">
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            Kết luận sơ bộ
          </h3>
          <p className="mt-1 text-base text-slate-700 dark:text-slate-300">{finding_vi}</p>
          {analysis.risk_score != null && <p className="mt-2 text-sm text-slate-600">Điểm chỉ dấu: {analysis.risk_score}/100. Đây là tổng trọng số của các rule đã kích hoạt, không phải xác suất lừa đảo.</p>}
        </div>
      </div>

      {/* Dấu hiệu cảnh báo với trích đoạn nguyên văn */}
      {indicators.length > 0 ? (
        <div className="rounded-xl border border-red-200 bg-red-50/50 p-5 shadow-sm dark:border-red-900/50 dark:bg-red-950/20">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-red-900 dark:text-red-300">
            Dấu hiệu cảnh báo phát hiện ({indicators.length})
          </h3>
          <ul className="mt-3 divide-y divide-red-200/60 dark:divide-red-900/40">
            {indicators.map((ind, idx) => (
              <li key={idx} className="py-2.5 first:pt-0 last:pb-0">
                <span className="inline-block rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/50 dark:text-red-200">
                  {ind.category_vi}
                </span>
                {ind.weight != null && <span className="ml-2 text-xs text-red-800">Ưu tiên: {ind.weight}</span>}
                <blockquote className="mt-1.5 border-l-2 border-red-400 pl-3 text-base italic text-slate-800 dark:border-red-700 dark:text-slate-200">
                  &ldquo;{ind.matched_quote}&rdquo;
                </blockquote>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="rounded-xl border border-slate-200 bg-white p-5 text-base text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300">
          Chưa phát hiện dấu hiệu cảnh báo trong văn bản. Điều này không chứng minh tin tuyển dụng an toàn; hãy kiểm tra nguồn và thông tin còn thiếu trước khi ứng tuyển.
        </p>
      )}

      {/* Thông tin đối chiếu nguồn & thiếu sót (Evidence Provenance) */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Căn cứ đối chiếu và nguồn xác minh
        </h3>
        <div className="mt-3 space-y-3 text-base text-slate-700 dark:text-slate-300">
          <div>
            <span className="font-semibold text-slate-900 dark:text-slate-100">Nguồn đối chiếu: </span>
            {evidence.matched_sources && evidence.matched_sources.length > 0 ? (
              <div className="mt-3"><EvidenceList sources={evidence.matched_sources} /></div>
            ) : (
              <span className="text-slate-500 italic">Chưa xác minh qua nguồn độc lập</span>
            )}
          </div>

          {evidence.missing_vi && evidence.missing_vi.length > 0 && (
            <div className="rounded-lg bg-amber-50/60 p-3 dark:bg-amber-950/20">
              <span className="font-semibold text-amber-900 dark:text-amber-300">
                Thông tin còn thiếu cần bổ sung:
              </span>
              <ul className="mt-1 list-disc pl-4 space-y-0.5 text-amber-800 dark:text-amber-200">
                {evidence.missing_vi.map((m, idx) => (
                  <li key={idx}>{m}</li>
                ))}
              </ul>
            </div>
          )}

          {evidence.limitations_vi && evidence.limitations_vi.length > 0 && (
            <div className="border-t border-slate-100 pt-2 text-sm text-slate-600 dark:text-slate-400 dark:border-slate-800">
              {evidence.limitations_vi.map((lim, idx) => (
                <p key={idx}>{lim}</p>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 11 trường thông tin trích xuất */}
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Thông tin tuyển dụng nhận diện được
        </h3>
        <dl className="mt-4 grid grid-cols-1 gap-x-4 gap-y-3 sm:grid-cols-2 text-base">
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Tên doanh nghiệp</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.company_name || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Vị trí công việc</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.job_title || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Mức lương</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.salary || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Địa điểm</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.location || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Hình thức</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.employment_type || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Email liên hệ</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.contact_email || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Điện thoại</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.contact_phone || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Website</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.recruitment_website || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Yêu cầu ứng tuyển</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.application_requirements || "Chưa có thông tin"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Yêu cầu tài chính</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.required_payments || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500 dark:text-slate-400">Chỉ dẫn đặc biệt</dt>
            <dd className="font-medium text-slate-900 dark:text-slate-100">
              {job.suspicious_instructions || "Chưa có thông tin"}
            </dd>
          </div>
        </dl>
      </div>

      {/* Hành động khuyến nghị */}
      {actions_vi.length > 0 && (
        <div className="rounded-xl border border-blue-100 bg-blue-50/40 p-5 shadow-sm dark:border-blue-900/40 dark:bg-blue-950/20">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-blue-900 dark:text-blue-300">
            Việc cần làm trước khi ứng tuyển
          </h3>
          <ul className="mt-3 list-disc space-y-1 pl-4 text-base text-slate-800 dark:text-slate-200">
            {actions_vi.map((act, idx) => (
              <li key={idx}>{act}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer: Thông tin lưu trữ phiên khách / tài khoản */}
      <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>
          {formattedExpiry
            ? `Kết quả lưu trong phiên khách đến: ${formattedExpiry}`
            : "Kết quả được lưu trong tài khoản của bạn"}
        </span>
        <span>ID phân tích: {analysis.id.slice(0, 8)}...</span>
      </div>
    </div>
  );
}
