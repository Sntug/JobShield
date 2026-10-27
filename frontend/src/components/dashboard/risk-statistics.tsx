import React from "react";
import { UserStats } from "@/types/api";

interface RiskStatisticsProps {
  stats: UserStats;
}

export function RiskStatistics({ stats }: RiskStatisticsProps) {
  const highRisk = stats.risk_distribution["Rủi ro cao"] || 0;
  const lowRisk = stats.risk_distribution["Ít dấu hiệu rủi ro"] || 0;
  const insufficient = stats.risk_distribution["Không đủ thông tin"] || 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Tổng tin đã phân tích</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-slate-900">
            {stats.total_analyses}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Tin đã lưu</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-blue-600">
            {stats.saved_analyses}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Tin rủi ro cao</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-rose-600">
            {highRisk}
          </p>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm font-medium text-slate-500">Ít dấu hiệu rủi ro</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-emerald-600">
            {lowRisk}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900 mb-4">
          Phân bổ mức độ rủi ro
        </h3>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium text-slate-700">Rủi ro cao</span>
              <span className="text-slate-600">{highRisk}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-rose-500"
                style={{
                  width: `${stats.total_analyses ? (highRisk / stats.total_analyses) * 100 : 0}%`,
                }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium text-slate-700">Không đủ thông tin</span>
              <span className="text-slate-600">{insufficient}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-amber-500"
                style={{
                  width: `${stats.total_analyses ? (insufficient / stats.total_analyses) * 100 : 0}%`,
                }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="font-medium text-slate-700">Ít dấu hiệu rủi ro</span>
              <span className="text-slate-600">{lowRisk}</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full bg-emerald-500"
                style={{
                  width: `${stats.total_analyses ? (lowRisk / stats.total_analyses) * 100 : 0}%`,
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
