"use client";

import { useState } from "react";
import { useCreatePublicWarning, useSupersedePublicWarning } from "@/hooks/use-admin";
import { PublicWarning } from "@/types/api";
import { Button } from "@/components/ui/button";

const control = "mt-1 block w-full rounded border border-slate-300 p-2 text-sm";
export function WarningEditor({ warning, onDone }: { warning?: PublicWarning; onDone: () => void }) {
  const create = useCreatePublicWarning();
  const correct = useSupersedePublicWarning();
  const [sources, setSources] = useState(warning?.public_sources_snapshot.map(s => ({ label_vi: String(s.label_vi || ""), url: String(s.url || "") })) || [{ label_vi: "", url: "" }]);
  const [error, setError] = useState("");
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const data = new FormData(event.currentTarget);
    const payload = { title_vi: String(data.get("title")).trim(), public_summary_vi: String(data.get("summary")).trim(), public_sources_snapshot: sources };
    try {
      if (warning) await correct.mutateAsync({ warningId: warning.id, payload });
      else await create.mutateAsync({ ...payload, report_id: String(data.get("report") || "").trim() || undefined });
      onDone();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Không thể xuất bản cảnh báo."); }
  }
  return <form onSubmit={event => void submit(event)} className="space-y-4 rounded-xl border bg-white p-5">
    <h2 className="text-lg font-semibold">{warning ? `Đính chính cảnh báo v${warning.revision}` : "Xuất bản cảnh báo"}</h2>
    {error && <p role="alert" className="text-rose-700">{error}</p>}
    {!warning && <label className="block">ID báo cáo đã xác minh (nếu có)<input name="report" className={control} /></label>}
    <label className="block">Tiêu đề công khai<input name="title" defaultValue={warning?.title_vi} required minLength={5} maxLength={255} className={control} /></label>
    <label className="block">Tóm tắt công khai, đã lược thông tin người gửi<textarea name="summary" defaultValue={warning?.public_summary_vi} required minLength={10} maxLength={5000} rows={4} className={control} /></label>
    {sources.map((source, index) => <fieldset key={index} className="space-y-2 rounded border p-3">
      <legend>Nguồn công khai {index + 1}</legend>
      <label className="block">Tên nguồn<input required maxLength={255} value={source.label_vi} onChange={e => setSources(prev => prev.map((s, i) => i === index ? { ...s, label_vi: e.target.value } : s))} className={control} /></label>
      <label className="block">URL nguồn<input required type="url" maxLength={2048} value={source.url} onChange={e => setSources(prev => prev.map((s, i) => i === index ? { ...s, url: e.target.value } : s))} className={control} /></label>
      <button type="button" disabled={sources.length === 1} onClick={() => setSources(prev => prev.filter((_, i) => i !== index))} className="text-sm text-rose-700 underline disabled:opacity-40">Xóa nguồn {index + 1}</button>
    </fieldset>)}
    <Button type="button" variant="outline" disabled={sources.length >= 10} onClick={() => setSources(prev => [...prev, { label_vi: "", url: "" }])}>Thêm nguồn công khai</Button>
    <label className="flex gap-2"><input type="checkbox" required />Tôi đã kiểm tra căn cứ và loại thông tin riêng của người báo cáo.</label>
    <div className="flex gap-3"><Button type="submit" disabled={create.isPending || correct.isPending}>{warning ? "Xuất bản bản đính chính" : "Xuất bản cảnh báo"}</Button><Button type="button" variant="outline" onClick={onDone}>Đóng</Button></div>
  </form>;
}
