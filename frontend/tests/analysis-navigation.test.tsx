import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import AnalyzePage from "@/app/(public)/analyze/page";
import { SearchParamsContext } from "next/dist/shared/lib/hooks-client-context.shared-runtime";
import { clearAuthToken, setAuthToken } from "@/lib/api-client";

const snapshot = {
  id: "old-result",
  risk_label_vi: "Ít dấu hiệu rủi ro",
  verification_label_vi: "Chưa xác minh",
  finding_vi: "Kết quả cũ.",
  job: {
    company_name: "Công ty kết quả cũ",
    job_title: null,
    salary: null,
    location: null,
    employment_type: null,
    contact_email: null,
    contact_phone: null,
    recruitment_website: null,
    application_requirements: null,
    required_payments: null,
    suspicious_instructions: null,
  },
  indicators: [],
  evidence: {
    is_demo: false,
    matched_sources: [],
    missing_vi: [],
    limitations_vi: [],
  },
  actions_vi: [],
  engine_version: "1.2.0",
  rules_version: "2026.10",
  created_at: "2026-10-26T00:00:00Z",
  expires_at: "2026-10-27T00:00:00Z",
};

const batchSnapshot = {
  id: "batch-123",
  status: "completed",
  total_items: 1,
  processed_items: 1,
  items: [
    {
      id: "item-1",
      item_order: 1,
      input_type: "url",
      input_value: "https://example.com/job",
      status: "success",
      analysis: snapshot,
    },
  ],
  created_at: "2026-11-03T10:00:00Z",
};

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
  window.history.replaceState({}, "", "/");
});

it("loads the current sample during navigation and replaces it when the query changes", () => {
  const { rerender } = render(
    <SearchParamsContext.Provider value={new URLSearchParams("sample=Tin+mẫu+đầu+tiên")}>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );
  expect(screen.getByLabelText("Nội dung tin tuyển dụng cần phân tích")).toHaveValue("Tin mẫu đầu tiên");
  fireEvent.change(screen.getByLabelText("Nội dung tin tuyển dụng cần phân tích"), { target: { value: "Đã chỉnh sửa" } });
  rerender(
    <SearchParamsContext.Provider value={new URLSearchParams("sample=Tin+mẫu+thứ+hai")}>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );
  expect(screen.getByLabelText("Nội dung tin tuyển dụng cần phân tích")).toHaveValue("Tin mẫu thứ hai");
});

it("a late detail response cannot overwrite the form after browser Back", async () => {
  let resolve!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((done) => { resolve = done; })));
  sessionStorage.setItem("jobshield_guest_token", "test-token");
  window.history.replaceState({}, "", "/analyze?id=old-result");
  render(<AnalyzePage />);
  await waitFor(() => expect(resolve).toBeDefined());
  act(() => {
    window.history.replaceState({}, "", "/analyze");
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();
  await act(async () => { resolve(new Response(JSON.stringify(snapshot))); });
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();
  expect(screen.queryByText("Công ty kết quả cũ")).not.toBeInTheDocument();
});

it("a late private detail response cannot appear after logout", async () => {
  let resolve!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((done) => { resolve = done; })));
  setAuthToken("account-a");
  window.history.replaceState({}, "", "/analyze?id=old-result");
  render(<AnalyzePage />);
  await waitFor(() => expect(resolve).toBeDefined());
  act(() => clearAuthToken());
  await act(async () => { resolve(new Response(JSON.stringify({ ...snapshot, expires_at: null }))); });
  expect(screen.queryByText("Công ty kết quả cũ")).not.toBeInTheDocument();
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();
});

it("a late private analysis submission cannot appear after logout", async () => {
  let resolve!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((done) => { resolve = done; })));
  setAuthToken("account-a");
  render(<AnalyzePage />);
  fireEvent.change(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/), {
    target: { value: "Công ty riêng tuyển dụng nhân viên." },
  });
  fireEvent.click(screen.getByRole("button", { name: /Phân tích tin tuyển dụng/ }));
  await waitFor(() => expect(resolve).toBeDefined());
  act(() => clearAuthToken());
  await act(async () => { resolve(new Response(JSON.stringify({ ...snapshot, expires_at: null }))); });
  expect(screen.queryByText("Công ty kết quả cũ")).not.toBeInTheDocument();
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();
});

it("switches between single and batch modes via the mode switcher tabs", () => {
  render(<AnalyzePage />);

  // Default is single mode
  expect(screen.getByRole("tab", { name: /Một tin/i })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();

  // Switch to batch mode
  fireEvent.click(screen.getByRole("tab", { name: /Nhiều tin/i }));
  expect(screen.getByRole("tab", { name: /Nhiều tin/i })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByRole("tab", { name: /Liên kết \(URLs\)/i })).toBeInTheDocument();

  // Switch back to single mode
  fireEvent.click(screen.getByRole("tab", { name: /Một tin/i }));
  expect(screen.getByRole("tab", { name: /Một tin/i })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/)).toBeInTheDocument();
});

it("switches to batch mode and loads batch when URL has ?batch_id=", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(batchSnapshot)))
  );

  render(
    <SearchParamsContext.Provider value={new URLSearchParams("batch_id=batch-123")}>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );

  expect(screen.getByRole("tab", { name: /Nhiều tin/i })).toHaveAttribute("aria-selected", "true");
  await waitFor(() => {
    expect(screen.getByText("Hoàn thành")).toBeInTheDocument();
  });
  expect(screen.getByText("Đã xử lý 1/1 tin")).toBeInTheDocument();
});

it("forces single mode when URL has ?sample= or ?id= even if batch_id was active", () => {
  render(
    <SearchParamsContext.Provider value={new URLSearchParams("sample=Tin+mẫu+bắt+buộc&batch_id=batch-123")}>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );

  expect(screen.getByRole("tab", { name: /Một tin/i })).toHaveAttribute("aria-selected", "true");
  expect(screen.getByLabelText("Nội dung tin tuyển dụng cần phân tích")).toHaveValue("Tin mẫu bắt buộc");
});
