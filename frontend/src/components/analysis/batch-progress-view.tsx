"use client";

import React, { useState } from "react";
import { BatchAnalysisResponse, BatchItemResponse, BatchStatus } from "@/types/api";
import { AnalysisResults } from "@/components/analysis/analysis-results";
import { Button } from "@/components/ui/button";
import {
  AlertCircle,
  ArrowLeft,
  Ban,
  CheckCircle2,
  Clock,
  ExternalLink,
  FileText,
  Loader2,
  RefreshCw,
  XCircle,
} from "lucide-react";

export interface BatchProgressViewProps {
  batch: BatchAnalysisResponse;
  isPolling?: boolean;
  isCancelling?: boolean;
  error?: string | null;
  onCancel?: () => Promise<void> | void;
  onRetry?: () => Promise<void> | void;
  onReset?: () => void;
  onRetryItem?: (item: BatchItemResponse) => void;
  onSwitchToText?: (item: BatchItemResponse) => void;
}

function getBatchStatusMeta(status: BatchStatus) {
  switch (status) {
    case "completed":
      return {
        label: "Hoàn thành",
        color:
          "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800",
        icon: CheckCircle2,
      };
    case "cancelled":
      return {
        label: "Đã hủy",
        color:
          "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700",
        icon: XCircle,
      };
    case "failed":
      return {
        label: "Thất bại",
        color:
          "bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800",
        icon: AlertCircle,
      };
    case "pending":
    case "processing":
    default:
      return {
        label: "Đang xử lý...",
        color:
          "bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800",
        icon: Loader2,
      };
  }
}

function getRiskBadgeColor(risk?: string) {
  switch (risk) {
    case "Rủi ro cao":
      return "bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800";
    case "Ít dấu hiệu rủi ro":
      return "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800";
    default:
      return "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800";
  }
}

function getVerificationBadgeColor(verif?: string) {
  switch (verif) {
    case "Khớp nguồn đã xác minh":
      return "bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-950/60 dark:text-sky-300 dark:border-sky-800";
    case "Thông tin xung đột":
      return "bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-950/60 dark:text-orange-300 dark:border-orange-800";
    default:
      return "bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700";
  }
}

export function BatchProgressView({
  batch,
  isPolling = false,
  isCancelling = false,
  error = null,
  onCancel,
  onRetry,
  onReset,
  onRetryItem,
  onSwitchToText,
}: BatchProgressViewProps) {
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);

  const total = batch.total_items || batch.items.length || 0;
  const processed = batch.processed_items;
  const percent = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  const statusMeta = getBatchStatusMeta(batch.status);
  const StatusIcon = statusMeta.icon;

  const isBatchActive =
    isPolling || batch.status === "pending" || batch.status === "processing";

  // In-place detail view
  const selectedItem = selectedItemId
    ? batch.items.find((item) => item.id === selectedItemId)
    : null;

  if (selectedItem && selectedItem.analysis) {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200/80 pb-3 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSelectedItemId(null)}
              className="text-xs font-semibold gap-1.5"
            >
              <ArrowLeft className="size-3.5" />
              <span>Quay lại danh sách</span>
            </Button>
            <span className="text-xs text-slate-500">
              Đang xem chi tiết tin #{selectedItem.item_order}
            </span>
          </div>

          <span className="text-xs font-medium text-slate-400">
            {selectedItem.input_type === "url" ? "Nguồn liên kết" : "Nội dung văn bản"}
          </span>
        </div>

        <AnalysisResults
          analysis={selectedItem.analysis}
          onReset={() => setSelectedItemId(null)}
          resetLabel="Quay lại danh sách"
        />
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      {/* Header card with progress bar and status badge */}
      <div className="rounded-2xl border border-slate-200 bg-slate-50/60 p-5 dark:border-slate-800 dark:bg-slate-900/50 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span
              data-testid="batch-status-badge"
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-bold ${statusMeta.color}`}
            >
              <StatusIcon
                className={`size-3.5 ${
                  batch.status === "pending" || batch.status === "processing"
                    ? "animate-spin"
                    : ""
                }`}
              />
              <span>{statusMeta.label}</span>
            </span>
            <span className="text-xs text-slate-500 font-medium">
              ID lô: {batch.id.slice(0, 8)}...
            </span>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2">
            {isBatchActive && onCancel && (
              batch.status !== "cancelled" && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onCancel}
                disabled={isCancelling}
                className="text-xs font-semibold text-rose-600 border-rose-200 hover:bg-rose-50 dark:border-rose-900/50 dark:hover:bg-rose-950/30"
              >
                <Ban className="size-3.5 mr-1.5" />
                {isCancelling ? "Đang hủy..." : "Hủy lượt"}
              </Button>
              )
            )}

            {!isBatchActive && onReset && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onReset}
                className="text-xs font-semibold text-slate-700 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100"
              >
                <RefreshCw className="size-3.5 mr-1.5" />
                Kiểm tra lượt mới
              </Button>
            )}
          </div>
        </div>

        {/* Progress Bar & Counter */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-600 dark:text-slate-400">
            <span>Đã xử lý {processed}/{total} tin</span>
            <span>{percent}%</span>
          </div>
          <div
            role="progressbar"
            aria-valuenow={percent}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Tiến độ phân tích: ${processed}/${total} tin`}
            className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
          >
            <div
              className={`h-full transition-all duration-300 ${
                batch.status === "failed"
                  ? "bg-rose-500"
                  : batch.status === "cancelled"
                  ? "bg-slate-400"
                  : batch.status === "completed"
                  ? "bg-emerald-500"
                  : "bg-sky-600"
              }`}
              style={{ width: `${percent}%` }}
            />
          </div>
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200"
        >
          <span>{error}</span>
          {onRetry && (
            <Button type="button" variant="outline" size="sm" onClick={onRetry}>
              Thử tải lại
            </Button>
          )}
        </div>
      )}

      {/* Items List */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
          Danh sách tin tuyển dụng ({batch.items.length})
        </h3>

        <div className="divide-y divide-slate-100 rounded-2xl border border-slate-200 bg-white shadow-sm dark:divide-slate-800 dark:border-slate-800 dark:bg-slate-900 overflow-hidden">
          {batch.items.map((item) => {
            const isSuccess = item.status === "success" && !!item.analysis;
            const isError = item.status === "error";
            const isProcessing = item.status === "processing";
            const isPending = item.status === "pending";
            const isCancelled = item.status === "cancelled";

            return (
              <div
                key={item.id}
                className="p-4 sm:p-5 transition-colors hover:bg-slate-50/50 dark:hover:bg-slate-800/40 space-y-2.5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-bold text-slate-700 dark:bg-slate-800 dark:text-slate-300 mt-0.5">
                      {item.item_order}
                    </span>

                    <div className="space-y-1 flex-1 min-w-0">
                      {/* Success Job Title or Company */}
                      {isSuccess && (
                        <div>
                          <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">
                            {item.analysis?.job?.job_title || "Tin tuyển dụng"}
                          </h4>
                          {item.analysis?.job?.company_name && (
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              {item.analysis.job.company_name}
                            </p>
                          )}
                        </div>
                      )}

                      {/* Input Preview */}
                      {item.input_type === "url" ? (
                        <div className="flex items-center gap-1.5 text-xs text-sky-600 dark:text-sky-400 font-mono">
                          <ExternalLink className="size-3.5 shrink-0 text-slate-400" />
                          <a
                            href={item.input_value}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline truncate"
                          >
                            {item.input_value}
                          </a>
                        </div>
                      ) : (
                        <div className="flex items-start gap-1.5 text-xs text-slate-600 dark:text-slate-400">
                          <FileText className="size-3.5 shrink-0 mt-0.5 text-slate-400" />
                          <p className="line-clamp-2 leading-relaxed">
                            {item.input_value}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Status Badge & Actions */}
                  <div className="flex flex-wrap items-center gap-2 shrink-0">
                    {isPending && (
                      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                        <Clock className="size-3" />
                        Đang chờ
                      </span>
                    )}

                    {isProcessing && (
                      <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300">
                        <Loader2 className="size-3 animate-spin" />
                        Đang xử lý...
                      </span>
                    )}

                    {isCancelled && (
                      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                        <Ban className="size-3" />
                        Đang hủy / Đã hủy
                      </span>
                    )}

                    {isSuccess && (
                      <>
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-bold ${getRiskBadgeColor(
                            item.analysis?.risk_label_vi
                          )}`}
                        >
                          {item.analysis?.risk_label_vi}
                        </span>

                        <span
                          className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${getVerificationBadgeColor(
                            item.analysis?.verification_label_vi
                          )}`}
                        >
                          {item.analysis?.verification_label_vi}
                        </span>

                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedItemId(item.id)}
                          className="text-xs font-semibold"
                        >
                          Xem chi tiết
                        </Button>
                      </>
                    )}
                  </div>
                </div>

                {/* Error Banner & Remediation */}
                {isError && (
                  <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="size-4 shrink-0 text-red-600" />
                      <span className="font-medium">
                        {item.error_message || "Đã xảy ra lỗi khi xử lý tin tuyển dụng này."}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {onRetryItem && (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => onRetryItem(item)}
                          className="h-7 text-xs bg-white text-red-700 hover:bg-red-100 border-red-300 dark:bg-slate-900 dark:text-red-300 dark:border-red-800"
                        >
                          <RefreshCw className="size-3 mr-1" />
                          Thử lại
                        </Button>
                      )}

                      {item.input_type === "url" && onSwitchToText && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => onSwitchToText(item)}
                          className="h-7 text-xs text-red-700 hover:bg-red-100 dark:text-red-300"
                        >
                          Dán văn bản thay thế
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
