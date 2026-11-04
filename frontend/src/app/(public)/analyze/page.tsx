"use client";

import React, { Suspense, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  AnalysisResponse,
  BatchAnalysisCreate,
  BatchAnalysisResponse,
  BatchItemInput,
  BatchItemResponse,
} from "@/types/api";
import {
  AUTH_CHANGED_EVENT,
  clearGuestToken,
  createAnalysis,
  getAnalysis,
  getAuthToken,
  getGuestToken,
} from "@/lib/api-client";
import { RecruitmentInputForm } from "@/components/analysis/recruitment-input-form";
import { AnalysisResults } from "@/components/analysis/analysis-results";
import { BatchRecruitmentForm } from "@/components/analysis/batch-recruitment-form";
import { BatchProgressView } from "@/components/analysis/batch-progress-view";
import { ACTIVE_BATCH_KEY, useBatchAnalysis } from "@/hooks/use-batch-analysis";
import { FileText, Layers, Loader2 } from "lucide-react";

export type AnalysisMode = "single" | "batch";

export default function AnalyzePage() {
  return (
    <Suspense fallback={<p role="status" className="p-6 text-center">Đang tải...</p>}>
      <AnalysisPageContent />
    </Suspense>
  );
}

function AnalysisPageContent() {
  const searchParams = useSearchParams();
  const sample = searchParams?.get("sample") || "";
  const idParam = searchParams?.get("id");
  const batchIdParam = searchParams?.get("batch_id");

  // Mode state: "single" (Một tin) vs "batch" (Nhiều tin)
  const [mode, setMode] = useState<AnalysisMode>(() => {
    if (sample || idParam) return "single";
    if (batchIdParam) return "batch";
    if (typeof window !== "undefined") {
      const sp = new URLSearchParams(window.location.search);
      if (sp.get("id") || sp.get("sample")) return "single";
      if (sp.get("batch_id")) return "batch";
      try {
        if (localStorage.getItem(ACTIVE_BATCH_KEY)) return "batch";
      } catch {
        // ignore
      }
    }
    return "single";
  });

  // Single analysis state
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSessionInvalid, setIsSessionInvalid] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const revision = useRef(0);
  const batchRouteRevision = useRef(0);
  const lastBatchUrlId = useRef(batchIdParam);
  const [retryItem, setRetryItem] = useState<BatchItemInput | null>(null);

  const initialBatchId = idParam || sample ? null : batchIdParam ?? undefined;

  // Batch analysis hook
  const {
    batch,
    batchId,
    isLoading: isBatchLoading,
    isPolling,
    isCancelling,
    error: batchError,
    startBatch,
    cancelBatch,
    reset: resetBatch,
    loadBatch,
  } = useBatchAnalysis(initialBatchId);

  // Synchronize mode when URL params change via props / context
  const [prevParams, setPrevParams] = useState({ idParam, sample, batchIdParam });
  if (
    prevParams.idParam !== idParam ||
    prevParams.sample !== sample ||
    prevParams.batchIdParam !== batchIdParam
  ) {
    setPrevParams({ idParam, sample, batchIdParam });
    setRetryItem(null);
    if (idParam || sample) {
      setMode("single");
    } else if (batchIdParam) {
      setMode("batch");
    }
  }

  // Synchronize with URL (?id=... / ?batch_id=...) on mount & popstate
  useEffect(() => {
    if (typeof window === "undefined") return;

    let active = true;
    const syncWithUrl = async () => {
      const current = ++revision.current;
      batchRouteRevision.current += 1;
      setRetryItem(null);
      const params = new URLSearchParams(window.location.search);
      const id = params.get("id");
      const sampleQuery = params.get("sample");
      const batchId = params.get("batch_id");

      if (id || sampleQuery) {
        setMode("single");
      } else if (batchId) {
        setMode("batch");
      }

      setAnalysis(null);
      setIsSubmitting(false);
      const token = getAuthToken() || getGuestToken();

      if (id) {
        if (!token) {
          setAnalysis(null);
          setIsLoadingDetail(false);
          setError(
            "Không có phiên khách để đọc kết quả phân tích. Vui lòng dán và phân tích tin mới."
          );
          return;
        }
        setIsLoadingDetail(true);
        setError(null);
        try {
          const data = await getAnalysis(id);
          if (!active || current !== revision.current) return;
          setAnalysis(data);
        } catch (err: unknown) {
          if (!active || current !== revision.current) return;
          const e = err as { message?: string; code?: string };
          setAnalysis(null);
          setError(
            "Không thể tải lại kết quả trước đó. Bạn có thể dán và phân tích lại."
          );
          if (e.code === "SESSION_INVALID") {
            setIsSessionInvalid(true);
          }
        } finally {
          if (active && current === revision.current) setIsLoadingDetail(false);
        }
      } else {
        // Ignore detail responses that belong to previous URL
        setIsLoadingDetail(false);
        setAnalysis(null);
        setError(null);
        setIsSessionInvalid(false);
      }
    };

    syncWithUrl();
    window.addEventListener("popstate", syncWithUrl);
    window.addEventListener(AUTH_CHANGED_EVENT, syncWithUrl);
    return () => {
      active = false;
      revision.current += 1;
      window.removeEventListener("popstate", syncWithUrl);
      window.removeEventListener(AUTH_CHANGED_EVENT, syncWithUrl);
    };
  }, []);

  useEffect(() => {
    if (batchIdParam) {
      lastBatchUrlId.current = batchIdParam;
      return;
    }
    if (mode !== "batch" || !batchId || lastBatchUrlId.current === batchId) return;

    lastBatchUrlId.current = batchId;
    const url = new URL(window.location.href);
    url.searchParams.set("batch_id", batchId);
    window.history.replaceState({ batch_id: batchId }, "", url.toString());
  }, [batchId, batchIdParam, idParam, mode, sample]);

  const handleSwitchMode = (newMode: AnalysisMode) => {
    batchRouteRevision.current += 1;
    setRetryItem(null);
    if (newMode === "single") lastBatchUrlId.current = null;
    setMode(newMode);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (newMode === "single") {
        url.searchParams.delete("batch_id");
        if (analysis) {
          url.searchParams.set("id", analysis.id);
        }
      } else {
        url.searchParams.delete("id");
        url.searchParams.delete("sample");
        if (batch) {
          url.searchParams.set("batch_id", batch.id);
        }
      }
      window.history.replaceState({}, "", url.toString());
    }
  };

  const handleAnalyze = async (
    text: string,
    options?: { use_ai?: boolean; ai_consent?: boolean }
  ) => {
    if (isSubmitting || isLoadingDetail) return;
    const current = ++revision.current;
    setIsSubmitting(true);
    setError(null);
    setIsSessionInvalid(false);

    try {
      const data = await createAnalysis(text, options);
      if (current !== revision.current) return;
      setAnalysis(data);
      if (typeof window !== "undefined") {
        const url = new URL(window.location.href);
        url.searchParams.delete("batch_id");
        url.searchParams.set("id", data.id);
        window.history.pushState({ id: data.id }, "", url.toString());
      }
    } catch (err: unknown) {
      if (current !== revision.current) return;
      const e = err as { message?: string; code?: string };
      setError(e.message || "Đã xảy ra lỗi khi phân tích tin.");
      if (e.code === "SESSION_INVALID") {
        setIsSessionInvalid(true);
      }
    } finally {
      if (current === revision.current) setIsSubmitting(false);
    }
  };

  const handleStartBatch = async (payload: BatchAnalysisCreate) => {
    const current = batchRouteRevision.current;
    let res: BatchAnalysisResponse;
    try {
      res = await startBatch(payload);
    } catch {
      return;
    }
    if (current !== batchRouteRevision.current) return;
    setRetryItem(null);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("id");
      url.searchParams.delete("sample");
      url.searchParams.set("batch_id", res.id);
      lastBatchUrlId.current = res.id;
      window.history.pushState({ batch_id: res.id }, "", url.toString());
    }
  };

  const handleResetBatch = () => {
    batchRouteRevision.current += 1;
    setRetryItem(null);
    lastBatchUrlId.current = null;
    resetBatch();
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("batch_id");
      window.history.replaceState({}, "", url.toString());
    }
  };

  const handleRetryItem = (item: BatchItemResponse) => {
    setRetryItem({ type: item.input_type, value: item.input_value });
  };

  const handleSwitchToText = () => {
    setRetryItem({ type: "text", value: "" });
  };

  const handleResetSession = () => {
    clearGuestToken();
    setError(null);
    setIsSessionInvalid(false);
  };

  const handleReset = () => {
    setAnalysis(null);
    setError(null);
    setIsSessionInvalid(false);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("id");
      window.history.pushState({}, "", url.toString());
    }
  };

  const isLoading = isSubmitting || isLoadingDetail;

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
      <nav
        aria-label="Điều hướng"
        className="mb-6 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400"
      >
        <Link
          href="/"
          className="hover:text-slate-900 dark:hover:text-slate-100 transition-colors"
        >
          Trang chủ
        </Link>
        <span>/</span>
        <span className="text-slate-900 dark:text-slate-100 font-semibold">
          Phân tích tin tuyển dụng
        </span>
        <span className="mx-1 text-slate-300 dark:text-slate-700">•</span>
        <Link
          href="/verify-employer"
          className="text-sky-600 hover:underline dark:text-sky-400"
        >
          Xác minh nhà tuyển dụng
        </Link>
      </nav>

      <div className="mb-8 text-center sm:text-left">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl dark:text-slate-100">
          Phân tích tin tuyển dụng
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Dán nội dung hoặc liên kết tin tuyển dụng để phát hiện dấu hiệu rủi ro, trích xuất dữ kiện và việc cần xác minh trước khi nộp hồ sơ.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/90 sm:p-8">
        {/* Mode Switcher Tabs */}
        <div className="mb-6 border-b border-slate-100 pb-4 dark:border-slate-800">
          <div
            role="tablist"
            aria-label="Chọn chế độ phân tích tin tuyển dụng"
            className="inline-flex rounded-xl bg-slate-100 p-1.5 dark:bg-slate-800/80"
          >
            <button
              type="button"
              role="tab"
              id="mode-tab-single"
              aria-selected={mode === "single"}
              aria-controls="mode-panel-single"
              onClick={() => handleSwitchMode("single")}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs sm:text-sm font-semibold transition-all ${
                mode === "single"
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-slate-100"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              <FileText className="size-4 shrink-0" />
              <span>Một tin</span>
            </button>
            <button
              type="button"
              role="tab"
              id="mode-tab-batch"
              aria-selected={mode === "batch"}
              aria-controls="mode-panel-batch"
              onClick={() => handleSwitchMode("batch")}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs sm:text-sm font-semibold transition-all ${
                mode === "batch"
                  ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-slate-100"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
              }`}
            >
              <Layers className="size-4 shrink-0" />
              <span>Nhiều tin</span>
            </button>
          </div>
        </div>

        {/* Single Mode View */}
        {mode === "single" && (
          <div id="mode-panel-single" role="tabpanel" aria-labelledby="mode-tab-single">
            {analysis ? (
              <AnalysisResults analysis={analysis} onReset={handleReset} />
            ) : (
              <RecruitmentInputForm
                key={sample}
                initialText={sample}
                onSubmit={handleAnalyze}
                isLoading={isLoading}
                error={error}
                onResetSession={handleResetSession}
                isSessionInvalid={isSessionInvalid}
              />
            )}
          </div>
        )}

        {/* Batch Mode View */}
        {mode === "batch" && (
          <div id="mode-panel-batch" role="tabpanel" aria-labelledby="mode-tab-batch">
            {isBatchLoading && !batch ? (
              <div role="status" className="p-8 text-center text-sm text-slate-500 space-y-2">
                <Loader2 className="mx-auto size-6 animate-spin text-sky-600" />
                <p>Đang tải dữ liệu phân tích theo lô...</p>
              </div>
            ) : batch ? (
              <>
                <BatchProgressView
                  batch={batch}
                  isPolling={isPolling}
                  isCancelling={isCancelling}
                  error={batchError}
                  onRetry={() => {
                    if (batchId) void loadBatch(batchId);
                  }}
                  onCancel={cancelBatch}
                  onReset={handleResetBatch}
                  onRetryItem={handleRetryItem}
                  onSwitchToText={handleSwitchToText}
                />
                {retryItem && (
                  <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
                    <h3 className="mb-4 text-sm font-bold text-slate-900 dark:text-slate-100">
                      Phân tích lại trong một lượt mới
                    </h3>
                    <BatchRecruitmentForm
                      key={`${batch.id}-${retryItem.type}-${retryItem.value}`}
                      initialItem={retryItem}
                      submitLabel="Phân tích lượt mới"
                      onSubmit={handleStartBatch}
                      isLoading={isBatchLoading}
                      error={batchError}
                      onRetry={
                        batchId
                          ? () => {
                              void loadBatch(batchId);
                            }
                          : undefined
                      }
                    />
                  </div>
                )}
              </>
            ) : (
              <BatchRecruitmentForm
                onSubmit={handleStartBatch}
                isLoading={isBatchLoading}
                error={batchError}
                onRetry={
                  batchId
                    ? () => {
                        void loadBatch(batchId);
                      }
                    : undefined
                }
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
