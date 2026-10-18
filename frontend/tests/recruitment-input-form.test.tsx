import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { RecruitmentInputForm } from "@/components/analysis/recruitment-input-form";

describe("RecruitmentInputForm", () => {
  it("renders textarea, character counter, and submit button", () => {
    const handleSubmit = vi.fn();
    render(<RecruitmentInputForm onSubmit={handleSubmit} />);

    const textarea = screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/i);
    expect(textarea).toBeInTheDocument();
    expect(screen.getByText(/0\s*\/\s*10[.,]000\s*ký tự/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Phân tích tin tuyển dụng/i });
    expect(submitBtn).toBeDisabled();
  });

  it("accurately counts Unicode code points and handles submit", async () => {
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RecruitmentInputForm onSubmit={handleSubmit} />);

    const textarea = screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/i);
    // Emoji 🚀 is 2 UTF-16 code units, but 1 Unicode code point
    fireEvent.change(textarea, { target: { value: "Tuyển dụng 🚀" } });

    expect(screen.getByText(/12\s*\/\s*10[.,]000\s*ký tự/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Phân tích tin tuyển dụng/i });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);
    expect(handleSubmit).toHaveBeenCalledWith("Tuyển dụng 🚀");
  });

  it("displays session error and calls onResetSession when reset button clicked", () => {
    const handleReset = vi.fn();
    render(
      <RecruitmentInputForm
        onSubmit={vi.fn()}
        error="Phiên khách đã hết hạn."
        isSessionInvalid={true}
        onResetSession={handleReset}
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Phiên khách đã hết hạn.");
    const resetBtn = screen.getByRole("button", { name: /Làm mới phiên và thử lại/i });
    fireEvent.click(resetBtn);
    expect(handleReset).toHaveBeenCalledTimes(1);
  });
});
