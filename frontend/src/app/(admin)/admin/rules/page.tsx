"use client";

import React, { useState } from "react";
import { useAdminRules, useUpdateAdminRule } from "@/hooks/use-admin";
import { RuleForm } from "@/components/admin/rule-form";
import { RiskIndicator } from "@/types/api";

export default function AdminRulesPage() {
  const { data, isLoading, isError, error, refetch } = useAdminRules();
  const updateRuleMutation = useUpdateAdminRule();
  const [editingRule, setEditingRule] = useState<RiskIndicator | null>(null);

  const rules = data?.items || [];

  const handleToggleRule = async (rule: RiskIndicator) => {
    try {
      await updateRuleMutation.mutateAsync({
        code: rule.code,
        payload: { enabled: !rule.enabled },
      });
      refetch();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Không thể cập nhật quy tắc.");
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Quản lý Quy tắc phát hiện rủi ro
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Cấu hình bật/tắt và điều chỉnh trọng số đánh giá của 8 nhóm chỉ dấu rủi ro tuyển dụng.
        </p>
      </div>

      {isLoading && (
        <div className="py-16 text-center text-sm text-slate-500">
          Đang tải danh sách quy tắc...
        </div>
      )}

      {isError && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          {error instanceof Error ? error.message : "Không thể tải danh sách quy tắc."}
        </div>
      )}

        <p className="text-sm text-slate-600">Điểm chỉ dấu cộng trọng số một lần cho mỗi rule đã kích hoạt, tối đa 100. Trọng số cũng quyết định thứ tự dấu hiệu; điểm này không phải xác suất lừa đảo.</p>

      {!isLoading && !isError && rules.length > 0 && (
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase">
              <tr>
                <th className="px-4 py-3">Mã & Tên quy tắc</th>
                <th className="px-4 py-3">Mô tả dấu hiệu</th>
                <th className="px-4 py-3">Ưu tiên</th>
                <th className="px-4 py-3">Trạng thái</th>
                <th className="px-4 py-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {rules.map((rule) => (
                <tr key={rule.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <p className="font-mono font-bold text-slate-900">{rule.code}</p>
                    <p className="text-slate-600 font-medium mt-0.5">{rule.name}</p>
                  </td>
                  <td className="px-4 py-3 max-w-md text-slate-600">
                    <p className="line-clamp-2">{rule.description}</p>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="font-bold text-slate-800 text-sm">{rule.weight}</span>
                    <span className="text-slate-400 text-[10px]"> / 100</span>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => handleToggleRule(rule)}
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border transition-colors ${
                        rule.enabled
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200 hover:bg-emerald-100"
                          : "bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200"
                      }`}
                    >
                      {rule.enabled ? "✓ Đang kích hoạt" : "✕ Đã tắt"}
                    </button>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-right">
                    <button
                      type="button"
                      onClick={() => setEditingRule(rule)}
                      className="rounded border border-slate-300 px-2.5 py-1 text-slate-700 hover:bg-slate-50 font-medium"
                    >
                      Chỉnh sửa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit Rule Modal */}
      {editingRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-sm font-bold text-slate-900">
                Chỉnh sửa quy tắc {editingRule.code}
              </h3>
              <button
                type="button"
                onClick={() => setEditingRule(null)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <RuleForm
              rule={editingRule}
              onSuccess={() => {
                setEditingRule(null);
                refetch();
              }}
              onCancel={() => setEditingRule(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
