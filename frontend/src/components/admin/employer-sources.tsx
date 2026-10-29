"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { addEmployerClaim, addEmployerSource, getEmployerSources } from "@/lib/api-client";
import { useSessionKey } from "@/hooks/use-session-key";
import { EmployerAdmin } from "@/types/api";
import { Button } from "@/components/ui/button";

const fields = [
  ["company_name", "Tên doanh nghiệp"], ["tax_id", "Mã số thuế"],
  ["contact_email", "Email liên hệ"], ["recruitment_website", "Website tuyển dụng"],
  ["social_channel_url", "Kênh mạng xã hội"], ["bank_account", "Tài khoản ngân hàng"], ["domain", "Tên miền"],
];
const inputClass = "mt-1 block w-full rounded border border-slate-300 p-2 text-sm";

export function EmployerSources({ employer }: { employer: EmployerAdmin }) {
  const session = useSessionKey();
  const cache = useQueryClient();
  const sources = useQuery({ queryKey: ["admin", "sources", session, employer.id], queryFn: () => getEmployerSources(employer.id), enabled: Boolean(session) });
  const [field, setField] = useState("contact_email");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function submit(event: React.FormEvent<HTMLFormElement>, kind: "source" | "claim") {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const value = (key: string) => String(data.get(key) || "").trim();
    setBusy(true); setError(""); setMessage("");
    try {
      if (kind === "source") {
        await addEmployerSource(employer.id, { url: value("url"), label_vi: value("label"), evidence_excerpt_vi: value("excerpt") });
        await cache.invalidateQueries({ queryKey: ["admin", "sources"] });
        await cache.invalidateQueries({ queryKey: ["admin", "employers"] });
      } else {
        await addEmployerClaim(employer.id, {
          source_id: value("source"), field,
          value: field === "bank_account" ? { account_number: value("account_number"), bank_name: value("bank_name"), account_holder: value("account_holder") } : value("value"),
          assertion: value("assertion") as "supports" | "refutes",
        });
      }
      form.reset();
      setMessage(kind === "source" ? "Đã thêm nguồn xác minh." : "Đã thêm dữ kiện đối chiếu vào nguồn đã chọn.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Không thể lưu dữ liệu."); }
    finally { setBusy(false); }
  }

  return <section className="space-y-5 rounded-xl border border-slate-200 bg-white p-5" aria-labelledby="curation-heading">
    <h2 id="curation-heading" className="text-lg font-semibold">Nguồn & đối chiếu: {employer.legal_name}</h2>
    {error && <p role="alert" className="text-rose-700">{error}</p>}
    {message && <p role="status" className="text-emerald-800">{message}</p>}
    {sources.isError && <p role="alert">{sources.error.message}</p>}
    <ul className="space-y-2 text-sm">{sources.data?.map(source => <li key={source.id}><a href={source.url} target="_blank" rel="noopener noreferrer" className="text-blue-700 underline">{source.label_vi}</a><p>{source.evidence_excerpt_vi}</p></li>)}</ul>
    <div className="grid gap-6 md:grid-cols-2">
      <form onSubmit={event => void submit(event, "source")} className="space-y-3">
        <h3 className="font-semibold">Thêm nguồn đã kiểm chứng</h3>
        <label className="block">Tên nguồn<input name="label" required maxLength={255} className={inputClass} /></label>
        <label className="block">URL nguồn công khai<input name="url" type="url" required maxLength={2048} className={inputClass} /></label>
        <label className="block">Trích đoạn bằng chứng đã lược dữ liệu riêng<textarea name="excerpt" required maxLength={4000} className={inputClass} /></label>
        <Button disabled={busy} type="submit">Thêm nguồn</Button>
      </form>
      <form onSubmit={event => void submit(event, "claim")} className="space-y-3">
        <h3 className="font-semibold">Thêm dữ kiện đối chiếu</h3>
        <label className="block">Nguồn chứng minh<select name="source" required className={inputClass} defaultValue=""><option value="" disabled>Chọn đúng nguồn cho dữ kiện</option>{sources.data?.filter(s => s.is_active && (!s.valid_until || new Date(s.valid_until) > new Date())).map(s => <option key={s.id} value={s.id}>{s.label_vi}</option>)}</select></label>
        <label className="block">Trường đối chiếu<select value={field} onChange={e => setField(e.target.value)} className={inputClass}>{fields.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        {field === "bank_account" ? <fieldset className="space-y-2"><legend>Thông tin ngân hàng</legend>{[["account_number", "Số tài khoản"], ["bank_name", "Ngân hàng"], ["account_holder", "Chủ tài khoản"]].map(([key, label]) => <label key={key} className="block">{label}<input name={key} required autoComplete="off" className={inputClass} /></label>)}</fieldset> : <label className="block">Giá trị đã kiểm chứng<input name="value" required maxLength={2048} className={inputClass} /></label>}
        <label className="block">Kết luận nguồn<select name="assertion" className={inputClass}><option value="supports">Xác nhận</option><option value="refutes">Phủ định</option></select></label>
        <Button disabled={busy || !sources.data?.length} type="submit">Thêm dữ kiện</Button>
      </form>
    </div>
  </section>;
}
