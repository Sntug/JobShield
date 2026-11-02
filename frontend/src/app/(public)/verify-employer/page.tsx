"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { VerificationForm } from "@/components/employers/verification-form";
import { VerificationResults } from "@/components/employers/verification-results";
import { createVerification } from "@/lib/api-client";
import { VerificationCreate, VerificationResponse } from "@/types/api";

export default function VerifyEmployerPage() {
  const [result, setResult] = useState<VerificationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => () => controller.current?.abort(), []);
  const submit = async (payload: VerificationCreate) => {
    if (loading) return;
    const current = new AbortController();
    controller.current = current;
    setLoading(true);
    setError(null);
    try {
      const response = await createVerification(payload, current.signal);
      if (!current.signal.aborted) setResult(response);
    } catch (error) {
      if (!current.signal.aborted) setError(error instanceof Error ? error.message : "Không thể hoàn tất xác minh. Vui lòng thử lại.");
    } finally {
      if (!current.signal.aborted) setLoading(false);
    }
  };
  const reset = () => {
    setResult(null);
    setError(null);
    heading.current?.focus();
  };
  return <main className="mx-auto max-w-4xl px-4 py-8 text-slate-900 dark:text-slate-100 sm:px-6">
    <nav aria-label="Điều hướng" className="mb-6 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400">
      <Link href="/" className="hover:text-slate-900 dark:hover:text-slate-100 transition-colors">Trang chủ</Link>
      <span>/</span>
      <span className="text-slate-900 dark:text-slate-100 font-semibold">Xác minh nhà tuyển dụng</span>
      <span className="mx-1 text-slate-300 dark:text-slate-700">•</span>
      <Link href="/analyze" className="text-sky-600 hover:underline dark:text-sky-400">Phân tích tin tuyển dụng</Link>
    </nav>
    <header className="mb-8">
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-extrabold tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-sky-600 sm:text-3xl text-slate-950 dark:text-white">Xác minh nhà tuyển dụng</h1>
      <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">Đối chiếu thông tin doanh nghiệp và kênh liên hệ với nguồn có căn cứ. Xem rõ phần đã khớp, phần chưa kiểm tra được và việc cần xác minh thêm.</p>
    </header>
    <div aria-busy={loading} className="rounded-2xl border border-slate-200/90 bg-white p-6 dark:border-slate-800 dark:bg-slate-900/90 sm:p-8 shadow-sm">
      {result ? <VerificationResults result={result} onReset={reset} /> : <VerificationForm onSubmit={submit} isLoading={loading} error={error} />}
    </div>
  </main>;
}
