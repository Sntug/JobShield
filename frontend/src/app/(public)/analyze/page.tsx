"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AnalysisResponse } from "@/types/api";
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

export default function AnalyzePage() {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSessionInvalid, setIsSessionInvalid] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const revision = useRef(0);

  // Đồng bộ trạng thái với query ?id=... trong URL trên mount và khi Back/Forward (popstate)
  useEffect(() => {
    if (typeof window === "undefined") return;

    let active = true;
    const syncWithUrl = async () => {
      const current = ++revision.current;
      setAnalysis(null);
      setIsSubmitting(false);
      const params = new URLSearchParams(window.location.search);
      const id = params.get("id");
      const token = getAuthToken() || getGuestToken();

      if (id) {
        if (!token) {
          setAnalysis(null);
          setIsLoadingDetail(false);
          setError("Không có phiên khách để đọc kết quả phân tích. Vui lòng dán và phân tích tin mới.");
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
          setError("Không thể tải lại kết quả trước đó. Bạn có thể dán và phân tích lại.");
          if (e.code === "SESSION_INVALID") {
            setIsSessionInvalid(true);
          }
        } finally {
          if (active && current === revision.current) setIsLoadingDetail(false);
        }
      } else {
        // Ignore detail responses that belong to the previous URL.
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
      <nav aria-label="Điều hướng" className="mb-6 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
        <Link href="/" className="hover:text-slate-900 dark:hover:text-slate-100 transition-colors">Trang chủ</Link>
        <span>/</span>
        <span className="text-slate-900 dark:text-slate-100 font-semibold">Phân tích tin tuyển dụng</span>
        <span className="mx-1 text-slate-300 dark:text-slate-700">•</span>
        <Link href="/verify-employer" className="text-sky-600 hover:underline dark:text-sky-400">Xác minh nhà tuyển dụng</Link>
      </nav>
      <div className="mb-8 text-center sm:text-left">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl dark:text-slate-100">
          Phân tích tin tuyển dụng
        </h1>
        <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Dán nội dung tin tuyển dụng để phát hiện dấu hiệu rủi ro, trích xuất dữ kiện và việc cần xác minh trước khi nộp hồ sơ.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200/90 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900/90 sm:p-8">
        {analysis ? (
          <AnalysisResults analysis={analysis} onReset={handleReset} />
        ) : (
          <RecruitmentInputForm
            onSubmit={handleAnalyze}
            isLoading={isLoading}
            error={error}
            onResetSession={handleResetSession}
            isSessionInvalid={isSessionInvalid}
          />
        )}
      </div>
    </div>
  );
}
