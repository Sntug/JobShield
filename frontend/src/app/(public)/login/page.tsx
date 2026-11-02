"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/auth/auth-form";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { ShieldCheck, Sparkles } from "lucide-react";

export default function LoginPage() {
  const { user, loading, login, hasGuestSession, claimGuest, dismissGuestClaim } = useAuth();
  const router = useRouter();
  const showClaimPrompt = Boolean(user && hasGuestSession);
  const [claimMessage, setClaimMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user && !hasGuestSession) {
      router.push("/dashboard");
    }
  }, [user, loading, hasGuestSession, router]);

  const handleLoginSubmit = async (data: { email: string; password: string }) => {
    await login(data.email, data.password);
  };

  const handleClaim = async () => {
    try {
      const res = await claimGuest();
      if (res && res.claimed_count > 0) {
        setClaimMessage(`Đã chuyển thành công ${res.claimed_count} kết quả phân tích vào tài khoản của bạn.`);
      }
      setTimeout(() => router.push("/dashboard"), 1500);
    } catch (err: unknown) {
      const e = err as { message?: string };
      setClaimMessage(e.message || "Không thể chuyển dữ liệu.");
      setTimeout(() => router.push("/dashboard"), 2000);
    }
  };

  const handleSkipClaim = () => {
    dismissGuestClaim();
    router.push("/dashboard");
  };

  return (
    <main className="mx-auto max-w-md px-4 py-12 sm:px-6 sm:py-16">
      <div className="text-center mb-8">
        <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-500 to-blue-700 text-white shadow-md shadow-sky-600/20">
          <ShieldCheck className="size-6" />
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-950 sm:text-3xl dark:text-white">
          Đăng nhập JobShield
        </h1>
        <p className="mt-2 text-xs sm:text-sm text-slate-600 dark:text-slate-400">
          Quản lý lịch sử phân tích, lưu trữ cảnh báo và bảo vệ thông tin ứng tuyển.
        </p>
      </div>

      {showClaimPrompt ? (
        <div className="rounded-2xl border border-sky-200 bg-sky-50/80 p-6 shadow-sm text-left space-y-4 dark:border-sky-900/50 dark:bg-sky-950/40">
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-sky-600" />
            <h2 className="text-base font-bold text-sky-950 dark:text-sky-200">
              Tìm thấy kết quả phân tích phiên khách
            </h2>
          </div>
          <p className="text-xs sm:text-sm leading-relaxed text-sky-900 dark:text-sky-300">
            Bạn có kết quả phân tích trong phiên làm việc vừa rồi. Bạn có muốn lưu các kết quả này vào tài khoản của mình không?
          </p>
          {claimMessage ? (
            <p className="text-xs sm:text-sm font-semibold text-emerald-800 dark:text-emerald-300">{claimMessage}</p>
          ) : (
            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                onClick={handleClaim}
                className="bg-sky-600 hover:bg-sky-700 text-white font-semibold text-xs"
              >
                Nhận vào tài khoản
              </Button>
              <Button
                type="button"
                onClick={handleSkipClaim}
                variant="outline"
                className="text-xs font-medium"
              >
                Bỏ qua
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200/90 bg-white p-6 sm:p-8 shadow-sm dark:border-slate-800 dark:bg-slate-900">
          <AuthForm mode="login" onSubmit={handleLoginSubmit} />
          <p className="mt-6 text-center text-xs text-slate-600 dark:text-slate-400">
            Chưa có tài khoản?{" "}
            <Link
              href="/register"
              className="font-semibold text-sky-600 hover:underline dark:text-sky-400"
            >
              Đăng ký ngay
            </Link>
          </p>
        </div>
      )}
    </main>
  );
}
