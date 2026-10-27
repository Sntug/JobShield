import React, { useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import LoginPage from "@/app/(public)/login/page";
import RegisterPage from "@/app/(public)/register/page";
import { setGuestToken } from "@/lib/api-client";
import { AuthProvider, useAuthContext } from "@/providers/auth-provider";

const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

const user = {
  id: "account-a",
  email: "guest-claim@example.com",
  full_name: "Guest Claim",
  role: "user",
  created_at: "2026-10-28T00:00:00Z",
};

afterEach(() => {
  sessionStorage.clear();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

function Journey({ Page, withGuest }: { Page: typeof LoginPage; withGuest: boolean }) {
  const { loading } = useAuthContext();
  const [showAuth, setShowAuth] = useState(false);
  if (showAuth) return <Page />;
  return <button disabled={loading} onClick={() => {
    if (withGuest) setGuestToken("guest-created-after-provider-mounted");
    setShowAuth(true);
  }}>Continue to account</button>;
}

for (const [mode, Page] of [["login", LoginPage], ["register", RegisterPage]] as const) {
  for (const withGuest of [true, false]) {
    it(`${mode} ${withGuest ? "offers consent for a guest session created during client navigation" : "opens the dashboard when there is no guest session"}`, async () => {
      vi.stubGlobal("fetch", vi.fn(async (url: string) => {
        if (!url.endsWith(`/auth/${mode}`)) throw new Error(`Unexpected request: ${url}`);
        return new Response(JSON.stringify({ access_token: "account-token", token_type: "bearer", user }));
      }));
      render(<AuthProvider><Journey Page={Page} withGuest={withGuest} /></AuthProvider>);
      await waitFor(() => expect(screen.getByText("Continue to account")).toBeEnabled());
      fireEvent.click(screen.getByText("Continue to account"));
      if (mode === "register") fireEvent.change(screen.getByLabelText("Họ và tên"), { target: { value: user.full_name } });
      fireEvent.change(screen.getByLabelText("Email"), { target: { value: user.email } });
      fireEvent.change(screen.getByLabelText("Mật khẩu"), { target: { value: "synthetic_password_2026" } });
      fireEvent.click(screen.getByRole("button", { name: mode === "login" ? "Đăng nhập" : "Đăng ký tài khoản" }));

      if (withGuest) {
        expect(await screen.findByRole("heading", { name: "Tìm thấy kết quả phân tích phiên khách" })).toBeVisible();
        expect(push).not.toHaveBeenCalled();
        expect(sessionStorage.getItem("jobshield_guest_token")).toBe("guest-created-after-provider-mounted");
        fireEvent.click(screen.getByRole("button", { name: "Bỏ qua" }));
        await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
        expect(sessionStorage.getItem("jobshield_guest_token")).toBeNull();
      } else {
        await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
        expect(screen.queryByRole("button", { name: "Nhận vào tài khoản" })).not.toBeInTheDocument();
      }
    });
  }
}
