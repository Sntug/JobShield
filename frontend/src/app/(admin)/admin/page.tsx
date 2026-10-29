"use client";

import React from "react";
import Link from "next/link";
import { useAdminStats } from "@/hooks/use-admin";

export default function AdminDashboardPage() {
  const { data: stats, isLoading, isError, error } = useAdminStats();

  if (isLoading) {
    return <div className="py-24 text-center text-sm text-slate-500">Đang tải số liệu thống kê...</div>;
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-8">
        <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          {error instanceof Error ? error.message : "Không thể tải số liệu thống kê."}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Bảng điều khiển Quản trị</h1>
        <p className="mt-1 text-sm text-slate-600">
          Tổng quan số liệu vận hành hệ thống, tình trạng kiểm duyệt và các chỉ dấu rủi ro.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase text-slate-500">Tổng số phân tích</p>
          <p className="mt-2 text-3xl font-extrabold text-slate-900">{stats?.total_analyses ?? 0}</p>
          <p className="mt-1 text-xs text-slate-500">Tin tuyển dụng đã được quét</p>
        </div>

        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase text-amber-700">Báo cáo chờ duyệt</p>
          <p className="mt-2 text-3xl font-extrabold text-amber-900">{stats?.pending_reports ?? 0}</p>
          <div className="mt-1 flex items-center justify-between">
            <span className="text-xs text-amber-700">Tổng: {stats?.total_reports ?? 0}</span>
            <Link
              href="/admin/reports"
              className="text-xs font-bold text-amber-800 underline hover:text-amber-950"
            >
              Vào hàng đợi →
            </Link>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase text-slate-500">Kho nhà tuyển dụng</p>
          <p className="mt-2 text-3xl font-extrabold text-slate-900">{stats?.total_verified_employers ?? 0}</p>
          <div className="mt-1 flex items-center justify-between">
            <span className="text-xs text-slate-500">Hồ sơ đã quản trị</span>
            <Link
              href="/admin/employers"
              className="text-xs font-bold text-slate-700 underline hover:text-slate-900"
            >
              Quản lý →
            </Link>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase text-slate-500">Cảnh báo công khai</p>
          <p className="mt-2 text-3xl font-extrabold text-slate-900">{stats?.active_warnings ?? 0}</p>
          <div className="mt-1 flex items-center justify-between">
            <span className="text-xs text-slate-500">Tổng xuất bản: {stats?.total_warnings ?? 0}</span>
            <Link
              href="/admin/warnings"
              className="text-xs font-bold text-slate-700 underline hover:text-slate-900"
            >
              Quản lý →
            </Link>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Phân bố mức độ rủi ro (Analyses)</h2>
          {stats?.risk_distribution && Object.keys(stats.risk_distribution).length > 0 ? (
            <ul className="space-y-3">
              {Object.entries(stats.risk_distribution).map(([label, count]) => (
                <li key={label} className="flex items-center justify-between text-sm">
                  <span className="text-slate-700 font-medium">{label}</span>
                  <span className="rounded-full bg-slate-100 px-3 py-0.5 text-xs font-bold text-slate-800">
                    {count}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500 italic">Chưa có dữ liệu phân tích.</p>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Trạng thái báo cáo cộng đồng</h2>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <span className="text-xs font-semibold text-amber-700">Chờ duyệt (Pending)</span>
              <p className="text-xl font-bold text-amber-900 mt-1">{stats?.pending_reports ?? 0}</p>
            </div>
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
              <span className="text-xs font-semibold text-blue-700">Đang xử lý (Under review)</span>
              <p className="text-xl font-bold text-blue-900 mt-1">{stats?.under_review_reports ?? 0}</p>
            </div>
            <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
              <span className="text-xs font-semibold text-rose-700">Xác nhận rủi ro (Verified)</span>
              <p className="text-xl font-bold text-rose-900 mt-1">{stats?.verified_reports ?? 0}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-100 p-3">
              <span className="text-xs font-semibold text-slate-600">Từ chối (Rejected)</span>
              <p className="text-xl font-bold text-slate-800 mt-1">{stats?.rejected_reports ?? 0}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
