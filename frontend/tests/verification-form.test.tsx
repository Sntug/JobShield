import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VerificationForm } from "@/components/employers/verification-form";

describe("VerificationForm", () => {
  it("rejects empty input with an accessible summary", async () => {
    const submit = vi.fn();
    render(<VerificationForm onSubmit={submit} />);
    fireEvent.click(screen.getByRole("button", { name: "Đối chiếu thông tin" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/ít nhất một thông tin/i);
    expect(submit).not.toHaveBeenCalled();
  });
  it("submits tax ID alone and omits empty optional values", async () => {
    const submit = vi.fn().mockResolvedValue(undefined);
    render(<VerificationForm onSubmit={submit} />);
    fireEvent.change(screen.getByLabelText("Mã số thuế"), { target: { value: "0123456789" } });
    fireEvent.click(screen.getByRole("button", { name: "Đối chiếu thông tin" }));
    await waitFor(() => expect(submit).toHaveBeenCalledWith({ tax_id: "0123456789" }));
  });
  it("requires a complete bank object and keeps the other input", async () => {
    const submit = vi.fn();
    render(<VerificationForm onSubmit={submit} />);
    fireEvent.change(screen.getByLabelText("Tên công ty"), { target: { value: "Công ty Mẫu" } });
    fireEvent.change(screen.getByLabelText("Số tài khoản"), { target: { value: "0000123" } });
    fireEvent.click(screen.getByRole("button", { name: "Đối chiếu thông tin" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/đủ ngân hàng, số tài khoản và chủ tài khoản/i);
    expect(screen.getByLabelText("Tên công ty")).toHaveValue("Công ty Mẫu");
    expect(submit).not.toHaveBeenCalled();
  });
  it("disables submission while a request is pending", () => {
    render(<VerificationForm onSubmit={vi.fn()} isLoading />);
    expect(screen.getByRole("button", { name: /Đang đối chiếu/i })).toBeDisabled();
    expect(screen.getByLabelText("Email liên hệ")).toBeDisabled();
  });
});
