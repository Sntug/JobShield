"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";

interface AuthFormData {
  email: string;
  password: string;
  full_name?: string;
}

interface AuthFormProps {
  mode: "login" | "register";
  onSubmit: (data: AuthFormData) => Promise<void>;
  onSuccess?: () => void;
}

export function AuthForm({ mode, onSubmit, onSuccess }: AuthFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setError("Vui lòng nhập email.");
      return;
    }

    if (mode === "register") {
      const trimmedName = fullName.trim();
      if (!trimmedName) {
        setError("Vui lòng nhập họ và tên.");
        return;
      }
      if (password.length < 15) {
        setError("Mật khẩu phải có tối thiểu 15 ký tự để bảo đảm an toàn.");
        return;
      }
    } else {
      if (!password) {
        setError("Vui lòng nhập mật khẩu.");
        return;
      }
    }

    setLoading(true);
    try {
      if (mode === "register") {
        await onSubmit({
          email: trimmedEmail,
          password,
          full_name: fullName.trim(),
        });
      } else {
        await onSubmit({
          email: trimmedEmail,
          password,
        });
      }
      if (onSuccess) {
        onSuccess();
      }
    } catch (err: unknown) {
      const e = err as { message?: string };
      setError(e.message || "Đã xảy ra lỗi. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md w-full" noValidate>
      {error && (
        <div
          role="alert"
          className="rounded-md bg-rose-50 border border-rose-200 p-3 text-sm text-rose-800"
        >
          {error}
        </div>
      )}

      {mode === "register" && (
        <div>
          <label
            htmlFor="full_name"
            className="block text-sm font-medium text-slate-700 mb-1"
          >
            Họ và tên
          </label>
          <input
            id="full_name"
            name="full_name"
            type="text"
            required
            disabled={loading}
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 disabled:opacity-50"
            placeholder="Ví dụ: Nguyễn Văn A"
          />
        </div>
      )}

      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-slate-700 mb-1"
        >
          Email
        </label>
        <input
          id="email"
          name="email"
          type="email"
          required
          disabled={loading}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 disabled:opacity-50"
          placeholder="name@example.com"
        />
      </div>

      <div>
        <label
          htmlFor="password"
          className="block text-sm font-medium text-slate-700 mb-1"
        >
          Mật khẩu
        </label>
        <input
          id="password"
          name="password"
          type="password"
          required
          disabled={loading}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900 disabled:opacity-50"
          placeholder={mode === "register" ? "Tối thiểu 15 ký tự" : "Nhập mật khẩu của bạn"}
        />
        {mode === "register" && (
          <p className="mt-1 text-xs text-slate-500">
            Mật khẩu yêu cầu từ 15 đến 128 ký tự theo tiêu chuẩn bảo mật OWASP.
          </p>
        )}
      </div>

      <Button
        type="submit"
        disabled={loading}
        className="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-2 rounded-lg"
      >
        {loading
          ? "Đang xử lý..."
          : mode === "register"
          ? "Đăng ký tài khoản"
          : "Đăng nhập"}
      </Button>
    </form>
  );
}
