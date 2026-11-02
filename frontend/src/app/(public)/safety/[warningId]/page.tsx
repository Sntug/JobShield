"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { usePublicWarning } from "@/hooks/use-admin";
import { ArrowLeft, ExternalLink } from "lucide-react";

export default function WarningDetailPage() {
  const { warningId } = useParams<{ warningId: string }>();
  const query = usePublicWarning(warningId);
  const warning = query.data;

  return (
    <main className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6">
      <Link
        href="/safety"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-800 dark:text-sky-400 transition-colors"
      >
        <ArrowLeft className="size-3.5" />
        <span>Danh sách cảnh báo</span>
      </Link>

      {query.isLoading && (
        <div className="rounded-2xl border border-slate-200 bg-white py-12 text-center text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          Đang tải cảnh báo...
        </div>
      )}

      {query.isError && (
        <div
          role="alert"
          className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200"
        >
          {query.error.message}
        </div>
      )}

      {warning && (
        <article className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900 space-y-6">
          <div className="border-b border-slate-100 pb-5 dark:border-slate-800 space-y-2">
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-rose-50 border border-rose-200 px-2.5 py-0.5 text-xs font-bold text-rose-800 dark:border-rose-900/50 dark:bg-rose-950/60 dark:text-rose-300">
                Phiên bản {warning.revision}
              </span>
              <span className="text-xs text-slate-400">
                {new Date(warning.published_at || warning.created_at).toLocaleDateString("vi-VN")}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              {warning.title_vi}
            </h1>
          </div>

          {warning.status === "withdrawn" ? (
            <div
              role="status"
              className="rounded-xl border border-slate-200 bg-slate-50 p-5 dark:border-slate-700 dark:bg-slate-800 space-y-2"
            >
              <h2 className="font-bold text-slate-800 dark:text-slate-100 text-base">
                Cảnh báo đã được thu hồi
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-300">
                {warning.withdrawal_reason_vi}
              </p>
              {warning.withdrawn_at && (
                <p className="text-xs text-slate-400">
                  Thời điểm: {new Date(warning.withdrawn_at).toLocaleString("vi-VN")}
                </p>
              )}
            </div>
          ) : warning.status === "superseded" ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/40 dark:text-amber-200">
              Cảnh báo này đã có bản đính chính.
            </div>
          ) : (
            <div className="space-y-6">
              <p className="text-base text-slate-700 dark:text-slate-300 leading-relaxed whitespace-pre-wrap">
                {warning.public_summary_vi}
              </p>

              {warning.public_sources_snapshot && warning.public_sources_snapshot.length > 0 && (
                <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                    Căn cứ và nguồn xác minh:
                  </h3>
                  <ul className="space-y-2 text-sm">
                    {warning.public_sources_snapshot.map((source, index) => (
                      <li key={index} className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                        <span className="text-sky-500 font-bold">•</span>
                        <a
                          href={String(source.url)}
                          className="inline-flex items-center gap-1 text-sky-600 underline hover:text-sky-800 dark:text-sky-400 font-medium"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <span>{String(source.label_vi || "Mở nguồn")}</span>
                          <ExternalLink className="size-3.5 shrink-0" />
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {warning.next_warning_id && (
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
              <Link
                href={`/safety/${warning.next_warning_id}`}
                className="inline-flex items-center gap-1.5 text-sm font-semibold text-sky-600 hover:text-sky-800 dark:text-sky-400"
              >
                <span>Xem bản đính chính tiếp theo →</span>
              </Link>
            </div>
          )}
        </article>
      )}
    </main>
  );
}
