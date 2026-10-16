"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleCheckApi = async () => {
    setLoading(true);
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
      const res = await fetch(`${baseUrl}/ready`);
      const data = await res.json();
      setResult(`HTTP ${res.status}: ${data.status} (DB: ${data.database})`);
    } catch {
      setResult("Lỗi: Không thể kết nối tới backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <p className="text-sm font-medium text-emerald-700">
        Kiểm tra môi trường frontend
      </p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight">JobShield</h1>
      <p className="mt-4 text-base text-slate-700">
        Next.js, React và Tailwind đang được kiểm tra trong G1.
      </p>
      <p className="mt-2 text-sm text-slate-600">
        Các chức năng phân tích và xác minh chưa được triển khai.
      </p>

      <div className="mt-6 flex flex-col items-start gap-3">
        <Button type="button" onClick={handleCheckApi} disabled={loading}>
          {loading ? "Đang kiểm tra..." : "Nút kiểm tra giao diện"}
        </Button>
        {result && (
          <p className="rounded bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-800">
            {result}
          </p>
        )}
      </div>
    </main>
  );
}
