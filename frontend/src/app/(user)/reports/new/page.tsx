"use client";

import React from "react";
import Link from "next/link";
import { ReportForm } from "@/components/reports/report-form";

export default function NewReportPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Gửi báo cáo tuyển dụng đáng ngờ
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Cung cấp thông tin để hỗ trợ cộng đồng phòng ngừa các thủ đoạn lừa đảo việc làm.
          </p>
        </div>
        <Link
          href="/reports"
          className="text-sm font-medium text-slate-600 hover:text-slate-900"
        >
          ← Báo cáo của tôi
        </Link>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <ReportForm />
      </div>
    </div>
  );
}
