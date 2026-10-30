"use client";

import React, { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { extractFromImage, extractFromUrl } from "@/lib/api-client";

export type InputMode = "text" | "image" | "url";

export interface AnalysisOptions {
  use_ai?: boolean;
  ai_consent?: boolean;
}

interface RecruitmentInputFormProps {
  onSubmit: (text: string, options?: AnalysisOptions) => Promise<void>;
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
  const [mode, setMode] = useState<InputMode>("text");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractionError, setExtractionError] = useState<string | null>(null);
  const [extractionSuccess, setExtractionSuccess] = useState<string | null>(null);
  const [useAi, setUseAi] = useState(false);
  const [aiConsent, setAiConsent] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const MAX_CODE_POINTS = 10000;

  // Đếm theo Unicode code points thực tế (Array.from) thay vì UTF-16 code units (text.length)
  const codePointsCount = Array.from(text).length;
  const isOverLimit = codePointsCount > MAX_CODE_POINTS;

  const handleModeChange = (newMode: InputMode) => {
    setMode(newMode);
    setExtractionError(null);
    setExtractionSuccess(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] || null;
    setSelectedFile(file);
    setExtractionError(null);
    setExtractionSuccess(null);
  };

  const handleExtractFromImage = async () => {
    if (!selectedFile || isExtracting || isLoading) return;
    setIsExtracting(true);
    setExtractionError(null);
    setExtractionSuccess(null);

    try {
      const result = await extractFromImage(selectedFile);
      if (result.success && result.text) {
        setText(result.text);
        setExtractionSuccess(
          "Đã trích xuất văn bản từ ảnh thành công. Bạn có thể kiểm tra và chỉnh sửa nội dung bên dưới trước khi phân tích."
        );
      } else {
        setExtractionError(
          result.failure_vi ||
            "Không nhận diện được nội dung văn bản từ ảnh. Vui lòng nhập hoặc dán văn bản thủ công bên dưới."
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể trích xuất văn bản từ ảnh.";
      setExtractionError(msg);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleExtractFromUrl = async () => {
    const cleanUrl = url.trim();
    if (!cleanUrl || isExtracting || isLoading) return;
    setIsExtracting(true);
    setExtractionError(null);
    setExtractionSuccess(null);

    try {
      const result = await extractFromUrl(cleanUrl);
      if (result.success && result.text) {
        setText(result.text);
        setExtractionSuccess(
          "Đã trích xuất nội dung từ liên kết. Bạn có thể kiểm tra và chỉnh sửa nội dung bên dưới trước khi phân tích."
        );
      } else {
        setExtractionError(
          result.failure_vi ||
            "Không lấy được nội dung từ liên kết. Vui lòng nhập hoặc dán văn bản thủ công bên dưới."
        );
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể kết nối hoặc trích xuất từ liên kết.";
      setExtractionError(msg);
    } finally {
      setIsExtracting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || isLoading || isExtracting || isOverLimit) return;
    if (useAi) {
      await onSubmit(text, { use_ai: true, ai_consent: aiConsent });
    } else {
      await onSubmit(text);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-4">
      {/* Input Mode Selector Tabs */}
      <div className="flex flex-col space-y-2">
        <label className="text-sm font-medium text-slate-900 dark:text-slate-100">
          Phương thức nhập tin tuyển dụng
        </label>
        <div
          role="tablist"
          aria-label="Chọn phương thức nhập tin tuyển dụng"
          className="grid grid-cols-3 gap-2 rounded-lg bg-slate-100 p-1 dark:bg-slate-800"
        >
          <button
            type="button"
            role="tab"
            aria-selected={mode === "text"}
            aria-controls="input-panel-text"
            onClick={() => handleModeChange("text")}
            className={`flex items-center justify-center rounded-md px-3 py-2 text-xs sm:text-sm font-medium transition-colors ${
              mode === "text"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-slate-100"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Văn bản
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "image"}
            aria-controls="input-panel-image"
            onClick={() => handleModeChange("image")}
            className={`flex items-center justify-center rounded-md px-3 py-2 text-xs sm:text-sm font-medium transition-colors ${
              mode === "image"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-slate-100"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Hình ảnh / OCR
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "url"}
            aria-controls="input-panel-url"
            onClick={() => handleModeChange("url")}
            className={`flex items-center justify-center rounded-md px-3 py-2 text-xs sm:text-sm font-medium transition-colors ${
              mode === "url"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-900 dark:text-slate-100"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
            }`}
          >
            Liên kết / URL
          </button>
        </div>
      </div>

      {/* Mode Panel: Image / OCR */}
      {mode === "image" && (
        <div
          id="input-panel-image"
          role="tabpanel"
          className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/50 space-y-3"
        >
          <div className="flex flex-col space-y-1">
            <label
              htmlFor="recruitment-image-file"
              className="text-xs sm:text-sm font-medium text-slate-900 dark:text-slate-100"
            >
              Chọn ảnh chụp tin tuyển dụng (PNG, JPEG, WebP, tối đa 5MB)
            </label>
            <p className="text-xs text-slate-500">
              Hệ thống sẽ trích xuất văn bản từ ảnh để bạn kiểm tra và phân tích rủi ro.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <input
              ref={fileInputRef}
              id="recruitment-image-file"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleFileChange}
              disabled={isExtracting || isLoading}
              className="text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 dark:file:bg-blue-900/40 dark:file:text-blue-300"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!selectedFile || isExtracting || isLoading}
              onClick={handleExtractFromImage}
              className="text-xs shrink-0"
            >
              {isExtracting ? "Đang đọc ảnh..." : "Trích xuất văn bản từ ảnh"}
            </Button>
          </div>

          {selectedFile && (
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Đã chọn: <span className="font-medium">{selectedFile.name}</span> (
              {(selectedFile.size / 1024).toFixed(1)} KB)
            </p>
          )}
        </div>
      )}

      {/* Mode Panel: URL */}
      {mode === "url" && (
        <div
          id="input-panel-url"
          role="tabpanel"
          className="rounded-lg border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/50 space-y-3"
        >
          <div className="flex flex-col space-y-1">
            <label
              htmlFor="recruitment-url-input"
              className="text-xs sm:text-sm font-medium text-slate-900 dark:text-slate-100"
            >
              Đường dẫn tin tuyển dụng công khai
            </label>
            <p className="text-xs text-slate-500">
              Chỉ hỗ trợ URL công khai HTTP/HTTPS (không vượt trang yêu cầu đăng nhập hoặc CAPTCHA).
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <input
              id="recruitment-url-input"
              type="text"
              inputMode="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://tuyendung.example/vi-tri-kiem-thu"
              disabled={isExtracting || isLoading}
              className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs sm:text-sm text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={!url.trim() || isExtracting || isLoading}
              onClick={handleExtractFromUrl}
              className="text-xs shrink-0"
            >
              {isExtracting ? "Đang tải nội dung..." : "Lấy nội dung từ liên kết"}
            </Button>
          </div>
        </div>
      )}

      {/* Extraction Alerts */}
      {extractionError && (
        <div
          role="alert"
          className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs sm:text-sm text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200"
        >
          <p className="font-medium">{extractionError}</p>
          <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
            Bạn có thể nhập hoặc dán toàn bộ nội dung tin tuyển dụng vào khung bên dưới để tiếp tục phân tích.
          </p>
        </div>
      )}

      {extractionSuccess && (
        <div
          role="status"
          className="rounded-lg border border-green-200 bg-green-50 p-3 text-xs sm:text-sm text-green-800 dark:border-green-900/50 dark:bg-green-950/30 dark:text-green-300"
        >
          <p className="font-medium">{extractionSuccess}</p>
        </div>
      )}

      {/* Text Editor Area */}
      <div className="flex flex-col space-y-2">
        <div className="flex justify-between items-center">
          <label
            htmlFor="recruitment-text"
            className="text-sm font-medium text-slate-900 dark:text-slate-100"
          >
            Nội dung tin tuyển dụng cần phân tích
          </label>
          <span className="text-xs text-slate-500">
            {mode !== "text" && "(có thể xem lại và chỉnh sửa)"}
          </span>
        </div>
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
            disabled={isLoading || isExtracting}
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

      {/* Tùy chọn phân tích chuyên sâu bằng AI (Layer 2) */}
      <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3.5 dark:border-slate-800 dark:bg-slate-900/60 space-y-2.5">
        <label className="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            type="checkbox"
            name="enable_ai"
            id="enable-ai-checkbox"
            checked={useAi}
            onChange={(e) => {
              setUseAi(e.target.checked);
              if (!e.target.checked) setAiConsent(false);
            }}
            disabled={isLoading || isExtracting}
            className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 dark:border-slate-700 dark:bg-slate-800"
          />
          <div className="flex-1">
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
              Bật hỗ trợ phân tích ngữ nghĩa AI chuyên sâu (Tùy chọn)
            </span>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Sử dụng mô hình ngôn ngữ lớn để làm rõ ngữ cảnh, bẫy tâm lý và cung cấp giải thích chi tiết bằng tiếng Việt.
            </p>
          </div>
        </label>

        {useAi && (
          <div className="rounded-md border border-amber-200 bg-amber-50/70 p-3 dark:border-amber-900/50 dark:bg-amber-950/20 space-y-2 mt-2">
            <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed">
              <strong>Lưu ý quyền riêng tư:</strong> Nội dung tin tuyển dụng sẽ được chuyển tiếp tới nhà cung cấp AI bên ngoài (Google Gemini / LLM) để phân tích. JobShield không chia sẻ danh tính, phiên làm việc hay tài khoản của bạn. Tuyệt đối không dán mật khẩu, số CCCD, mã OTP hoặc tài khoản ngân hàng của bạn.
            </p>
            <label className="flex items-center gap-2 cursor-pointer select-none pt-1">
              <input
                type="checkbox"
                name="ai_consent"
                id="ai-consent-checkbox"
                checked={aiConsent}
                onChange={(e) => setAiConsent(e.target.checked)}
                disabled={isLoading || isExtracting}
                className="h-4 w-4 rounded border-amber-400 text-amber-600 focus:ring-amber-500"
              />
              <span className="text-xs font-medium text-amber-900 dark:text-amber-200">
                Tôi đồng ý gửi nội dung tin tuyển dụng này tới dịch vụ AI để phân tích ngữ nghĩa
              </span>
            </label>
          </div>
        )}
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
        disabled={isLoading || isExtracting || !text.trim() || isOverLimit}
        size="lg"
        className="w-full sm:w-auto"
      >
        {isLoading ? "Đang phân tích..." : "Phân tích tin tuyển dụng"}
      </Button>
    </form>
  );
}
