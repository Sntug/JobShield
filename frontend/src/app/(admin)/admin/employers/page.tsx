"use client";

import React, { useState } from "react";
import { useAdminEmployers } from "@/hooks/use-admin";
import { EmployerSources } from "@/components/admin/employer-sources";
import { EmployerForm } from "@/components/admin/employer-form";
import { EmployerAdmin } from "@/types/api";

export default function AdminEmployersPage() {
  const [curating, setCurating] = useState<EmployerAdmin | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [editingEmployer, setEditingEmployer] = useState<EmployerAdmin | null>(null);
  const [isAddingNew, setIsAddingNew] = useState(false);

  const { data, isLoading, isError, error, refetch } = useAdminEmployers(
    page,
    10,
    search.trim() || undefined
  );

  const employers = data?.items || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / 10) || 1;

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    refetch();
  };

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Quản lý Kho nhà tuyển dụng
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Quản trị danh sách các doanh nghiệp đã được xác minh nguồn và các kênh liên hệ chính thức.
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setEditingEmployer(null);
            setIsAddingNew(true);
          }}
          className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 transition-colors"
        >
          + Thêm nhà tuyển dụng
        </button>
      </div>

      <form onSubmit={handleSearchSubmit} className="flex gap-2 max-w-md">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tìm kiếm theo tên hoặc mã số thuế..."
          className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:outline-none"
        />
        <button
          type="submit"
          className="rounded-lg bg-slate-800 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-slate-700"
        >
          Tìm
        </button>
      </form>

      {isLoading && (
        <div className="py-16 text-center text-sm text-slate-500">
          Đang tải danh sách nhà tuyển dụng...
        </div>
      )}

      {isError && (
        <div
          role="alert"
          className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"
        >
          {error instanceof Error ? error.message : "Không thể tải danh sách nhà tuyển dụng."}
        </div>
      )}

      {!isLoading && !isError && employers.length === 0 && (
        <div className="rounded-xl border border-dashed border-slate-300 p-12 text-center text-sm text-slate-500">
          Chưa có nhà tuyển dụng nào phù hợp với tìm kiếm.
        </div>
      )}

      {!isLoading && !isError && employers.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
            <thead className="bg-slate-50 text-slate-600 font-semibold uppercase">
              <tr>
                <th className="px-4 py-3">Tên pháp lý doanh nghiệp</th>
                <th className="px-4 py-3">Mã số thuế</th>
                <th className="px-4 py-3">Trạng thái</th>
                <th className="px-4 py-3">Số nguồn</th>
                <th className="px-4 py-3">Ngày tạo</th>
                <th className="px-4 py-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {employers.map((emp) => (
                <tr key={emp.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-4 py-3 font-bold text-slate-900">{emp.legal_name}</td>
                  <td className="px-4 py-3 font-mono text-slate-600">{emp.tax_id || "N/A"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        emp.is_active
                          ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                          : "bg-slate-100 text-slate-600 border border-slate-200"
                      }`}
                    >
                      {emp.is_active ? "Hoạt động" : "Tạm khóa"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{emp.sources_count} nguồn</td>
                  <td className="px-4 py-3 text-slate-500">
                    {new Date(emp.created_at).toLocaleDateString("vi-VN")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button type="button" onClick={() => setCurating(emp)} className="mr-3 text-blue-700 underline">Nguồn & đối chiếu</button>
                    <button
                      type="button"
                      onClick={() => {
                        setIsAddingNew(false);
                        setEditingEmployer(emp);
                      }}
                      className="rounded border border-slate-300 px-2.5 py-1 text-slate-700 hover:bg-slate-50 font-medium"
                    >
                      Sửa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3 bg-white">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 disabled:opacity-40"
              >
                Trước
              </button>
              <span className="text-xs text-slate-500">
                Trang {page} / {totalPages}
              </span>
              <button
                type="button"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 disabled:opacity-40"
              >
                Sau
              </button>
            </div>
          )}
        </div>
      )}

      {curating && <EmployerSources key={curating.id} employer={curating} />}

      {/* Modal Add / Edit Employer */}
      {(isAddingNew || editingEmployer) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 pb-3">
              <h3 className="text-sm font-bold text-slate-900">
                {editingEmployer ? "Cập nhật nhà tuyển dụng" : "Thêm nhà tuyển dụng mới"}
              </h3>
              <button
                type="button"
                onClick={() => {
                  setIsAddingNew(false);
                  setEditingEmployer(null);
                }}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <EmployerForm
              initialEmployer={editingEmployer}
              onSuccess={() => {
                setIsAddingNew(false);
                setEditingEmployer(null);
                refetch();
              }}
              onCancel={() => {
                setIsAddingNew(false);
                setEditingEmployer(null);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
