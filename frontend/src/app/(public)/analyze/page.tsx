"use client";

import React, { useEffect, useState } from "react";
import { AnalysisResponse } from "@/types/api";
import {
  clearGuestToken,
  createAnalysis,
  getAnalysis,
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

  // Đồng bộ trạng thái với query ?id=... trong URL trên mount và khi Back/Forward (popstate)
  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncWithUrl = async () => {
      const params = new URLSearchParams(window.location.search);
      const id = params.get("id");
      const token = getGuestToken();

      if (id) {
        if (!token) {
          setAnalysis(null);
          setError("Không có phiên khách để đọc kết quả phân tích. Vui lòng dán và phân tích tin mới.");
          return;
        }
        setIsLoadingDetail(true);
        setError(null);
        try {
          const data = await getAnalysis(id);
          setAnalysis(data);
        } catch (err: unknown) {
          const e = err as { message?: string; code?: string };
          setAnalysis(null);
          setError("Không thể tải lại kết quả trước đó. Bạn có thể dán và phân tích lại.");
          if (e.code === "SESSION_INVALID") {
            setIsSessionInvalid(true);
          }
        } finally {
          setIsLoadingDetail(false);
        }
      } else {
        // Người dùng ấn Back về /analyze không có id -> trả về form nhập liệu
        setAnalysis(null);
        setError(null);
        setIsSessionInvalid(false);
      }
    };

    syncWithUrl();
    window.addEventListener("popstate", syncWithUrl);
    return () => {
      window.removeEventListener("popstate", syncWithUrl);
    };
  }, []);

  const handleAnalyze = async (text: string) => {
    if (isSubmitting || isLoadingDetail) return;
    setIsSubmitting(true);
    setError(null);
    setIsSessionInvalid(false);

    try {
      const data = await createAnalysis(text);
      setAnalysis(data);
      if (typeof window !== "undefined") {
        const url = new URL(window.location.href);
        url.searchParams.set("id", data.id);
        window.history.pushState({ id: data.id }, "", url.toString());
      }
    } catch (err: unknown) {
      const e = err as { message?: string; code?: string };
      setError(e.message || "Đã xảy ra lỗi khi phân tích tin.");
      if (e.code === "SESSION_INVALID") {
        setIsSessionInvalid(true);
      }
    } finally {
      setIsSubmitting(false);
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
      <div className="mb-8 text-center sm:text-left">
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl dark:text-slate-100">
          Phân tích tin tuyển dụng
        </h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Dán nội dung tin tuyển dụng để phát hiện dấu hiệu rủi ro, trích xuất dữ kiện và việc cần xác minh trước khi nộp hồ sơ.
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950 sm:p-8">
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
