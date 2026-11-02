"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { listSavedAnalyses, unsaveAnalysis } from "@/lib/api-client";
import { SavedAnalysisItem } from "@/types/api";
import { Bookmark } from "lucide-react";

export default function SavedPage() {
  const [savedItems, setSavedItems] = useState<SavedAnalysisItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let ignore = false;
    void Promise.resolve().then(async () => {
      try {
        if (!ignore) {
          setLoading(true);
          setError(null);
        }
        const data = await listSavedAnalyses(page, pageSize);
        if (!ignore) {
          setSavedItems(data.items);
          setTotal(data.total);
        }
      } catch (err: unknown) {
        if (!ignore) {
          const e = err as { message?: string };
          setError(e.message || "Không thể tải danh sách bài đã lưu.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    });

    return () => {
      ignore = true;
    };
  }, [page, pageSize]);

  const handleUnsave = async (analysisId: string) => {
    try {
      await unsaveAnalysis(analysisId);
      const data = await listSavedAnalyses(page, pageSize);
      setTotal(data.total);
      const lastPage = Math.max(1, Math.ceil(data.total / pageSize));
      if (page > lastPage) {
        setLoading(true);
        setPage(lastPage);
      } else {
        setSavedItems(data.items);
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      alert(e.message || "Lỗi bỏ lưu bài.");
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-950 dark:text-white">
          Tin đã lưu ({total})
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
          Các tin tuyển dụng bạn đã đánh dấu để theo dõi hoặc đối chiếu lại.
        </p>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white py-16 text-center text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          Đang tải danh sách bài đã lưu...
        </div>
      ) : error ? (
        <div role="alert" className="p-5 rounded-2xl border border-rose-200 bg-rose-50 text-rose-800 text-sm dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </div>
      ) : savedItems.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center dark:border-slate-800 dark:bg-slate-900">
          <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-sky-50 text-sky-600 dark:bg-sky-950 dark:text-sky-300">
            <Bookmark className="size-6" />
          </div>
          <p className="mt-4 text-base font-bold text-slate-900 dark:text-slate-100">
            Chưa có tin tuyển dụng nào được lưu
          </p>
          <p className="mt-1 text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
            Trong lịch sử hoặc kết quả phân tích, nhấn &quot;Lưu&quot; để lưu lại những tin bạn muốn theo dõi.
          </p>
          <div className="mt-6">
            <Link
              href="/history"
              className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-xs sm:text-sm font-semibold text-white hover:bg-slate-800 transition-colors"
            >
              Xem lịch sử phân tích
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="divide-y divide-slate-100 rounded-2xl border border-slate-200/90 bg-white overflow-hidden shadow-sm dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900">
            {savedItems.map((item) => (
              <div
                key={item.analysis_id}
                className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50/80 transition-colors dark:hover:bg-slate-800/50"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getRiskBadgeColor(
                        item.analysis.risk_label_vi
                      )}`}
                    >
                      {item.analysis.risk_label_vi}
                    </span>
                    <span className="text-xs text-slate-400">
                      Đã lưu lúc:{" "}
                      {new Date(item.saved_at).toLocaleDateString("vi-VN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                    {item.analysis.job.job_title || "Tin tuyển dụng"}
                  </h2>
                  <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 line-clamp-1">
                    {item.analysis.job.company_name
                      ? `Công ty: ${item.analysis.job.company_name} — `
                      : ""}
                    {item.analysis.finding_vi}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    href={`/analyze?id=${item.analysis_id}`}
                    className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 shadow-sm"
                  >
                    <span>Xem chi tiết</span>
                  </Link>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleUnsave(item.analysis_id)}
                    className="rounded-lg text-xs font-medium"
                  >
                    Bỏ lưu
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <Button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="border border-slate-300 bg-white text-slate-700 disabled:opacity-40 text-xs"
              >
                Trang trước
              </Button>
              <span className="text-xs font-medium text-slate-500">
                Trang {page} / {totalPages}
              </span>
              <Button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="border border-slate-300 bg-white text-slate-700 disabled:opacity-40 text-xs"
              >
                Trang sau
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
