"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { BatchAnalysisCreate, BatchItemInput } from "@/types/api";
import {
  AlertCircle,
  FileText,
  Layers,
  Link2,
  Lock,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";

export type BatchInputMode = "urls" | "content" | "mixed";

export interface BatchRecruitmentFormProps {
  onSubmit: (payload: BatchAnalysisCreate) => Promise<unknown>;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => Promise<void> | void;
  initialItem?: BatchItemInput;
  submitLabel?: string;
}

const MAX_UNICODE_CHARS = 10000;
const MAX_ITEMS = 10;

function getUnicodeLength(str: string): number {
  return Array.from(str).length;
}

function isValidHttpUrl(str: string): boolean {
  try {
    const parsed = new URL(str);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function BatchRecruitmentForm({
  onSubmit,
  isLoading = false,
  error = null,
  onRetry,
  initialItem,
  submitLabel = "Kiểm tra tất cả",
}: BatchRecruitmentFormProps) {
  const [mode, setMode] = useState<BatchInputMode>(() =>
    initialItem?.type === "text" ? "content" : "urls"
  );
  const [urlRawText, setUrlRawText] = useState(
    initialItem?.type === "url" ? initialItem.value : ""
  );
  const [contentBoxes, setContentBoxes] = useState<string[]>([
    initialItem?.type === "text" ? initialItem.value : "",
    "",
  ]);
  const [useAi, setUseAi] = useState(false);
  const [aiConsent, setAiConsent] = useState(false);

  // Parsing & validating URLs mode
  const urlLines = urlRawText.split(/\r?\n/);
  const parsedUrlItems = urlLines
    .map((line, originalIndex) => ({
      value: line.trim(),
      originalIndex: originalIndex + 1,
    }))
    .filter((item) => item.value.length > 0);

  const urlErrors: string[] = [];
  parsedUrlItems.forEach((item) => {
    const len = getUnicodeLength(item.value);
    if (len > MAX_UNICODE_CHARS) {
      urlErrors.push(
        `Dòng ${item.originalIndex}: Vượt quá giới hạn ${MAX_UNICODE_CHARS.toLocaleString("vi-VN")} ký tự.`
      );
    }
    if (!isValidHttpUrl(item.value)) {
      urlErrors.push(
        `Dòng ${item.originalIndex}: "${item.value.slice(0, 40)}${item.value.length > 40 ? "..." : ""}" không phải URL http(s) hợp lệ.`
      );
    }
  });

  // Parsing & validating Content mode
  const parsedContentItems = contentBoxes
    .map((text, originalIndex) => ({
      raw: text,
      trimmed: text.trim(),
      originalIndex: originalIndex + 1,
    }))
    .filter((item) => item.trimmed.length > 0);

  const contentBoxErrors: Record<number, string> = {};
  contentBoxes.forEach((box, idx) => {
    const len = getUnicodeLength(box);
    if (len > MAX_UNICODE_CHARS) {
      contentBoxErrors[idx] = `Vượt quá giới hạn ${MAX_UNICODE_CHARS.toLocaleString("vi-VN")} ký tự (${len.toLocaleString("vi-VN")} ký tự).`;
    }
  });

  const hasContentErrors = Object.keys(contentBoxErrors).length > 0;
  const hasUrlInput = mode !== "content";
  const hasContentInput = mode !== "urls";
  const totalItemCount =
    (hasUrlInput ? parsedUrlItems.length : 0) +
    (hasContentInput ? parsedContentItems.length : 0);
  const itemCountError =
    totalItemCount > MAX_ITEMS
      ? `Tối đa ${MAX_ITEMS} tin tuyển dụng cho mỗi lượt (hiện có ${totalItemCount} tin).`
      : null;
  const isValid =
    totalItemCount >= 1 &&
    !itemCountError &&
    (!hasUrlInput || urlErrors.length === 0) &&
    (!hasContentInput || !hasContentErrors);

  const handleAddContentBox = () => {
    if (contentBoxes.length >= MAX_ITEMS || totalItemCount >= MAX_ITEMS) return;
    setContentBoxes([...contentBoxes, ""]);
  };

  const handleRemoveContentBox = (index: number) => {
    if (contentBoxes.length <= 1) return;
    setContentBoxes(contentBoxes.filter((_, idx) => idx !== index));
  };

  const handleContentBoxChange = (index: number, val: string) => {
    const next = [...contentBoxes];
    next[index] = val;
    setContentBoxes(next);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || isLoading) return;

    const items: BatchItemInput[] = [
      ...(hasUrlInput
        ? parsedUrlItems.map((item) => ({
            type: "url" as const,
            value: item.value,
          }))
        : []),
      ...(hasContentInput
        ? parsedContentItems.map((item) => ({
            type: "text" as const,
            value: item.trimmed,
          }))
        : []),
    ];

    const payload: BatchAnalysisCreate = {
      items,
      use_ai: useAi,
      ai_consent: useAi ? aiConsent : false,
    };

    await onSubmit(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-6">
      {/* Mode Selector Tabs */}
      <div className="flex flex-col space-y-2">
        <label className="text-sm font-semibold text-slate-900 dark:text-slate-100">
          Phương thức nhập theo lô
        </label>
        <div
          role="tablist"
          aria-label="Chọn phương thức nhập theo lô"
          className="grid grid-cols-3 gap-1.5 rounded-xl bg-slate-100 p-1.5 dark:bg-slate-800/80 max-w-xl"
        >
          <button
            type="button"
            role="tab"
            aria-selected={mode === "urls"}
            aria-controls="batch-panel-urls"
            onClick={() => setMode("urls")}
            className={`flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
              mode === "urls"
                ? "bg-white text-slate-900 shadow-sm font-semibold dark:bg-slate-900 dark:text-slate-100"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Link2 className="size-4 shrink-0 opacity-70" />
            <span>Liên kết (URLs)</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "content"}
            aria-controls="batch-panel-content"
            onClick={() => setMode("content")}
            className={`flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
              mode === "content"
                ? "bg-white text-slate-900 shadow-sm font-semibold dark:bg-slate-900 dark:text-slate-100"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <FileText className="size-4 shrink-0 opacity-70" />
            <span>Nội dung (Văn bản)</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "mixed"}
            aria-controls="batch-panel-urls batch-panel-content"
            onClick={() => setMode("mixed")}
            className={`flex items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs sm:text-sm font-medium transition-all ${
              mode === "mixed"
                ? "bg-white text-slate-900 shadow-sm font-semibold dark:bg-slate-900 dark:text-slate-100"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            <Layers className="size-4 shrink-0 opacity-70" />
            <span>Kết hợp</span>
          </button>
        </div>
      </div>

      {itemCountError && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300">
          {itemCountError}
        </div>
      )}
      {mode === "mixed" && (
        <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">
          Đã nhận diện: {totalItemCount}/{MAX_ITEMS} tin
        </p>
      )}

      {/* Mode Panel: URLs */}
      {hasUrlInput && (
        <div id="batch-panel-urls" role="tabpanel" className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <label
                htmlFor="batch-urls-input"
                className="text-sm font-semibold text-slate-900 dark:text-slate-100"
              >
                Danh sách liên kết tuyển dụng (1 - 10 liên kết)
              </label>
              <p className="text-xs text-slate-500 mt-0.5">
                Dán các đường dẫn HTTP/HTTPS công khai, mỗi đường dẫn trên một dòng riêng.
              </p>
            </div>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                parsedUrlItems.length > MAX_ITEMS
                  ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                  : parsedUrlItems.length > 0
                  ? "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
              }`}
            >
              Đã nhận diện: {parsedUrlItems.length}/{MAX_ITEMS} liên kết
            </span>
          </div>

          <textarea
            id="batch-urls-input"
            rows={7}
            value={urlRawText}
            onChange={(e) => setUrlRawText(e.target.value)}
            placeholder="https://tuyendung.example/job-1&#10;https://tuyendung.example/job-2&#10;https://tuyendung.example/job-3"
            disabled={isLoading}
            className={`w-full font-mono text-xs sm:text-sm rounded-xl border p-4 leading-relaxed shadow-sm transition-all focus:outline-none focus:ring-2 ${
              urlErrors.length > 0
                ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                : "border-slate-300 bg-white text-slate-900 focus:border-sky-500 focus:ring-sky-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            }`}
          />

          {urlErrors.length > 0 && (
            <div
              role="alert"
              className="rounded-xl border border-red-200 bg-red-50 p-4 text-xs sm:text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300 space-y-1"
            >
              <div className="flex items-center gap-2 font-semibold">
                <AlertCircle className="size-4 shrink-0 text-red-600" />
                <span>Vui lòng kiểm tra lại danh sách liên kết:</span>
              </div>
              <ul className="list-disc pl-6 space-y-0.5 pt-1">
                {urlErrors.slice(0, 5).map((err, idx) => (
                  <li key={idx}>{err}</li>
                ))}
                {urlErrors.length > 5 && (
                  <li>Và thêm {urlErrors.length - 5} lỗi khác...</li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Mode Panel: Content Boxes */}
      {hasContentInput && (
        <div id="batch-panel-content" role="tabpanel" className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <label className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Nội dung các tin tuyển dụng (1 - 10 tin)
              </label>
              <p className="text-xs text-slate-500 mt-0.5">
                Các ô để trống sẽ tự động được bỏ qua và giữ nguyên thứ tự các tin có nội dung.
              </p>
            </div>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                parsedContentItems.length > MAX_ITEMS
                  ? "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
                  : parsedContentItems.length > 0
                  ? "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
              }`}
            >
              Đã nhập: {parsedContentItems.length}/{MAX_ITEMS} tin
            </span>
          </div>

          <div className="space-y-4">
            {contentBoxes.map((box, idx) => {
              const codePoints = getUnicodeLength(box);
              const isOverLimit = codePoints > MAX_UNICODE_CHARS;
              const hasError = !!contentBoxErrors[idx];

              return (
                <div
                  key={idx}
                  className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 dark:border-slate-800 dark:bg-slate-900/40 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      Tin #{idx + 1}
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs ${
                          isOverLimit
                            ? "font-semibold text-red-600"
                            : "text-slate-500"
                        }`}
                      >
                        {codePoints.toLocaleString("vi-VN")} /{" "}
                        {MAX_UNICODE_CHARS.toLocaleString("vi-VN")} ký tự
                      </span>
                      {contentBoxes.length > 1 && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveContentBox(idx)}
                          disabled={isLoading}
                          aria-label={`Xóa tin #${idx + 1}`}
                          className="h-7 px-2 text-xs text-slate-400 hover:text-red-600 dark:hover:text-red-400"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      )}
                    </div>
                  </div>

                  <textarea
                    rows={4}
                    value={box}
                    onChange={(e) => handleContentBoxChange(idx, e.target.value)}
                    placeholder={`Dán nội dung tin tuyển dụng #${idx + 1} vào đây...`}
                    disabled={isLoading}
                    className={`w-full rounded-lg border p-3 text-xs sm:text-sm leading-relaxed shadow-sm transition-all focus:outline-none focus:ring-2 ${
                      hasError
                        ? "border-red-400 focus:border-red-500 focus:ring-red-500/20"
                        : "border-slate-300 bg-white text-slate-900 focus:border-sky-500 focus:ring-sky-500/20 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
                    }`}
                  />

                  {hasError && (
                    <p className="text-xs font-semibold text-red-600">
                      {contentBoxErrors[idx]}
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          {contentBoxes.length < MAX_ITEMS && totalItemCount < MAX_ITEMS && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddContentBox}
              disabled={isLoading || contentBoxes.length >= MAX_ITEMS}
              className="text-xs font-medium"
            >
              <Plus className="size-3.5 mr-1.5" />
              Thêm tin tuyển dụng ({contentBoxes.length}/{MAX_ITEMS})
            </Button>
          )}
        </div>
      )}

      {/* AI Consent Toggle */}
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-900/60 space-y-3">
        <label className="flex items-start gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            name="enable_ai_batch"
            id="batch-enable-ai-checkbox"
            checked={useAi}
            onChange={(e) => {
              setUseAi(e.target.checked);
              if (!e.target.checked) setAiConsent(false);
            }}
            disabled={isLoading}
            className="mt-1 size-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500 dark:border-slate-700 dark:bg-slate-800"
          />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Bật hỗ trợ phân tích ngữ nghĩa AI chuyên sâu (Tùy chọn)
              </span>
              <span className="rounded-full bg-sky-100 px-2 py-0.5 text-[10px] font-bold text-sky-800 dark:bg-sky-950 dark:text-sky-300">
                Gemini AI
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
              Sử dụng mô hình ngôn ngữ lớn để làm rõ ngữ cảnh, bẫy tâm lý và cung cấp giải thích chi tiết cho từng tin trong lô.
            </p>
          </div>
        </label>

        {useAi && (
          <div className="rounded-lg border border-amber-200 bg-amber-50/80 p-3.5 dark:border-amber-900/50 dark:bg-amber-950/20 space-y-2 mt-2">
            <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
              <strong>Lưu ý quyền riêng tư:</strong> Nội dung các tin tuyển dụng sẽ được chuyển tiếp tới nhà cung cấp AI bên ngoài (Google Gemini / LLM) để phân tích. JobShield không chia sẻ danh tính, phiên làm việc hay tài khoản của bạn. Tuyệt đối không dán mật khẩu, số CCCD, mã OTP hoặc tài khoản ngân hàng.
            </p>
            <label className="flex items-center gap-2.5 cursor-pointer select-none pt-1">
              <input
                type="checkbox"
                name="ai_consent_batch"
                id="batch-ai-consent-checkbox"
                checked={aiConsent}
                onChange={(e) => setAiConsent(e.target.checked)}
                disabled={isLoading}
                className="size-4 rounded border-amber-400 text-amber-600 focus:ring-amber-500"
              />
              <span className="text-xs font-semibold text-amber-950 dark:text-amber-200">
                Tôi đồng ý gửi nội dung các tin tuyển dụng này tới dịch vụ AI để phân tích ngữ nghĩa
              </span>
            </label>
          </div>
        )}
      </div>

      {/* Global Error Banner */}
      {error && (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300 flex items-start gap-2.5"
        >
          <AlertCircle className="size-5 shrink-0 text-red-600 mt-0.5" />
          <div className="flex flex-1 flex-wrap items-center justify-between gap-3">
            <p className="font-semibold">{error}</p>
            {onRetry && (
              <Button type="button" variant="outline" size="sm" onClick={onRetry}>
                Thử tải lại
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Footer / Submit Button */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
        <Button
          type="submit"
          disabled={isLoading || !isValid}
          size="lg"
          className="min-h-11 px-6 font-semibold bg-gradient-to-r from-sky-600 to-blue-700 text-white shadow-md shadow-sky-600/25 hover:from-sky-500 hover:to-blue-600 disabled:opacity-50"
        >
          <Sparkles className="size-4 mr-2" />
          {isLoading ? "Đang gửi yêu cầu..." : submitLabel}
        </Button>

        <span className="flex items-center gap-1.5 text-xs text-slate-400 select-none">
          <Lock className="size-3.5" />
          Không chia sẻ mật khẩu, OTP hoặc CCCD cá nhân
        </span>
      </div>
    </form>
  );
}
