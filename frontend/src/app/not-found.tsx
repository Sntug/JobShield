import Link from "next/link";
import { ShieldAlert, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-xl flex-col items-center justify-center px-6 py-16 text-center">
      <div className="flex size-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-600 shadow-sm dark:bg-slate-800 dark:text-slate-300">
        <ShieldAlert className="size-7 text-sky-600" />
      </div>
      <h1 className="mt-5 text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
        Không tìm thấy trang
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        Trang bạn yêu cầu chưa có hoặc đã được chuyển dời. Bạn có thể quay lại trang chủ.
      </p>
      <Link
        href="/"
        className="mt-6 inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-slate-800 transition-colors"
      >
        <ArrowLeft className="size-4" />
        <span>Về trang chủ</span>
      </Link>
    </main>
  );
}
