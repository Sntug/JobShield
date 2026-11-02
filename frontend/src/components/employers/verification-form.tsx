"use client";

import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { VerificationCreate } from "@/types/api";
import { verificationFormSchema, VerificationFormValues, verificationPayload } from "@/lib/validations";
import { Building2, Hash, Mail, Globe, MessageSquare, CreditCard, AlertCircle, Sparkles } from "lucide-react";

const primaryFields = [
  { name: "company_name", label: "Tên công ty", placeholder: "Tên doanh nghiệp trong tin tuyển dụng", icon: Building2 },
  { name: "tax_id", label: "Mã số thuế", placeholder: "10 hoặc 13 chữ số", icon: Hash },
  { name: "contact_email", label: "Email liên hệ", placeholder: "Email nhà tuyển dụng đã sử dụng", type: "email", icon: Mail },
  { name: "recruitment_website", label: "Website tuyển dụng", placeholder: "https://…", type: "url", icon: Globe },
  { name: "social_channel_url", label: "Link Telegram, Zalo hoặc Facebook", placeholder: "Link đầy đủ đến trang hoặc kênh cụ thể", type: "url", icon: MessageSquare },
] as const;

const bankFields = [
  { name: "bank_name", label: "Ngân hàng" },
  { name: "account_number", label: "Số tài khoản" },
  { name: "account_holder", label: "Chủ tài khoản" }
] as const;

export function VerificationForm({
  onSubmit,
  initialCompany = "",
  isLoading = false,
  error = null,
}: {
  onSubmit: (payload: VerificationCreate) => Promise<void>;
  initialCompany?: string;
  isLoading?: boolean;
  error?: string | null;
}) {
  const { register, handleSubmit, setValue, formState: { isSubmitting } } = useForm<VerificationFormValues>({
    defaultValues: {
      company_name: initialCompany,
      tax_id: "",
      contact_email: "",
      recruitment_website: "",
      social_channel_url: "",
      account_number: "",
      bank_name: "",
      account_holder: "",
    },
  });

  const [issues, setIssues] = useState<Array<{ field: string; message: string }>>([]);
  const summary = useRef<HTMLDivElement>(null);
  const bank = useRef<HTMLDetailsElement>(null);
  const busy = isLoading || isSubmitting;

  useEffect(() => {
    if (issues.length || error) summary.current?.focus();
    if (
      issues.some((issue) =>
        ["account_number", "bank_name", "account_holder"].includes(issue.field)
      ) &&
      bank.current
    ) {
      bank.current.open = true;
    }
  }, [issues, error]);

  const submit = handleSubmit(async (values) => {
    const parsed = verificationFormSchema.safeParse(values);
    if (!parsed.success) {
      setIssues(
        parsed.error.issues.map((issue) => ({
          field: String(issue.path[0] || ""),
          message: issue.message,
        }))
      );
      return;
    }
    setIssues([]);
    await onSubmit(verificationPayload(parsed.data));
  });

  const handleFillSample = () => {
    setValue("company_name", "Công ty Cổ phần Công nghệ An Toàn");
    setValue("tax_id", "0101234567");
    setValue("contact_email", "tuyendung@antoan.example.vn");
    setValue("recruitment_website", "https://antoan.example.vn");
  };

  const inputClasses =
    "min-h-11 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-base text-slate-900 shadow-sm transition-all outline-none focus:border-sky-500 focus-visible:ring-2 focus-visible:ring-sky-500/20 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100";

  return (
    <form onSubmit={submit} noValidate autoComplete="off" className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <p id="verification-help" className="text-base text-slate-600 dark:text-slate-300">
          Nhập ít nhất một thông tin bạn có. Tên công ty đơn lẻ chưa đủ xác minh; không cần điền tất cả các trường.
        </p>
        <button
          type="button"
          onClick={handleFillSample}
          disabled={busy}
          className="inline-flex items-center gap-1.5 self-start sm:self-auto rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-sky-50 hover:text-sky-800 hover:border-sky-200 dark:border-slate-800 dark:bg-slate-800 dark:text-slate-300 transition-colors shrink-0"
        >
          <Sparkles className="size-3.5 text-sky-600" />
          <span>Điền thông tin mẫu để thử</span>
        </button>
      </div>

      {(issues.length > 0 || error) && (
        <div
          role="alert"
          tabIndex={-1}
          ref={summary}
          className="rounded-xl border border-red-300 bg-red-50 p-4 text-red-900 outline-none focus-visible:ring-2 focus-visible:ring-red-600 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-200"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="size-5 text-red-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              {error && <p className="font-semibold">{error}</p>}
              {issues.length > 0 && (
                <ul className="list-disc space-y-1 pl-4 text-sm">
                  {issues.map((issue, index) => (
                    <li key={index}>
                      {issue.field ? (
                        <a href={`#verify-${issue.field}`} className="underline font-medium">
                          {issue.message}
                        </a>
                      ) : (
                        issue.message
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      <fieldset
        disabled={busy}
        aria-describedby="verification-help"
        className="grid gap-5 sm:grid-cols-2"
      >
        <legend className="sr-only">Thông tin doanh nghiệp và kênh liên hệ</legend>
        {primaryFields.map((field) => {
          const issue = issues.find((issue) => issue.field === field.name);
          const Icon = field.icon;
          return (
            <div
              key={field.name}
              className={field.name === "social_channel_url" ? "sm:col-span-2" : ""}
            >
              <label
                htmlFor={`verify-${field.name}`}
                className="mb-2 flex items-center gap-1.5 font-semibold text-slate-900 dark:text-slate-100 text-sm"
              >
                <Icon className="size-4 text-slate-500" />
                <span>{field.label}</span>
              </label>
              <input
                {...register(field.name)}
                id={`verify-${field.name}`}
                type={"type" in field ? field.type : "text"}
                placeholder={field.placeholder}
                className={inputClasses}
                aria-invalid={!!issue}
                aria-describedby={issue ? `error-${field.name}` : undefined}
              />
              {issue && (
                <p id={`error-${field.name}`} className="mt-1.5 text-xs font-semibold text-red-700 dark:text-red-300">
                  {issue.message}
                </p>
              )}
            </div>
          );
        })}
      </fieldset>

      <details
        ref={bank}
        className="rounded-xl border border-slate-200 bg-slate-50/50 p-4 transition-colors dark:border-slate-800 dark:bg-slate-900/40"
      >
        <summary className="cursor-pointer py-1 font-semibold text-slate-900 dark:text-slate-100 focus-visible:outline-2 focus-visible:outline-sky-600 flex items-center gap-2">
          <CreditCard className="size-4 text-sky-600" />
          <span>Tài khoản ngân hàng (tùy chọn)</span>
        </summary>
        <p className="mt-2 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
          Chỉ nhập khi cần đối chiếu. Dữ liệu tra cứu không được lưu thành lịch sử. Không nhập mật khẩu, OTP hoặc thông tin đăng nhập ngân hàng.
        </p>
        <fieldset disabled={busy} className="mt-4 grid gap-4 sm:grid-cols-2">
          <legend className="sr-only">Thông tin tài khoản cần đối chiếu</legend>
          {bankFields.map((field) => (
            <div
              key={field.name}
              className={field.name === "account_holder" ? "sm:col-span-2" : ""}
            >
              <label
                htmlFor={`verify-${field.name}`}
                className="mb-1.5 block text-xs font-semibold text-slate-900 dark:text-slate-100"
              >
                {field.label}
              </label>
              <input
                {...register(field.name)}
                id={`verify-${field.name}`}
                className={inputClasses}
                aria-invalid={issues.some((issue) => issue.field === field.name)}
              />
            </div>
          ))}
        </fieldset>
      </details>

      <Button
        type="submit"
        disabled={busy}
        size="lg"
        className="min-h-11 w-full sm:w-auto px-6 font-semibold bg-gradient-to-r from-sky-600 to-blue-700 text-white shadow-md shadow-sky-600/25 hover:from-sky-500 hover:to-blue-600 disabled:opacity-50"
      >
        {busy ? "Đang đối chiếu…" : "Đối chiếu thông tin"}
      </Button>

      <p className="text-xs text-slate-500 dark:text-slate-400">
        Kết quả dựa trên nguồn đã được quản trị kiểm chứng. Khớp nguồn không bảo đảm tin tuyển dụng thật hoặc an toàn.
      </p>
    </form>
  );
}
