import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { SearchParamsContext } from "next/dist/shared/lib/hooks-client-context.shared-runtime";
import AnalyzePage from "@/app/(public)/analyze/page";
import { ACTIVE_BATCH_KEY } from "@/hooks/use-batch-analysis";

const batch = {
  id: "batch-123",
  status: "completed",
  total_items: 1,
  processed_items: 1,
  items: [],
  created_at: "2026-11-03T10:00:00Z",
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
  window.history.replaceState({}, "", "/analyze");
});

it("loads an explicit batch URL once", async () => {
  sessionStorage.setItem("jobshield_guest_token", "guest-session");
  const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify(batch), { status: 200 }));
  vi.stubGlobal("fetch", fetchSpy);

  render(
    <SearchParamsContext.Provider value={new URLSearchParams("batch_id=batch-123")}>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );

  await waitFor(() => expect(screen.getByText("Hoàn thành")).toBeInTheDocument());
  expect(fetchSpy).toHaveBeenCalledTimes(1);
});

it("restores the active batch on a bare analyze route and reflects its ID in the URL", async () => {
  localStorage.setItem(ACTIVE_BATCH_KEY, "batch-123");
  sessionStorage.setItem("jobshield_guest_token", "guest-session");
  const fetchSpy = vi.fn().mockResolvedValue(new Response(JSON.stringify(batch), { status: 200 }));
  vi.stubGlobal("fetch", fetchSpy);

  render(
    <SearchParamsContext.Provider value={new URLSearchParams()}>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );

  await waitFor(() => expect(screen.getByText("Hoàn thành")).toBeInTheDocument());
  await waitFor(() => expect(window.location.search).toBe("?batch_id=batch-123"));
  expect(fetchSpy).toHaveBeenCalledTimes(1);
});

it("does not restore a cached batch over an explicit single-analysis URL", async () => {
  localStorage.setItem(ACTIVE_BATCH_KEY, "batch-123");
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);

  render(
    <SearchParamsContext.Provider value={new URLSearchParams("sample=Tin+mẫu") }>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );

  expect(screen.getByLabelText("Nội dung tin tuyển dụng cần phân tích")).toHaveValue("Tin mẫu");
  expect(fetchSpy).not.toHaveBeenCalled();
});

it("clears a cached batch when a bare-route guest has no credential to access it", async () => {
  localStorage.setItem(ACTIVE_BATCH_KEY, "batch-123");
  const fetchSpy = vi.fn(async (_url: string, options: RequestInit) => {
    expect(new Headers(options.headers).has("X-Guest-Session-Token")).toBe(false);
    return new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 });
  });
  vi.stubGlobal("fetch", fetchSpy);

  render(
    <SearchParamsContext.Provider value={new URLSearchParams()}>
      <AnalyzePage />
    </SearchParamsContext.Provider>
  );

  await waitFor(() => expect(localStorage.getItem(ACTIVE_BATCH_KEY)).toBeNull());
  expect(await screen.findByText(/Forbidden/i)).toBeInTheDocument();
  expect(fetchSpy).toHaveBeenCalledTimes(1);
});
