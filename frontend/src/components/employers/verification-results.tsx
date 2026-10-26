"use client";

import React, { useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { EvidenceList } from "@/components/analysis/evidence-list";
import { VerificationField, VerificationResponse } from "@/types/api";

const labels: Record<VerificationField, string> = { company_name: "Tên công ty", tax_id: "Mã số thuế", contact_email: "Email liên hệ", recruitment_website: "Website tuyển dụng", social_channel_url: "Kênh mạng xã hội", bank_account: "Thông tin ngân hàng" };
const statusText = { matched: "Khớp căn cứ", conflicting: "Có xung đột", unverified: "Chưa đối chiếu được" };

export function VerificationResults({ result, onReset }: { result: VerificationResponse; onReset: () => void }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, [result]);
  return <section className="space-y-7 break-words" aria-label="Kết quả đối chiếu">
    <div className="border-b border-slate-200 pb-5 dark:border-slate-700">
      <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Kết quả đối chiếu nguồn</p>
      <h2 ref={heading} tabIndex={-1} className="mt-2 text-2xl font-semibold outline-none focus-visible:ring-2 focus-visible:ring-blue-600">{result.verification_label_vi}</h2>
      <p className="mt-3 text-base text-slate-700 dark:text-slate-200">{result.summary_vi}</p>
    </div>
    <div><h3 className="mb-3 text-lg font-semibold">Thông tin đã kiểm tra</h3><dl className="divide-y divide-slate-200 dark:divide-slate-700">{result.field_checks.map(check => <div key={check.field} className="py-4 first:pt-0">
      <dt className="flex flex-wrap items-center gap-2 font-medium">{labels[check.field]}<span className={`rounded border px-2 py-1 text-sm ${check.status === "conflicting" ? "border-orange-300 bg-orange-50 text-orange-900 dark:bg-orange-950 dark:text-orange-200" : "border-slate-300 text-slate-700 dark:text-slate-200"}`}>{statusText[check.status]}</span></dt>
      <dd className="mt-2 text-slate-700 dark:text-slate-200">{check.reason_vi}{check.source_ids.length > 0 && <ul className="mt-1 space-y-1">{check.source_ids.map(id => <li key={id}><a href={`#source-${id}`} className="text-blue-700 underline dark:text-blue-300">Căn cứ: {result.matched_sources.find(source => source.id === id)?.label_vi || "Nguồn đối chiếu"}</a></li>)}</ul>}</dd>
    </div>)}</dl></div>
    {result.findings_vi.length > 0 && <div><h3 className="mb-2 text-lg font-semibold">Nhận định và lý do</h3><ul className="list-disc space-y-2 pl-5">{result.findings_vi.map((finding, index) => <li key={index}>{finding}</li>)}</ul></div>}
    {result.missing_fields_vi.length > 0 && <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100"><h3 className="font-semibold">Thông tin cần bổ sung</h3><ul className="mt-2 list-disc space-y-1 pl-5">{result.missing_fields_vi.map((field, index) => <li key={index}>{field}</li>)}</ul></div>}
    <div><h3 className="mb-3 text-lg font-semibold">Nguồn và căn cứ đối chiếu</h3><EvidenceList sources={result.matched_sources} /></div>
    <div><h3 className="mb-2 text-lg font-semibold">Việc cần làm tiếp</h3><ul className="list-disc space-y-2 pl-5">{result.recommended_actions_vi.map((action, index) => <li key={index}>{action}</li>)}</ul></div>
    <div className="rounded-lg bg-slate-100 p-4 text-slate-700 dark:bg-slate-800 dark:text-slate-200"><h3 className="font-semibold">Giới hạn của kết quả</h3>{result.limitations_vi.map((limit, index) => <p key={index} className="mt-2">{limit}</p>)}</div>
    <Button type="button" onClick={onReset} className="min-h-11" variant="outline">Kiểm tra thông tin khác</Button>
    <p className="text-sm text-slate-600 dark:text-slate-300">Kiểm tra lúc {new Date(result.checked_at).toLocaleString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })} (giờ Việt Nam). Kết quả tra cứu không được lưu thành lịch sử.</p>
  </section>;
}
