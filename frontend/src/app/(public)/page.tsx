"use client";

import { useState } from "react";
import Link from "next/link";
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
      setResult(`HTTP ${res.status}: ${data.detail?.message_vi || `${data.status} (DB: ${data.database})`}`);
    } catch {
      setResult("Lỗi: Không thể kết nối tới backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <p className="text-sm font-medium text-emerald-700">
        Phân tích và đối chiếu tin tuyển dụng
      </p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight">JobShield</h1>
      <p className="mt-4 text-base text-slate-700">
        Đọc dấu hiệu rủi ro và kiểm tra thông tin nhà tuyển dụng trước khi ứng tuyển.
      </p>
      <p className="mt-2 text-sm text-slate-600">
        Kết quả giải thích căn cứ và thông tin còn thiếu; khớp nguồn không bảo đảm tin an toàn.
      </p>

      <div className="mt-6 space-y-3">
        <div>
          <Button type="button" onClick={handleCheckApi} disabled={loading}>
            {loading ? "Đang kiểm tra..." : "Nút kiểm tra giao diện"}
          </Button>
        </div>
        {result && (
          <p className="rounded bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-800">
            {result}
          </p>
        )}
      </div>
      <nav aria-label="Chức năng chính" className="mt-8 flex flex-wrap gap-4">
        <Link href="/analyze" className="rounded-lg bg-slate-900 px-4 py-3 font-medium text-white focus-visible:outline-2 focus-visible:outline-blue-600">Phân tích tin tuyển dụng</Link>
        <Link href="/verify-employer" className="rounded-lg border border-slate-300 px-4 py-3 font-medium focus-visible:outline-2 focus-visible:outline-blue-600">Xác minh nhà tuyển dụng</Link>
        <Link href="/login" className="rounded-lg border border-slate-300 px-4 py-3 font-medium focus-visible:outline-2 focus-visible:outline-blue-600">Đăng nhập tài khoản</Link>
      </nav>
    </main>
  );
}
