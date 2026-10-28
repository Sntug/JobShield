"use client";

import Link from "next/link";
import { useState } from "react";
import { useAdminWarnings, useWithdrawPublicWarning } from "@/hooks/use-admin";
import { WarningEditor } from "@/components/admin/warning-editor";
import { Button } from "@/components/ui/button";
import { PublicWarning } from "@/types/api";

export default function AdminWarningsPage() {
  const [page, setPage] = useState(1);
  const warnings = useAdminWarnings(page);
  const withdraw = useWithdrawPublicWarning();
  const [editor, setEditor] = useState<PublicWarning | "new" | null>(null);
  const [withdrawing, setWithdrawing] = useState<PublicWarning | null>(null);
  const [error, setError] = useState("");
  async function submitWithdrawal(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (!withdrawing) return;
    const reason = String(new FormData(event.currentTarget).get("reason") || "").trim();
    try { await withdraw.mutateAsync({ warningId: withdrawing.id, payload: { withdrawal_reason_vi: reason } }); setWithdrawing(null); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Không thể thu hồi cảnh báo."); }
  }
  return <div className="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-bold">Quản lý cảnh báo công khai</h1><Button onClick={() => { setWithdrawing(null); setEditor("new"); }}>Tạo cảnh báo</Button></div>
    {warnings.isLoading && <p>Đang tải cảnh báo...</p>}
    {warnings.isError && <p role="alert">{warnings.error.message}</p>}
    {editor && <WarningEditor key={editor === "new" ? "new" : editor.id} warning={editor === "new" ? undefined : editor} onDone={() => setEditor(null)} />}
    {withdrawing && <form onSubmit={event => void submitWithdrawal(event)} className="space-y-3 rounded border border-rose-300 bg-white p-5">
      <h2 className="font-semibold">Thu hồi: {withdrawing.title_vi}</h2>
      {error && <p role="alert" className="text-rose-700">{error}</p>}
      <label className="block">Lý do thu hồi công khai<textarea name="reason" required minLength={5} maxLength={1000} className="mt-1 block w-full rounded border p-2" /></label>
      <Button disabled={withdraw.isPending} type="submit">Xác nhận thu hồi</Button><Button variant="outline" type="button" onClick={() => setWithdrawing(null)}>Hủy</Button>
    </form>}
    <ul className="space-y-3">{warnings.data?.items.map(warning => <li key={warning.id} className="space-y-2 rounded border bg-white p-4">
      <h2 className="font-semibold">{warning.title_vi}</h2><p>v{warning.revision} · {({ published: "Đang công khai", superseded: "Đã đính chính", withdrawn: "Đã thu hồi" })[warning.status]}</p>
      {warning.withdrawal_reason_vi && <p>Lý do: {warning.withdrawal_reason_vi}</p>}
      <div className="flex flex-wrap gap-3"><Link className="text-blue-700 underline" href={`/safety/${warning.id}`}>Xem bản công khai</Link>{warning.status === "published" && <><button className="text-blue-700 underline" onClick={() => { setWithdrawing(null); setEditor(warning); }}>Đính chính</button><button className="text-rose-700 underline" onClick={() => { setEditor(null); setError(""); setWithdrawing(warning); }}>Thu hồi</button></>}</div>
    </li>)}</ul>
    {warnings.data?.total === 0 && <p>Chưa có cảnh báo. Tạo cảnh báo từ căn cứ đã kiểm chứng.</p>}
    <div className="flex items-center gap-3"><Button variant="outline" disabled={page === 1} onClick={() => setPage(p => p - 1)}>Trang trước</Button><span>Trang {page}</span><Button variant="outline" disabled={!warnings.data || page * 10 >= warnings.data.total} onClick={() => setPage(p => p + 1)}>Trang sau</Button></div>
  </div>;
}
