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
    <nav aria-label="Điều hướng" className="mb-6 flex flex-wrap gap-5 text-sm">
      <Link href="/" className="text-blue-700 underline dark:text-blue-300">Trang chủ</Link>
      <Link href="/analyze" className="text-blue-700 underline dark:text-blue-300">Phân tích tin tuyển dụng</Link>
    </nav>
    <header className="mb-7">
      <h1 ref={heading} tabIndex={-1} className="text-2xl font-semibold tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-blue-600 sm:text-3xl">Xác minh nhà tuyển dụng</h1>
      <p className="mt-3 max-w-2xl text-base leading-relaxed text-slate-600 dark:text-slate-300">Đối chiếu thông tin doanh nghiệp và kênh liên hệ với nguồn có căn cứ. Xem rõ phần đã khớp, phần chưa kiểm tra được và việc cần xác minh thêm.</p>
    </header>
    <div aria-busy={loading} className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900 sm:p-7">
      {result ? <VerificationResults result={result} onReset={reset} /> : <VerificationForm onSubmit={submit} isLoading={loading} error={error} />}
    </div>
  </main>;
}
