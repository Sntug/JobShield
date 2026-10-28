"use client";

import React, { useState } from "react";
import { useCreateAdminEmployer, useUpdateAdminEmployer } from "@/hooks/use-admin";
import { EmployerAdmin } from "@/types/api";

interface EmployerFormProps {
  initialEmployer?: EmployerAdmin | null;
  onSuccess: () => void;
  onCancel: () => void;
}

export function EmployerForm({
  initialEmployer,
  onSuccess,
  onCancel,
}: EmployerFormProps) {
  const createMutation = useCreateAdminEmployer();
  const updateMutation = useUpdateAdminEmployer();

  const [legalName, setLegalName] = useState(initialEmployer?.legal_name || "");
  const [taxId, setTaxId] = useState(initialEmployer?.tax_id || "");
  const [isActive, setIsActive] = useState(
    initialEmployer ? initialEmployer.is_active : true
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedName = legalName.trim();
    if (!trimmedName) {
      setErrorMessage("Tên doanh nghiệp không được để trống.");
      return;
    }

    const trimmedTax = taxId.trim();
    if (trimmedTax && trimmedTax.length !== 10 && trimmedTax.length !== 13) {
      setErrorMessage("Mã số thuế phải gồm đúng 10 hoặc 13 chữ số.");
      return;
    }

    try {
      if (initialEmployer) {
        await updateMutation.mutateAsync({
          employerId: initialEmployer.id,
          payload: {
            legal_name: trimmedName,
            tax_id: trimmedTax || null,
            is_active: isActive,
          },
        });
      } else {
        await createMutation.mutateAsync({
          legal_name: trimmedName,
          tax_id: trimmedTax || undefined,
        });
      }
      onSuccess();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra.";
      setErrorMessage(msg);
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {errorMessage && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800"
        >
          {errorMessage}
        </div>
      )}

      <div>
        <label htmlFor="employer-legal-name" className="block text-xs font-semibold text-slate-900">
          Tên pháp lý doanh nghiệp <span className="text-rose-500">*</span>
        </label>
        <input
          id="employer-legal-name"
          type="text"
          value={legalName}
          onChange={(e) => setLegalName(e.target.value)}
          placeholder="Ví dụ: Công ty Cổ phần FPT"
          className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-800 focus:outline-none"
          required
        />
      </div>

      <div>
        <label htmlFor="employer-tax-id" className="block text-xs font-semibold text-slate-900">
          Mã số thuế (10 hoặc 13 chữ số)
        </label>
        <input
          id="employer-tax-id"
          type="text"
          value={taxId}
          onChange={(e) => setTaxId(e.target.value)}
          placeholder="Ví dụ: 0101248141"
          className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-800 focus:outline-none"
        />
      </div>

      {initialEmployer && (
        <div className="flex items-center gap-2">
          <input
            id="employer-is-active"
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="rounded border-slate-300 text-slate-900 focus:ring-0"
          />
          <label htmlFor="employer-is-active" className="text-xs text-slate-800 font-medium">
            Kích hoạt sử dụng trong kho xác minh
          </label>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          Hủy
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {isPending ? "Đang lưu..." : initialEmployer ? "Cập nhật" : "Thêm mới"}
        </button>
      </div>
    </form>
  );
}
