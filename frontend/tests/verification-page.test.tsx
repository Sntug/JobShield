import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import VerifyEmployerPage from "@/app/(public)/verify-employer/page";
import { createVerification } from "@/lib/api-client";

const response = {
  request_id: "page-test", verification_label_vi: "Chưa xác minh", summary_vi: "Chưa có nguồn đối chiếu.", findings_vi: [], field_checks: [], matched_sources: [], missing_fields_vi: [],
  limitations_vi: ["Khớp nguồn không xác nhận tin tuyển dụng thật hoặc an toàn."], recommended_actions_vi: ["Xác nhận qua kênh độc lập."], verification_version: "1.2.0", checked_at: "2026-10-26T00:00:00Z",
};
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("Verification page and client", () => {
  it("sends only explicit fields in JSON without guest token or persistent storage", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify(response)));
    vi.stubGlobal("fetch", fetcher);
    const write = vi.spyOn(Storage.prototype, "setItem");
    await createVerification({ tax_id: "0000000001" });
    const [url, options] = fetcher.mock.calls[0];
    expect(url).toBe("/api/v1/verifications");
    expect(JSON.parse(options.body)).toEqual({ tax_id: "0000000001" });
    expect(options.headers).not.toHaveProperty("X-Guest-Session-Token");
    expect(options.credentials).toBe("same-origin");
    expect(write).not.toHaveBeenCalled();
  });
  it("preserves entered fields after server failure and succeeds on retry", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: { code: "SOURCE_STORE_UNAVAILABLE", message_vi: "Kho nguồn tạm thời không khả dụng." } }), { status: 503 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(response))));
    render(<VerifyEmployerPage />);
    fireEvent.change(screen.getByLabelText("Mã số thuế"), { target: { value: "0000000001" } });
    fireEvent.click(screen.getByRole("button", { name: "Đối chiếu thông tin" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Kho nguồn tạm thời không khả dụng.");
    expect(screen.getByLabelText("Mã số thuế")).toHaveValue("0000000001");
    fireEvent.click(screen.getByRole("button", { name: "Đối chiếu thông tin" }));
    expect(await screen.findByRole("heading", { name: "Chưa xác minh" })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Kiểm tra thông tin khác" }));
    await waitFor(() => expect(screen.getByLabelText("Mã số thuế")).toHaveValue(""));
  });
});
