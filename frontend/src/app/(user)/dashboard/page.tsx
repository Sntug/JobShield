"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { RiskStatistics } from "@/components/dashboard/risk-statistics";
import { useAuth } from "@/hooks/use-auth";
import { getUserStats } from "@/lib/api-client";
import { UserStats } from "@/types/api";

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
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Xin chào, {user?.full_name}
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Theo dõi các tin tuyển dụng đã đánh giá và quản lý dấu hiệu rủi ro.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <Link
          href="/analyze"
          className="rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 transition-colors"
        >
          Phân tích tin mới
        </Link>
        <Link
          href="/history"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Xem lịch sử
        </Link>
        <Link
          href="/saved"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
        >
          Tin đã lưu
        </Link>
      </div>

      {loading ? (
        <div className="py-12 text-center text-sm text-slate-500">
          Đang tải thống kê dữ liệu...
        </div>
      ) : error ? (
        <div role="alert" className="p-4 rounded-xl border border-rose-200 bg-rose-50 text-rose-800 text-sm">
          {error}
        </div>
      ) : stats ? (
        <RiskStatistics stats={stats} />
      ) : null}
    </div>
  );
}
