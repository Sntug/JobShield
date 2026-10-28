import React from "react";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AuthProvider, useAuthContext } from "@/providers/auth-provider";
import { getAuthToken, getUserStats, setAuthToken } from "@/lib/api-client";
import { Header } from "@/components/layout/header";
import UserLayout from "@/app/(user)/layout";

const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
  usePathname: () => "/dashboard",
}));
const userA = { id: "a", email: "a@example.com", full_name: "Account A", role: "user", created_at: "2026-10-27T00:00:00Z" };
const userB = { ...userA, id: "b", email: "b@example.com", full_name: "Account B" };
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status });

afterEach(() => {
  sessionStorage.clear();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

function AccountControls() {
  const auth = useAuthContext();
  return <>
    <output>{auth.user?.email || "signed out"}</output>
    <button onClick={() => void auth.refreshUser()}>Refresh</button>
    <button onClick={() => void auth.logout()}>Logout</button>
    <button onClick={() => void auth.login(userB.email, "password_for_account_b")}>Login B</button>
  </>;
}

it("a late profile response cannot replace the newly signed-in account", async () => {
  sessionStorage.setItem("jobshield_auth_token", "token-a");
  let finish!: (response: Response) => void;
  let reads = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/login")) return json({ access_token: "token-b", user: userB });
    if (++reads === 1) return json(userA);
    return new Promise<Response>(resolve => { finish = resolve; });
  }));
  render(<AuthProvider><AccountControls /></AuthProvider>);
  await screen.findByText(userA.email);
  fireEvent.click(screen.getByText("Refresh"));
  await waitFor(() => expect(finish).toBeDefined());
  fireEvent.click(screen.getByText("Login B"));
  await screen.findByText(userB.email);
  await act(async () => { finish(json(userA)); });
  expect(screen.queryByText(userA.email)).not.toBeInTheDocument();
  expect(getAuthToken()).toBe("token-b");
});

it("a late logout response cannot clear a newer login", async () => {
  sessionStorage.setItem("jobshield_auth_token", "token-a");
  let finish!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/logout")) return new Promise<Response>(resolve => { finish = resolve; });
    if (url.endsWith("/login")) return json({ access_token: "token-b", user: userB });
    return json(userA);
  }));
  render(<AuthProvider><AccountControls /></AuthProvider>);
  await screen.findByText(userA.email);
  fireEvent.click(screen.getByText("Logout"));
  await screen.findByText("signed out");
  fireEvent.click(screen.getByText("Login B"));
  await screen.findByText(userB.email);
  await act(async () => { finish(json({ status: "ok" })); });
  expect(getAuthToken()).toBe("token-b");
  expect(screen.getByText(userB.email)).toBeInTheDocument();
});

it("an old account's late 401 cannot clear the new account's token", async () => {
  sessionStorage.setItem("jobshield_auth_token", "token-a");
  let finish!: (response: Response) => void;
  vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const pending = getUserStats();
  setAuthToken("token-b");
  finish(json({}, 401));
  await expect(pending).rejects.toThrow();
  expect(getAuthToken()).toBe("token-b");
});

it("temporary profile errors offer retry without redirecting or discarding the token", async () => {
  sessionStorage.setItem("jobshield_auth_token", "valid-token");
  vi.stubGlobal("fetch", vi.fn()
    .mockResolvedValueOnce(json({}, 503))
    .mockResolvedValueOnce(json(userA)));
  render(<AuthProvider><UserLayout><h1>Private dashboard</h1></UserLayout></AuthProvider>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Không thể tải thông tin tài khoản");
  expect(push).not.toHaveBeenCalled();
  expect(getAuthToken()).toBe("valid-token");
  fireEvent.click(screen.getByText("Thử lại"));
  await screen.findByText("Private dashboard");
  expect(screen.getByText(userA.full_name)).toBeInTheDocument();
  expect(getAuthToken()).toBe("valid-token");
});

it("logout navigates to login after the account state is cleared", async () => {
  sessionStorage.setItem("jobshield_auth_token", "valid-token");
  vi.stubGlobal("fetch", vi.fn(async (url: string) => json(url.endsWith("/logout") ? {} : userA)));
  render(<AuthProvider><Header /></AuthProvider>);
  await screen.findByText(userA.full_name);
  fireEvent.click(screen.getByRole("button", { name: "Đăng xuất" }));
  await waitFor(() => expect(push).toHaveBeenCalledWith("/login"));
  expect(screen.queryByText(userA.full_name)).not.toBeInTheDocument();
});
