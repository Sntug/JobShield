import React from "react";
import { UserStats } from "@/types/api";
import { Sparkles, Bookmark, ShieldAlert, ShieldCheck, BarChart3 } from "lucide-react";

interface RiskStatisticsProps {
  stats: UserStats;
}

export function RiskStatistics({ stats }: RiskStatisticsProps) {
  const highRisk = stats.risk_distribution["Rủi ro cao"] || 0;
  const lowRisk = stats.risk_distribution["Ít dấu hiệu rủi ro"] || 0;
  const insufficient = stats.risk_distribution["Không đủ thông tin"] || 0;

  const highPercent = stats.total_analyses ? Math.round((highRisk / stats.total_analyses) * 100) : 0;
  const insufficientPercent = stats.total_analyses ? Math.round((insufficient / stats.total_analyses) * 100) : 0;
  const lowPercent = stats.total_analyses ? Math.round((lowRisk / stats.total_analyses) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* 4 Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Tổng tin */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Tổng tin đã phân tích
            </p>
            <span className="flex size-8 items-center justify-center rounded-lg bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
              <Sparkles className="size-4" />
            </span>
          </div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            {stats.total_analyses}
          </p>
        </div>

        {/* Card 2: Tin đã lưu */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Tin đã lưu
            </p>
            <span className="flex size-8 items-center justify-center rounded-lg bg-sky-50 text-sky-600 dark:bg-sky-950 dark:text-sky-300">
              <Bookmark className="size-4" />
            </span>
          </div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-sky-600 dark:text-sky-400">
            {stats.saved_analyses}
          </p>
        </div>

        {/* Card 3: Tin rủi ro cao */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Tin rủi ro cao
            </p>
            <span className="flex size-8 items-center justify-center rounded-lg bg-rose-50 text-rose-600 dark:bg-rose-950 dark:text-rose-300">
              <ShieldAlert className="size-4" />
            </span>
          </div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-rose-600 dark:text-rose-400">
            {highRisk}
          </p>
        </div>

        {/* Card 4: Ít dấu hiệu rủi ro */}
        <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm transition-all hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Ít dấu hiệu rủi ro
            </p>
            <span className="flex size-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-300">
              <ShieldCheck className="size-4" />
            </span>
          </div>
          <p className="mt-3 text-3xl font-extrabold tracking-tight text-emerald-600 dark:text-emerald-400">
            {lowRisk}
          </p>
        </div>
      </div>

      {/* Distribution Chart Card */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <BarChart3 className="size-4 text-slate-500" />
            <span>Phân bổ mức độ rủi ro</span>
          </h3>
          <span className="text-xs text-slate-400">
            {stats.total_analyses} lượt phân tích tổng cộng
          </span>
        </div>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-xs font-semibold mb-1.5">
              <span className="text-rose-700 dark:text-rose-300 flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-rose-500" />
                Rủi ro cao
              </span>
              <span className="text-slate-600 dark:text-slate-300">
                {highRisk} ({highPercent}%)
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-rose-500 transition-all rounded-full"
                style={{
                  width: `${stats.total_analyses ? (highRisk / stats.total_analyses) * 100 : 0}%`,
                }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-semibold mb-1.5">
              <span className="text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-amber-500" />
                Không đủ thông tin
              </span>
              <span className="text-slate-600 dark:text-slate-300">
                {insufficient} ({insufficientPercent}%)
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-amber-500 transition-all rounded-full"
                style={{
                  width: `${stats.total_analyses ? (insufficient / stats.total_analyses) * 100 : 0}%`,
                }}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-semibold mb-1.5">
              <span className="text-emerald-700 dark:text-emerald-300 flex items-center gap-1.5">
                <span className="size-2 rounded-full bg-emerald-500" />
                Ít dấu hiệu rủi ro
              </span>
              <span className="text-slate-600 dark:text-slate-300">
                {lowRisk} ({lowPercent}%)
              </span>
            </div>
            <div className="h-2.5 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-emerald-500 transition-all rounded-full"
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
