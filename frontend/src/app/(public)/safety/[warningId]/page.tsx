"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { usePublicWarning } from "@/hooks/use-admin";

export default function WarningDetailPage() {
  const { warningId } = useParams<{ warningId: string }>();
  const query = usePublicWarning(warningId);
  const warning = query.data;
  return <main className="mx-auto max-w-3xl space-y-4 px-4 py-10">
    <Link href="/safety" className="text-blue-700 underline">← Danh sách cảnh báo</Link>
    {query.isLoading && <p>Đang tải cảnh báo...</p>}
    {query.isError && <p role="alert">{query.error.message}</p>}
    {warning && <><h1 className="text-2xl font-bold">{warning.title_vi}</h1><p>Phiên bản {warning.revision}</p>
      {warning.status === "withdrawn" ? <div role="status"><h2 className="font-semibold">Cảnh báo đã được thu hồi</h2><p>{warning.withdrawal_reason_vi}</p>{warning.withdrawn_at && <p>Thời điểm: {new Date(warning.withdrawn_at).toLocaleString("vi-VN")}</p>}</div> : warning.status === "superseded" ? <p>Cảnh báo này đã có bản đính chính.</p> : <><p className="whitespace-pre-wrap">{warning.public_summary_vi}</p><ul>{warning.public_sources_snapshot.map((source, index) => <li key={index}><a href={String(source.url)} className="text-blue-700 underline" target="_blank" rel="noopener noreferrer">{String(source.label_vi)}</a></li>)}</ul></>}
      {warning.next_warning_id && <Link href={`/safety/${warning.next_warning_id}`} className="text-blue-700 underline">Xem bản đính chính tiếp theo →</Link>}
    </>}
  </main>;
}
