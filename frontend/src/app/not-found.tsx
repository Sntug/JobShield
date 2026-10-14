import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Không tìm thấy trang</h1>
      <p className="mt-4 text-slate-700">
        Trang bạn yêu cầu chưa có. Bạn có thể quay lại trang chủ.
      </p>
      <Link href="/" className="mt-6 inline-block underline">
        Về trang chủ
      </Link>
    </main>
  );
}
