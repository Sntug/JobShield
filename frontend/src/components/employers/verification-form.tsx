"use client";

import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { VerificationCreate } from "@/types/api";
import { verificationFormSchema, VerificationFormValues, verificationPayload } from "@/lib/validations";

const primaryFields = [
  { name: "company_name", label: "Tên công ty", placeholder: "Tên doanh nghiệp trong tin tuyển dụng" },
  { name: "tax_id", label: "Mã số thuế", placeholder: "10 hoặc 13 chữ số" },
  { name: "contact_email", label: "Email liên hệ", placeholder: "Email nhà tuyển dụng đã sử dụng", type: "email" },
  { name: "recruitment_website", label: "Website tuyển dụng", placeholder: "https://…", type: "url" },
  { name: "social_channel_url", label: "Link Telegram, Zalo hoặc Facebook", placeholder: "Link đầy đủ đến trang hoặc kênh cụ thể", type: "url" },
] as const;
const bankFields = [{ name: "bank_name", label: "Ngân hàng" }, { name: "account_number", label: "Số tài khoản" }, { name: "account_holder", label: "Chủ tài khoản" }] as const;

export function VerificationForm({ onSubmit, isLoading = false, error = null }: {
  onSubmit: (payload: VerificationCreate) => Promise<void>; isLoading?: boolean; error?: string | null;
}) {
  const { register, handleSubmit, formState: { isSubmitting } } = useForm<VerificationFormValues>({
    defaultValues: { company_name: "", tax_id: "", contact_email: "", recruitment_website: "", social_channel_url: "", account_number: "", bank_name: "", account_holder: "" },
  });
  const [issues, setIssues] = useState<Array<{ field: string; message: string }>>([]);
  const summary = useRef<HTMLDivElement>(null);
  const bank = useRef<HTMLDetailsElement>(null);
  const busy = isLoading || isSubmitting;
  useEffect(() => {
    if (issues.length || error) summary.current?.focus();
    if (issues.some(issue => ["account_number", "bank_name", "account_holder"].includes(issue.field)) && bank.current) bank.current.open = true;
  }, [issues, error]);
  const submit = handleSubmit(async values => {
    const parsed = verificationFormSchema.safeParse(values);
    if (!parsed.success) {
      setIssues(parsed.error.issues.map(issue => ({ field: String(issue.path[0] || ""), message: issue.message })));
      return;
    }
    setIssues([]);
    await onSubmit(verificationPayload(parsed.data));
  });
  const inputClasses = "min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 outline-none focus-visible:ring-2 focus-visible:ring-blue-600 disabled:opacity-60 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100";
  return (
    <form onSubmit={submit} noValidate autoComplete="off" className="space-y-6">
      <p id="verification-help" className="text-base text-slate-600 dark:text-slate-300">Nhập ít nhất một thông tin bạn có. Tên công ty đơn lẻ chưa đủ xác minh; không cần điền tất cả các trường.</p>
      {(issues.length > 0 || error) && (
        <div role="alert" tabIndex={-1} ref={summary} className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-900 outline-none focus-visible:ring-2 focus-visible:ring-red-600 dark:bg-red-950 dark:text-red-200">
          {error && <p>{error}</p>}
          {issues.length > 0 && <ul className="list-disc space-y-1 pl-5">{issues.map((issue, index) => <li key={index}>{issue.field ? <a href={`#verify-${issue.field}`} className="underline">{issue.message}</a> : issue.message}</li>)}</ul>}
        </div>
      )}
      <fieldset disabled={busy} aria-describedby="verification-help" className="grid gap-5 sm:grid-cols-2">
        <legend className="sr-only">Thông tin doanh nghiệp và kênh liên hệ</legend>
        {primaryFields.map(field => {
          const issue = issues.find(issue => issue.field === field.name);
          return <div key={field.name} className={field.name === "social_channel_url" ? "sm:col-span-2" : ""}>
            <label htmlFor={`verify-${field.name}`} className="mb-2 block font-medium">{field.label}</label>
            <input {...register(field.name)} id={`verify-${field.name}`} type={"type" in field ? field.type : "text"} placeholder={field.placeholder} className={inputClasses} aria-invalid={!!issue} aria-describedby={issue ? `error-${field.name}` : undefined} />
            {issue && <p id={`error-${field.name}`} className="mt-1 text-sm text-red-700 dark:text-red-300">{issue.message}</p>}
          </div>;
        })}
      </fieldset>
      <details ref={bank} className="rounded-lg border border-slate-200 p-4 dark:border-slate-700">
        <summary className="cursor-pointer py-1 font-medium focus-visible:outline-2 focus-visible:outline-blue-600">Tài khoản ngân hàng (tùy chọn)</summary>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">Chỉ nhập khi cần đối chiếu. Dữ liệu tra cứu không được lưu thành lịch sử. Không nhập mật khẩu, OTP hoặc thông tin đăng nhập ngân hàng.</p>
        <fieldset disabled={busy} className="mt-4 grid gap-4 sm:grid-cols-2">
          <legend className="sr-only">Thông tin tài khoản cần đối chiếu</legend>
          {bankFields.map(field => <div key={field.name} className={field.name === "account_holder" ? "sm:col-span-2" : ""}>
            <label htmlFor={`verify-${field.name}`} className="mb-2 block font-medium">{field.label}</label>
            <input {...register(field.name)} id={`verify-${field.name}`} className={inputClasses} aria-invalid={issues.some(issue => issue.field === field.name)} />
          </div>)}
        </fieldset>
      </details>
      <Button type="submit" disabled={busy} size="lg" className="min-h-11 w-full sm:w-auto">{busy ? "Đang đối chiếu…" : "Đối chiếu thông tin"}</Button>
      <p className="text-sm text-slate-600 dark:text-slate-300">Kết quả dựa trên nguồn đã được quản trị kiểm chứng. Khớp nguồn không bảo đảm tin tuyển dụng thật hoặc an toàn.</p>
    </form>
  );
}
