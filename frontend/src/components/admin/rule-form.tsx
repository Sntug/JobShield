"use client";

import React, { useState } from "react";
import { useUpdateAdminRule } from "@/hooks/use-admin";
import { RiskIndicator } from "@/types/api";

interface RuleFormProps {
  rule: RiskIndicator;
  onSuccess: () => void;
  onCancel: () => void;
}

export function RuleForm({ rule, onSuccess, onCancel }: RuleFormProps) {
  const updateMutation = useUpdateAdminRule();

  const [weight, setWeight] = useState(rule.weight);
  const [description, setDescription] = useState(rule.description);
  const [enabled, setEnabled] = useState(rule.enabled);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    try {
      await updateMutation.mutateAsync({
        code: rule.code,
        payload: {
          weight: Number(weight),
          description: description.trim() || undefined,
          enabled,
        },
      });
      onSuccess();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Đã có lỗi xảy ra.";
      setErrorMessage(msg);
    }
  };

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
        <span className="block text-xs font-semibold text-slate-500 uppercase">Mã quy tắc</span>
        <span className="font-mono text-sm font-bold text-slate-900">{rule.code}</span>
      </div>

      <div>
        <label htmlFor="rule-name" className="block text-xs font-semibold text-slate-900">
          Tên quy tắc
        </label>
        <p className="text-xs text-slate-700 font-medium mt-0.5">{rule.name}</p>
      </div>

      <div>
        <label htmlFor="rule-weight" className="block text-xs font-semibold text-slate-900">
          Trọng số ưu tiên (1 - 100)
        </label>
        <input
          id="rule-weight"
          type="number"
          min={1}
          max={100}
          value={weight}
          onChange={(e) => setWeight(Number(e.target.value))}
          className="mt-1 block w-24 rounded-lg border border-slate-300 p-2 text-xs text-slate-800 focus:outline-none"
          required
        />
      </div>

      <div>
        <label htmlFor="rule-description" className="block text-xs font-semibold text-slate-900">
          Mô tả dấu hiệu
        </label>
        <textarea
          id="rule-description"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="mt-1 block w-full rounded-lg border border-slate-300 p-2 text-xs text-slate-800 focus:outline-none"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          id="rule-enabled"
          type="checkbox"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="rounded border-slate-300 text-slate-900 focus:ring-0"
        />
        <label htmlFor="rule-enabled" className="text-xs text-slate-800 font-medium">
          Kích hoạt quy tắc phát hiện này
        </label>
      </div>

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
          disabled={updateMutation.isPending}
          className="rounded-lg bg-slate-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {updateMutation.isPending ? "Đang lưu..." : "Lưu thay đổi"}
        </button>
      </div>
    </form>
  );
}
