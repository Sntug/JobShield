import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { QueryProvider } from "@/providers/query-provider";
import { useMyReports } from "@/hooks/use-reports";
import { clearAuthToken, setAuthToken } from "@/lib/api-client";

afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); });
function Reports() {
  const query = useMyReports();
  return <output>{query.data?.items[0]?.description || "No private data"}</output>;
}
it("isolates cached reports across login, logout and late requests", async () => {
  setAuthToken("session-a");
  let late!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn((_url, options) => {
    const token = options.headers.get("Authorization");
    if (token === "Bearer session-a") return new Promise<Response>(resolve => { late = resolve; });
    return Promise.resolve(new Response(JSON.stringify({ items: [{ description: "B private report" }], total: 1 })));
  }));
  render(<QueryProvider><Reports /></QueryProvider>);
  await waitFor(() => expect(late).toBeDefined());
  act(() => setAuthToken("session-b"));
  await screen.findByText("B private report");
  await act(async () => late(new Response(JSON.stringify({ items: [{ description: "A private report" }], total: 1 }))));
  expect(screen.queryByText("A private report")).not.toBeInTheDocument();
  act(() => clearAuthToken());
  await screen.findByText("No private data");
  expect(screen.queryByText("B private report")).not.toBeInTheDocument();
});
