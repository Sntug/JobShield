"use client";

import React, { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { EvidenceList } from "@/components/analysis/evidence-list";
import { VerificationField, VerificationResponse } from "@/types/api";
import { AlertTriangle, ShieldCheck } from "lucide-react";

const labels: Record<VerificationField, string> = {
  company_name: "Tên công ty",
  tax_id: "Mã số thuế",
  contact_email: "Email liên hệ",
  recruitment_website: "Website tuyển dụng",
  social_channel_url: "Kênh mạng xã hội",
  bank_account: "Thông tin ngân hàng",
};

const statusText = {
  matched: "Khớp căn cứ",
  conflicting: "Có xung đột",
  unverified: "Chưa đối chiếu được",
};

export function VerificationResults({
  result,
  onReset,
}: {
  result: VerificationResponse;
  onReset: () => void;
}) {
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    heading.current?.focus();
  }, [result]);

  return (
    <section className="space-y-6 break-words" aria-label="Kết quả đối chiếu">
      {/* Top Banner Card */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4 dark:border-slate-800">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Kết quả đối chiếu nguồn
            </p>
            <h2
              ref={heading}
              tabIndex={-1}
              className="mt-1 text-2xl font-bold tracking-tight text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-sky-600 dark:text-slate-100"
            >
              {result.verification_label_vi}
            </h2>
          </div>
          <Button
            type="button"
            onClick={onReset}
            variant="outline"
            size="sm"
            className="text-xs font-medium"
          >
            ← Kiểm tra thông tin khác
          </Button>
        </div>
        <p className="mt-4 text-base leading-relaxed text-slate-700 dark:text-slate-200">
          {result.summary_vi}
        </p>
      </div>

      {/* Field Checks */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Thông tin đã kiểm tra
        </h3>
        <dl className="divide-y divide-slate-100 dark:divide-slate-800">
          {result.field_checks.map((check) => (
            <div key={check.field} className="py-4 first:pt-0 last:pb-0">
              <dt className="flex flex-wrap items-center gap-2 font-semibold text-slate-900 dark:text-slate-100 text-sm">
                <span>{labels[check.field]}</span>
                <span
                  className={`inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold ${
                    check.status === "conflicting"
                      ? "border-orange-300 bg-orange-50 text-orange-900 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-200"
                      : check.status === "matched"
                      ? "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200"
                      : "border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                  }`}
                >
                  {statusText[check.status]}
                </span>
              </dt>
              <dd className="mt-2 text-sm text-slate-700 dark:text-slate-200">
                <p>{check.reason_vi}</p>
                {check.source_ids.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {check.source_ids.map((id) => (
                      <li key={id}>
                        <a
                          href={`#source-${id}`}
                          className="text-xs text-sky-600 underline hover:text-sky-800 dark:text-sky-400"
                        >
                          Căn cứ: {result.matched_sources.find((source) => source.id === id)?.label_vi || "Nguồn đối chiếu"}
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      {/* Findings */}
      {result.findings_vi.length > 0 && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Nhận định và lý do
          </h3>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700 dark:text-slate-200">
            {result.findings_vi.map((finding, index) => (
              <li key={index}>{finding}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Missing Fields */}
      {result.missing_fields_vi.length > 0 && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/70 p-6 text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
          <h3 className="font-bold flex items-center gap-1.5 text-sm uppercase tracking-wider text-amber-900 dark:text-amber-300">
            <AlertTriangle className="size-4 text-amber-600" />
            <span>Thông tin cần bổ sung</span>
          </h3>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm">
            {result.missing_fields_vi.map((field, index) => (
              <li key={index}>{field}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Matched Sources */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <ShieldCheck className="size-4 text-sky-600" />
          <span>Nguồn và căn cứ đối chiếu</span>
        </h3>
        <EvidenceList sources={result.matched_sources} />
      </div>

      {/* Recommended Actions */}
      <div className="rounded-2xl border border-sky-100 bg-sky-50/50 p-6 shadow-sm dark:border-sky-900/40 dark:bg-sky-950/20">
        <h3 className="mb-3 text-sm font-bold uppercase tracking-wider text-sky-900 dark:text-sky-300">
          Việc cần làm tiếp
        </h3>
        <ul className="list-disc space-y-2 pl-5 text-sm text-slate-800 dark:text-slate-200">
          {result.recommended_actions_vi.map((action, index) => (
            <li key={index}>{action}</li>
          ))}
        </ul>
      </div>

      {/* Limitations */}
      <div className="rounded-2xl bg-slate-100/80 p-5 text-slate-700 dark:bg-slate-800/60 dark:text-slate-200 text-xs leading-relaxed space-y-2">
        <h3 className="font-bold uppercase tracking-wider text-slate-800 dark:text-slate-100">
          Giới hạn của kết quả
        </h3>
        {result.limitations_vi.map((limit, index) => (
          <p key={index}>* {limit}</p>
        ))}
      </div>

      <div className="pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <Button
          type="button"
          onClick={onReset}
          className="min-h-11 px-6 font-semibold"
          variant="outline"
        >
          Kiểm tra thông tin khác
        </Button>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Kiểm tra lúc {new Date(result.checked_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })} (giờ Việt Nam). Kết quả tra cứu không được lưu thành lịch sử.
        </p>
      </div>
    </section>
  );
}
