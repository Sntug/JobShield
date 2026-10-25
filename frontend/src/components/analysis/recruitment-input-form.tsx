"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";

interface RecruitmentInputFormProps {
  onSubmit: (text: string) => Promise<void>;
  isLoading?: boolean;
  error?: string | null;
  onResetSession?: () => void;
  isSessionInvalid?: boolean;
}

export function RecruitmentInputForm({
  onSubmit,
  isLoading = false,
  error = null,
  onResetSession,
  isSessionInvalid = false,
}: RecruitmentInputFormProps) {
  const [text, setText] = useState("");
  const MAX_CODE_POINTS = 10000;

  // Đếm theo Unicode code points thực tế (Array.from) thay vì UTF-16 code units (text.length)
  const codePointsCount = Array.from(text).length;
  const isOverLimit = codePointsCount > MAX_CODE_POINTS;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isLoading || isOverLimit) return;
    await onSubmit(text);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      <div className="flex flex-col space-y-2">
        <label
          htmlFor="recruitment-text"
          className="text-sm font-medium text-slate-900 dark:text-slate-100"
        >
          Nội dung tin tuyển dụng
        </label>
        <div className="relative">
          <textarea
            id="recruitment-text"
            rows={8}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Dán toàn bộ văn bản tin tuyển dụng cần kiểm tra vào đây (tối đa 10.000 ký tự)..."
            className={`w-full rounded-lg border p-3 text-sm shadow-sm focus:outline-none focus:ring-1 ${
              isOverLimit
                ? "border-red-500 focus:border-red-500 focus:ring-red-500"
                : "border-slate-300 bg-white text-slate-900 focus:border-blue-500 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            }`}
            disabled={isLoading}
          />
          <div className="mt-1 flex justify-between text-xs text-slate-500">
            <span>Không chia sẻ mật khẩu, OTP hoặc thông tin bảo mật</span>
            <span className={isOverLimit ? "font-semibold text-red-500" : ""}>
              {codePointsCount.toLocaleString("vi-VN")} / {MAX_CODE_POINTS.toLocaleString("vi-VN")} ký tự
            </span>
          </div>
          {isOverLimit && (
            <p className="mt-1 text-xs text-red-500">
              Văn bản vượt quá giới hạn {MAX_CODE_POINTS.toLocaleString("vi-VN")} ký tự. Vui lòng rút gọn trước khi gửi.
            </p>
          )}
        </div>
      </div>

      {error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300"
        >
          <p className="font-medium">{error}</p>
          {isSessionInvalid && onResetSession && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onResetSession}
              className="mt-2 text-xs"
            >
              Làm mới phiên và thử lại
            </Button>
          )}
        </div>
      )}

      <Button
        type="submit"
        disabled={isLoading || !text.trim() || isOverLimit}
        size="lg"
        className="w-full sm:w-auto"
      >
        {isLoading ? "Đang phân tích..." : "Phân tích tin tuyển dụng"}
      </Button>
    </form>
  );
}
