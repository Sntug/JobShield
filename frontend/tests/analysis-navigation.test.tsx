import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import AnalyzePage from "@/app/(public)/analyze/page";

const snapshot = {
  id: "old-result", risk_label_vi: "Ít dấu hiệu rủi ro", verification_label_vi: "Chưa xác minh", finding_vi: "Kết quả cũ.",
  job: { company_name: "Công ty kết quả cũ", job_title: null, salary: null, location: null, employment_type: null, contact_email: null, contact_phone: null, recruitment_website: null, application_requirements: null, required_payments: null, suspicious_instructions: null },
  indicators: [], evidence: { is_demo: false, matched_sources: [], missing_vi: [], limitations_vi: [] }, actions_vi: [], engine_version: "1.2.0", rules_version: "2026.10", created_at: "2026-10-26T00:00:00Z", expires_at: "2026-10-27T00:00:00Z",
};
afterEach(() => { vi.unstubAllGlobals(); sessionStorage.clear(); window.history.replaceState({}, "", "/"); });

it("a late detail response cannot overwrite the form after browser Back", async () => {
  let resolve!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(done => { resolve = done; })));
  sessionStorage.setItem("jobshield_guest_token", "test-token");
  window.history.replaceState({}, "", "/analyze?id=old-result");
  render(<AnalyzePage />);
  await waitFor(() => expect(resolve).toBeDefined());
  act(() => { window.history.replaceState({}, "", "/analyze"); window.dispatchEvent(new PopStateEvent("popstate")); });
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();
  await act(async () => { resolve(new Response(JSON.stringify(snapshot))); });
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();
  expect(screen.queryByText("Công ty kết quả cũ")).not.toBeInTheDocument();
});
