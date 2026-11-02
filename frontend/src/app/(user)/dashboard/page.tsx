"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { RiskStatistics } from "@/components/dashboard/risk-statistics";
import { useAuth } from "@/hooks/use-auth";
import { getUserStats } from "@/lib/api-client";
import { UserStats } from "@/types/api";
import { Sparkles, History, Bookmark } from "lucide-react";

export default function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getUserStats()
      .then((data) => {
        if (active) setStats(data);
      })
      .catch((err) => {
        if (active) setError(err.message || "Không thể tải thống kê.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-8">
      {/* Welcome Card */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-950 dark:text-white sm:text-3xl">
            Xin chào, {user?.full_name}
          </h1>
          <p className="mt-1.5 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
            Theo dõi các tin tuyển dụng đã đánh giá và quản lý dấu hiệu rủi ro.
          </p>
        </div>

        <div className="flex flex-wrap gap-2.5">
          <Link
            href="/analyze"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-sky-600 to-blue-700 px-4 py-2.5 text-xs sm:text-sm font-semibold text-white shadow-md shadow-sky-600/20 transition-all hover:from-sky-500 hover:to-blue-600"
          >
            <Sparkles className="size-4" />
            <span>Phân tích tin mới</span>
          </Link>
          <Link
            href="/history"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs sm:text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300"
          >
            <History className="size-4" />
            <span>Xem lịch sử</span>
          </Link>
          <Link
            href="/saved"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs sm:text-sm font-semibold text-slate-700 shadow-sm transition-all hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300"
          >
            <Bookmark className="size-4" />
            <span>Tin đã lưu</span>
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-slate-200 bg-white py-16 text-center text-sm text-slate-500 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          Đang tải thống kê dữ liệu...
        </div>
      ) : error ? (
        <div role="alert" className="p-5 rounded-2xl border border-rose-200 bg-rose-50 text-rose-800 text-sm dark:border-rose-900/50 dark:bg-rose-950/40 dark:text-rose-200">
          {error}
        </div>
      ) : stats ? (
        <RiskStatistics stats={stats} />
      ) : null}
    </div>
  );
}
