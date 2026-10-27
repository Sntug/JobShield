"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/auth/auth-form";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";

export default function LoginPage() {
  const { user, loading, login, hasGuestSession, claimGuest, dismissGuestClaim } = useAuth();
  const router = useRouter();
  const [showClaimPrompt, setShowClaimPrompt] = useState(false);
  const [claimMessage, setClaimMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user && !hasGuestSession) {
      router.push("/dashboard");
    }
  }, [user, loading, hasGuestSession, router]);

  const handleLoginSubmit = async (data: { email: string; password: string }) => {
    await login(data.email, data.password);
    if (hasGuestSession) {
      setShowClaimPrompt(true);
    } else {
      router.push("/dashboard");
    }
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
    <main className="mx-auto max-w-md px-6 py-16">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">
          Đăng nhập JobShield
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Quản lý lịch sử phân tích, lưu trữ cảnh báo và bảo vệ thông tin ứng tuyển.
        </p>
      </div>

      {showClaimPrompt ? (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-6 shadow-sm text-left space-y-4">
          <h2 className="text-lg font-semibold text-blue-900">
            Tìm thấy kết quả phân tích phiên khách
          </h2>
          <p className="text-sm text-blue-800">
            Bạn có kết quả phân tích trong phiên làm việc vừa rồi. Bạn có muốn lưu các kết quả này vào tài khoản của mình không?
          </p>
          {claimMessage ? (
            <p className="text-sm font-medium text-emerald-800">{claimMessage}</p>
          ) : (
            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                onClick={handleClaim}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                Nhận vào tài khoản
              </Button>
              <Button
                type="button"
                onClick={handleSkipClaim}
                className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
              >
                Bỏ qua
              </Button>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white p-8 border border-slate-200 rounded-xl shadow-sm">
          <AuthForm mode="login" onSubmit={handleLoginSubmit} />
          <p className="mt-6 text-center text-sm text-slate-600">
            Chưa có tài khoản?{" "}
            <Link
              href="/register"
              className="font-medium text-slate-900 hover:underline"
            >
              Đăng ký ngay
            </Link>
          </p>
        </div>
      )}
    </main>
  );
}
