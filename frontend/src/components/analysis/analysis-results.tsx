"use client";

import React, { useState } from "react";
import Link from "next/link";
import { AnalysisResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { EvidenceList } from "@/components/analysis/evidence-list";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Building2,
  Copy,
  Check,
  Sparkles,
  CheckSquare2,
  FileText,
  BadgeAlert,
} from "lucide-react";

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

  const [copied, setCopied] = useState(false);

  const isHighRisk = risk_label_vi === "Rủi ro cao";
  const isLowRisk = risk_label_vi === "Ít dấu hiệu rủi ro";

  const getRiskBadgeColor = (risk: string) => {
    switch (risk) {
      case "Rủi ro cao":
        return "bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800";
      case "Ít dấu hiệu rủi ro":
        return "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800";
      default:
        return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800";
    }
  };

  const getVerificationBadgeColor = (verif: string) => {
    switch (verif) {
      case "Khớp nguồn đã xác minh":
        return "bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800";
      case "Thông tin xung đột":
        return "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-950/60 dark:text-orange-300 dark:border-orange-800";
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

  const handleCopySummary = async () => {
    const summaryText = `[Cảnh báo an toàn JobShield]\n• Mức độ rủi ro: ${risk_label_vi}\n• Xác minh pháp nhân: ${verification_label_vi}\n• Kết luận: ${finding_vi}\n${
      analysis.risk_score != null ? `• Điểm chỉ dấu: ${analysis.risk_score}/100\n` : ""
    }${
      indicators.length > 0
        ? `• Dấu hiệu phát hiện:\n${indicators
            .map((i) => `  - ${i.category_vi}: "${i.matched_quote}"`)
            .join("\n")}\n`
        : ""
    }${
      actions_vi.length > 0
        ? `• Khuyến nghị hành động:\n${actions_vi.map((a) => `  - ${a}`).join("\n")}\n`
        : ""
    }Nguồn kiểm tra: JobShield - Hệ thống phân tích tin tuyển dụng`;

    try {
      await navigator.clipboard.writeText(summaryText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // ignore
    }
  };

  return (
    <div className="w-full space-y-6 break-words">
      {/* Top Banner: Status, Badges & Hero Risk Meter */}
      <div
        className={`rounded-2xl border p-6 shadow-sm transition-all ${
          isHighRisk
            ? "border-rose-200 bg-rose-50/40 dark:border-rose-900/40 dark:bg-rose-950/20"
            : isLowRisk
            ? "border-emerald-200 bg-emerald-50/40 dark:border-emerald-900/40 dark:bg-emerald-950/20"
            : "border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
        }`}
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 pb-4 dark:border-slate-800">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${getRiskBadgeColor(
                risk_label_vi
              )}`}
            >
              {isHighRisk ? (
                <ShieldAlert className="size-3.5" />
              ) : isLowRisk ? (
                <ShieldCheck className="size-3.5" />
              ) : (
                <AlertTriangle className="size-3.5" />
              )}
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

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopySummary}
              className="text-xs font-medium gap-1.5"
            >
              {copied ? (
                <>
                  <Check className="size-3.5 text-emerald-600" />
                  <span className="text-emerald-700 font-semibold">Đã sao chép!</span>
                </>
              ) : (
                <>
                  <Copy className="size-3.5" />
                  <span>Sao chép tóm tắt</span>
                </>
              )}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={onReset}
              className="text-xs text-sky-600 hover:text-sky-700 hover:bg-sky-50 dark:text-sky-400 dark:hover:bg-sky-950/50 font-medium"
            >
              ← Phân tích tin khác
            </Button>
          </div>
        </div>

        <div className="mt-5">
          <div className="flex items-start gap-3">
            <div
              className={`flex size-10 shrink-0 items-center justify-center rounded-xl shadow-sm ${
                isHighRisk
                  ? "bg-rose-600 text-white shadow-rose-600/30"
                  : isLowRisk
                  ? "bg-emerald-600 text-white shadow-emerald-600/30"
                  : "bg-amber-600 text-white shadow-amber-600/30"
              }`}
            >
              {isHighRisk ? (
                <ShieldAlert className="size-5" />
              ) : isLowRisk ? (
                <ShieldCheck className="size-5" />
              ) : (
                <AlertTriangle className="size-5" />
              )}
            </div>
            <div className="flex-1">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Kết luận sơ bộ
              </h3>
              <p className="mt-1 text-base leading-relaxed text-slate-700 dark:text-slate-300 font-medium">
                {finding_vi}
              </p>
              {analysis.risk_score != null && (
                <div className="mt-3 flex items-center gap-3">
                  <div className="h-2 w-36 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
                    <div
                      className={`h-full ${
                        analysis.risk_score >= 60
                          ? "bg-rose-500"
                          : analysis.risk_score >= 30
                          ? "bg-amber-500"
                          : "bg-emerald-500"
                      }`}
                      style={{ width: `${Math.min(100, analysis.risk_score)}%` }}
                    />
                  </div>
                  <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    Điểm chỉ dấu: {analysis.risk_score}/100. Đây là tổng trọng số của các rule đã kích hoạt, không phải xác suất lừa đảo.
                  </p>
                </div>
              )}
            </div>
          </div>

          {job.company_name && (
            <div className="mt-4 pt-3 border-t border-slate-200/60 dark:border-slate-800 flex items-center justify-between text-xs">
              <span className="text-slate-600 dark:text-slate-400">
                Doanh nghiệp trong bài: <strong className="text-slate-900 dark:text-slate-100">{job.company_name}</strong>
              </span>
              <Link
                href={`/verify-employer?company=${encodeURIComponent(job.company_name)}`}
                className="inline-flex items-center gap-1 font-semibold text-sky-600 hover:underline dark:text-sky-400"
              >
                <Building2 className="size-3.5" />
                <span>Xác minh nhà tuyển dụng này →</span>
              </Link>
            </div>
          )}
        </div>
      </div>

      {/* Dấu hiệu cảnh báo với trích đoạn nguyên văn */}
      {indicators.length > 0 ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50/40 p-6 shadow-sm dark:border-rose-900/50 dark:bg-rose-950/20">
          <h3 className="text-sm font-bold uppercase tracking-wider text-rose-900 dark:text-rose-300 flex items-center gap-2">
            <BadgeAlert className="size-4 text-rose-600" />
            <span>Dấu hiệu cảnh báo phát hiện ({indicators.length})</span>
          </h3>
          <ul className="mt-4 divide-y divide-rose-200/60 dark:divide-rose-900/40">
            {indicators.map((ind, idx) => (
              <li key={idx} className="py-3 first:pt-0 last:pb-0">
                <div className="flex items-center gap-2">
                  <span className="inline-block rounded-md bg-rose-100 px-2.5 py-0.5 text-xs font-semibold text-rose-800 dark:bg-rose-900/60 dark:text-rose-200">
                    {ind.category_vi}
                  </span>
                  {ind.weight != null && (
                    <span className="text-xs font-medium text-rose-700 dark:text-rose-300">
                      Ưu tiên: {ind.weight}
                    </span>
                  )}
                </div>
                <blockquote className="mt-2 rounded-r-lg border-l-4 border-rose-500 bg-white/60 p-2.5 pl-3 text-base italic text-slate-800 dark:border-rose-600 dark:bg-slate-900/60 dark:text-slate-200">
                  &ldquo;{ind.matched_quote}&rdquo;
                </blockquote>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-base text-slate-700 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 leading-relaxed shadow-sm">
          Chưa phát hiện dấu hiệu cảnh báo trong văn bản. Điều này không chứng minh tin tuyển dụng an toàn; hãy kiểm tra nguồn và thông tin còn thiếu trước khi ứng tuyển.
        </div>
      )}

      {/* Phân tích ngữ nghĩa chuyên sâu bằng AI (Layer 2) */}
      {analysis.ai_insights && (
        <div
          data-testid="ai-insights-card"
          className="rounded-2xl border border-indigo-200 bg-indigo-50/40 p-6 shadow-sm dark:border-indigo-900/40 dark:bg-indigo-950/20 space-y-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-indigo-100 pb-3 dark:border-indigo-900/50">
            <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-900 dark:text-indigo-300 flex items-center gap-2">
              <Sparkles className="size-4 text-indigo-600" />
              <span>Phân tích ngữ nghĩa AI</span>
              {analysis.ai_insights.provider && analysis.ai_insights.provider !== "none" && (
                <span className="text-xs font-normal lowercase text-indigo-700 dark:text-indigo-400">
                  ({analysis.ai_insights.provider}
                  {analysis.ai_insights.model ? `/${analysis.ai_insights.model}` : ""})
                </span>
              )}
            </h3>
            <span
              className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${
                analysis.ai_insights.status === "success"
                  ? "bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-900/60 dark:text-indigo-200 dark:border-indigo-800"
                  : "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/60 dark:text-amber-200 dark:border-amber-800"
              }`}
            >
              {analysis.ai_insights.status === "success"
                ? "AI Hoạt động"
                : analysis.ai_insights.status === "fallback_no_consent"
                ? "Chưa cấp quyền AI (Quy tắc chuẩn)"
                : "Dùng quy tắc chuẩn (Fallback)"}
            </span>
          </div>

          {analysis.ai_insights.status === "success" ? (
            <div className="space-y-4 text-base text-slate-800 dark:text-slate-200">
              {analysis.ai_insights.semantic_summary_vi && (
                <div>
                  <h4 className="text-xs font-bold uppercase text-indigo-900 dark:text-indigo-300">
                    Nhận định ngữ cảnh
                  </h4>
                  <p className="mt-1 leading-relaxed text-slate-700 dark:text-slate-300 font-medium">
                    {analysis.ai_insights.semantic_summary_vi}
                  </p>
                </div>
              )}

              {analysis.ai_insights.suspicious_patterns_vi &&
                analysis.ai_insights.suspicious_patterns_vi.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase text-indigo-900 dark:text-indigo-300">
                      Mẫu bất thường phát hiện từ ngữ cảnh ({analysis.ai_insights.suspicious_patterns_vi.length})
                    </h4>
                    <ul className="mt-2 list-disc pl-5 space-y-1 text-slate-700 dark:text-slate-300">
                      {analysis.ai_insights.suspicious_patterns_vi.map((pat, idx) => (
                        <li key={idx}>{pat}</li>
                      ))}
                    </ul>
                  </div>
                )}

              {analysis.ai_insights.reasoning_vi && (
                <div>
                  <h4 className="text-xs font-bold uppercase text-indigo-900 dark:text-indigo-300">
                    Lập luận giải thích rủi ro
                  </h4>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                    {analysis.ai_insights.reasoning_vi}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-slate-600 dark:text-slate-400 space-y-1">
              <p>
                Hệ thống đang bảo vệ và phân tích bằng bộ quy tắc chuẩn đã kiểm chứng (Rule-Based Engine).
              </p>
            </div>
          )}

          {analysis.ai_insights.limitations_vi && analysis.ai_insights.limitations_vi.length > 0 && (
            <div className="border-t border-indigo-100/80 pt-3 text-xs text-slate-500 dark:text-slate-400 dark:border-indigo-900/40">
              {analysis.ai_insights.limitations_vi.map((lim, idx) => (
                <p key={idx}>{lim}</p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Thông tin đối chiếu nguồn & thiếu sót (Evidence Provenance) */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <Building2 className="size-4 text-sky-600" />
          <span>Căn cứ đối chiếu và nguồn xác minh</span>
        </h3>
        <div className="mt-4 space-y-4 text-base text-slate-700 dark:text-slate-300">
          <div>
            <span className="font-semibold text-slate-900 dark:text-slate-100">Nguồn đối chiếu: </span>
            {evidence.matched_sources && evidence.matched_sources.length > 0 ? (
              <div className="mt-3">
                <EvidenceList sources={evidence.matched_sources} />
              </div>
            ) : (
              <span className="text-slate-500 italic">Chưa xác minh qua nguồn độc lập</span>
            )}
          </div>

          {evidence.missing_vi && evidence.missing_vi.length > 0 && (
            <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4 dark:border-amber-900/40 dark:bg-amber-950/30">
              <span className="font-bold text-amber-900 dark:text-amber-300 flex items-center gap-1.5">
                <AlertTriangle className="size-4 text-amber-600" />
                Thông tin còn thiếu cần bổ sung:
              </span>
              <ul className="mt-2 list-disc pl-5 space-y-1 text-sm text-amber-900 dark:text-amber-200">
                {evidence.missing_vi.map((m, idx) => (
                  <li key={idx}>{m}</li>
                ))}
              </ul>
            </div>
          )}

          {evidence.limitations_vi && evidence.limitations_vi.length > 0 && (
            <div className="border-t border-slate-100 pt-3 text-xs text-slate-500 dark:text-slate-400 dark:border-slate-800 space-y-1">
              {evidence.limitations_vi.map((lim, idx) => (
                <p key={idx}>* {lim}</p>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 11 trường thông tin trích xuất */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <FileText className="size-4 text-slate-600" />
          <span>Thông tin tuyển dụng nhận diện được</span>
        </h3>
        <dl className="mt-5 grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2 text-sm">
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Tên doanh nghiệp</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.company_name || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Vị trí công việc</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.job_title || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Mức lương</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.salary || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Địa điểm</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.location || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Hình thức</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.employment_type || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Email liên hệ</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.contact_email || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Điện thoại</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.contact_phone || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Website</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.recruitment_website || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60 sm:col-span-2">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Yêu cầu ứng tuyển</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.application_requirements || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Yêu cầu tài chính</dt>
            <dd className={`mt-1 font-semibold ${job.required_payments ? "text-rose-600 dark:text-rose-400" : "text-slate-900 dark:text-slate-100"}`}>
              {job.required_payments || "Chưa có thông tin"}
            </dd>
          </div>
          <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
            <dt className="text-xs font-medium text-slate-500 dark:text-slate-400">Chỉ dẫn đặc biệt</dt>
            <dd className="mt-1 font-semibold text-slate-900 dark:text-slate-100">
              {job.suspicious_instructions || "Chưa có thông tin"}
            </dd>
          </div>
        </dl>
      </div>

      {/* Hành động khuyến nghị */}
      {actions_vi.length > 0 && (
        <div className="rounded-2xl border border-sky-200 bg-sky-50/50 p-6 shadow-sm dark:border-sky-900/40 dark:bg-sky-950/20">
          <h3 className="text-sm font-bold uppercase tracking-wider text-sky-900 dark:text-sky-300 flex items-center gap-2">
            <CheckSquare2 className="size-4 text-sky-600" />
            <span>Việc cần làm trước khi ứng tuyển</span>
          </h3>
          <ul className="mt-4 space-y-2.5 text-base text-slate-800 dark:text-slate-200">
            {actions_vi.map((act, idx) => (
              <li key={idx} className="flex items-start gap-2.5">
                <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-sky-200 text-xs font-bold text-sky-800 dark:bg-sky-900 dark:text-sky-300">
                  {idx + 1}
                </span>
                <span className="font-medium">{act}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer: Thông tin lưu trữ phiên khách / tài khoản */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
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
