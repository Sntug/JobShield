import React from "react";
import { MatchedSource } from "@/types/api";

export function EvidenceList({ sources }: { sources: MatchedSource[] }) {
  if (!sources.length) return <p className="text-slate-600 dark:text-slate-300">Chưa có nguồn độc lập đủ căn cứ đối chiếu.</p>;
  return <ul className="space-y-4">{sources.map((source, index) => {
    const label = source.label_vi || "Nguồn đối chiếu";
    let href: string | null = null;
    try {
      const url = new URL(source.url || "");
      if (["http:", "https:"].includes(url.protocol) && !url.username && !url.password) href = url.href;
    } catch { /* Missing source URLs remain readable without a link. */ }
    const date = source.verified_at ? new Date(source.verified_at) : null;
    return <li key={source.id || index} id={`source-${source.id || index}`} className="scroll-mt-6 break-words rounded-lg border border-slate-200 p-4 dark:border-slate-700">
      <p className="font-medium">{label} {source.is_demo && <span className="ml-2 text-sm text-purple-800 dark:text-purple-300">Nguồn DEMO</span>}</p>
      {href && <a href={href} target="_blank" rel="noopener noreferrer" aria-label={`Mở nguồn: ${label}`} className="mt-1 block break-all text-blue-700 underline dark:text-blue-300">{source.url}</a>}
      <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{date && !Number.isNaN(date.valueOf()) ? <>Kiểm chứng nguồn: <time dateTime={source.verified_at}>{date.toLocaleDateString("vi-VN", { timeZone: "Asia/Ho_Chi_Minh" })}</time></> : "Chưa có ngày xác minh"}{source.source_revision && <> · Phiên bản nguồn: {source.source_revision}</>}</p>
      {source.evidence_excerpt_vi && <blockquote className="mt-3 border-l-2 border-slate-300 pl-3 text-slate-700 dark:text-slate-200">{source.evidence_excerpt_vi}</blockquote>}
    </li>;
  })}</ul>;
}
