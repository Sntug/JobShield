import { Button } from "@/components/ui/button";

export default function HomePage() {
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

      <div className="mt-6">
        <Button type="button">Nút kiểm tra giao diện</Button>
      </div>
    </main>
  );
}
