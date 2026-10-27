"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { listSavedAnalyses, unsaveAnalysis } from "@/lib/api-client";
import { SavedAnalysisItem } from "@/types/api";

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
        return "bg-rose-100 text-rose-800 border-rose-200";
      case "Ít dấu hiệu rủi ro":
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
      default:
        return "bg-amber-100 text-amber-800 border-amber-200";
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Tin đã lưu ({total})
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Các tin tuyển dụng bạn đã đánh dấu để theo dõi hoặc đối chiếu lại.
        </p>
      </div>

      {loading ? (
        <div className="py-16 text-center text-sm text-slate-500">
          Đang tải danh sách bài đã lưu...
        </div>
      ) : error ? (
        <div role="alert" className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-sm">
          {error}
        </div>
      ) : savedItems.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-12 text-center">
          <p className="text-base font-medium text-slate-900">
            Chưa có tin tuyển dụng nào được lưu
          </p>
          <p className="mt-1 text-sm text-slate-500">
            Trong lịch sử hoặc kết quả phân tích, nhấn &quot;Lưu&quot; để lưu lại những tin bạn muốn theo dõi.
          </p>
          <div className="mt-6">
            <Link
              href="/history"
              className="inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              Xem lịch sử phân tích
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm">
            {savedItems.map((item) => (
              <div
                key={item.analysis_id}
                className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-slate-50 transition-colors"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-3">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold border ${getRiskBadgeColor(
                        item.analysis.risk_label_vi
                      )}`}
                    >
                      {item.analysis.risk_label_vi}
                    </span>
                    <span className="text-xs text-slate-500">
                      Đã lưu lúc:{" "}
                      {new Date(item.saved_at).toLocaleDateString("vi-VN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <h2 className="text-base font-semibold text-slate-900">
                    {item.analysis.job.job_title || "Tin tuyển dụng"}
                  </h2>
                  <p className="text-sm text-slate-600 line-clamp-1">
                    {item.analysis.job.company_name
                      ? `Công ty: ${item.analysis.job.company_name} — `
                      : ""}
                    {item.analysis.finding_vi}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Link
                    href={`/analyze?id=${item.analysis_id}`}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                  >
                    Xem chi tiết
                  </Link>
                  <Button
                    type="button"
                    onClick={() => handleUnsave(item.analysis_id)}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100"
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
                className="border border-slate-300 bg-white text-slate-700 disabled:opacity-40"
              >
                Trang trước
              </Button>
              <span className="text-sm text-slate-600">
                Trang {page} / {totalPages}
              </span>
              <Button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="border border-slate-300 bg-white text-slate-700 disabled:opacity-40"
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
