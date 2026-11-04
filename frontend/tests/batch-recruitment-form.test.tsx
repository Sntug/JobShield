import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BatchRecruitmentForm } from "@/components/analysis/batch-recruitment-form";

describe("BatchRecruitmentForm", () => {
  it("renders default URLs mode with submit button disabled initially", () => {
    render(<BatchRecruitmentForm onSubmit={vi.fn()} />);

    expect(
      screen.getByRole("tab", { name: /Liên kết \(URLs\)/i })
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/)).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Kiểm tra tất cả/i });
    expect(submitBtn).toBeDisabled();
  });

  it("validates URLs line by line, ignores empty lines, and preserves ordering", async () => {
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BatchRecruitmentForm onSubmit={handleSubmit} />);

    const textarea = screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/);

    // Paste valid URLs with empty lines
    fireEvent.change(textarea, {
      target: {
        value: `
          https://congty-a.vn/tuyendung
          
          https://congty-b.com/careers/frontend
          
        `,
      },
    });

    expect(screen.getByText(/Đã nhận diện: 2\/10 liên kết/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Kiểm tra tất cả/i });
    expect(submitBtn).not.toBeDisabled();

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledTimes(1);
    });

    expect(handleSubmit).toHaveBeenCalledWith({
      items: [
        { type: "url", value: "https://congty-a.vn/tuyendung" },
        { type: "url", value: "https://congty-b.com/careers/frontend" },
      ],
      use_ai: false,
      ai_consent: false,
    });
  });

  it("submits URL and pasted text items together in mixed mode", async () => {
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BatchRecruitmentForm onSubmit={handleSubmit} />);

    fireEvent.click(screen.getByRole("tab", { name: "Kết hợp" }));
    fireEvent.change(screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/), {
      target: { value: "https://jobs.example.com/role" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #1/), {
      target: { value: "Tuyển kỹ sư phần mềm tại Hà Nội." },
    });

    expect(screen.getByText("Đã nhận diện: 2/10 tin")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Kiểm tra tất cả/i }));

    await waitFor(() => expect(handleSubmit).toHaveBeenCalledTimes(1));
    expect(handleSubmit).toHaveBeenCalledWith({
      items: [
        { type: "url", value: "https://jobs.example.com/role" },
        { type: "text", value: "Tuyển kỹ sư phần mềm tại Hà Nội." },
      ],
      use_ai: false,
      ai_consent: false,
    });
  });

  it("ignores hidden URL drafts when submitting in text-only mode", async () => {
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BatchRecruitmentForm onSubmit={handleSubmit} />);

    fireEvent.change(screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/), {
      target: { value: "https://jobs.example.com/hidden" },
    });
    fireEvent.click(screen.getByRole("tab", { name: /Nội dung \(Văn bản\)/i }));

    expect(screen.getByText("Đã nhập: 0/10 tin")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Kiểm tra tất cả/i })).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #1/), {
      target: { value: "Tuyển nhân viên kế toán." },
    });
    fireEvent.click(screen.getByRole("button", { name: /Kiểm tra tất cả/i }));

    await waitFor(() => expect(handleSubmit).toHaveBeenCalledTimes(1));
    expect(handleSubmit).toHaveBeenCalledWith({
      items: [{ type: "text", value: "Tuyển nhân viên kế toán." }],
      use_ai: false,
      ai_consent: false,
    });
  });

  it("applies the 10-item limit to the combined URL and text payload", () => {
    render(<BatchRecruitmentForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("tab", { name: "Kết hợp" }));
    fireEvent.change(screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/), {
      target: {
        value: Array.from({ length: 9 }, (_, index) => `https://jobs.example.com/${index}`).join("\n"),
      },
    });
    fireEvent.change(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #1/), {
      target: { value: "Tin văn bản thứ nhất" },
    });
    fireEvent.change(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #2/), {
      target: { value: "Tin văn bản thứ hai" },
    });

    expect(screen.getByRole("alert")).toHaveTextContent(/Tối đa 10 tin tuyển dụng/i);
    expect(screen.getByRole("button", { name: /Kiểm tra tất cả/i })).toBeDisabled();
  });

  it("preloads a failed item into the matching input mode", () => {
    render(
      <BatchRecruitmentForm
        onSubmit={vi.fn()}
        initialItem={{ type: "url", value: "https://jobs.example.com/retry" }}
      />
    );

    expect(screen.getByRole("tab", { name: /Liên kết \(URLs\)/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/)).toHaveValue(
      "https://jobs.example.com/retry"
    );
  });

  it("shows inline error when URL is malformed and disables submit", () => {
    render(<BatchRecruitmentForm onSubmit={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/);

    fireEvent.change(textarea, {
      target: {
        value: "https://valid.com/job\nnot-a-valid-url\nftp://invalid-protocol.com",
      },
    });

    expect(
      screen.getAllByText(/không phải URL http\(s\) hợp lệ/i).length
    ).toBeGreaterThanOrEqual(1);

    const submitBtn = screen.getByRole("button", { name: /Kiểm tra tất cả/i });
    expect(submitBtn).toBeDisabled();
  });

  it("shows error when item count exceeds 10 in URL mode", () => {
    render(<BatchRecruitmentForm onSubmit={vi.fn()} />);

    const textarea = screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/);

    const elevenUrls = Array.from({ length: 11 }, (_, i) => `https://job.vn/${i + 1}`).join("\n");
    fireEvent.change(textarea, { target: { value: elevenUrls } });

    expect(screen.getByText(/Tối đa 10 tin tuyển dụng cho mỗi lượt/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Kiểm tra tất cả/i })).toBeDisabled();
  });

  it("switches to Content mode, manages multiple text boxes, ignores empty boxes, and submits", async () => {
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BatchRecruitmentForm onSubmit={handleSubmit} />);

    // Switch to Content mode tab
    const contentTab = screen.getByRole("tab", { name: /Nội dung \(Văn bản\)/i });
    fireEvent.click(contentTab);
    expect(contentTab).toHaveAttribute("aria-selected", "true");

    // Initially 2 boxes
    expect(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #1/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #2/)).toBeInTheDocument();

    // Fill only box #1, box #2 empty (empty boxes ignored)
    fireEvent.change(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #1/), {
      target: { value: "Tuyển kỹ sư phần mềm mức lương 25 triệu/tháng tại Hà Nội." },
    });

    const submitBtn = screen.getByRole("button", { name: /Kiểm tra tất cả/i });
    expect(submitBtn).not.toBeDisabled();

    // Add box #3
    const addBtn = screen.getByRole("button", { name: /Thêm tin tuyển dụng/i });
    fireEvent.click(addBtn);
    expect(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #3/)).toBeInTheDocument();

    // Fill box #3
    fireEvent.change(screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #3/), {
      target: { value: "Tuyển chuyên viên an ninh mạng tại TP.HCM." },
    });

    // Delete box #2 (the empty one)
    const deleteBtnBox2 = screen.getByRole("button", { name: "Xóa tin #2" });
    fireEvent.click(deleteBtnBox2);

    // Now box 1 and box 2 are the filled ones
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledTimes(1);
    });

    expect(handleSubmit).toHaveBeenCalledWith({
      items: [
        {
          type: "text",
          value: "Tuyển kỹ sư phần mềm mức lương 25 triệu/tháng tại Hà Nội.",
        },
        {
          type: "text",
          value: "Tuyển chuyên viên an ninh mạng tại TP.HCM.",
        },
      ],
      use_ai: false,
      ai_consent: false,
    });
  });

  it("enforces 10,000 Unicode character limit on content items", () => {
    render(<BatchRecruitmentForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("tab", { name: /Nội dung \(Văn bản\)/i }));

    const box1 = screen.getByPlaceholderText(/Dán nội dung tin tuyển dụng #1/);
    const hugeText = "A".repeat(10001);

    fireEvent.change(box1, { target: { value: hugeText } });

    expect(screen.getByText(/Vượt quá giới hạn 10.000 ký tự/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Kiểm tra tất cả/i })).toBeDisabled();
  });

  it("handles AI analysis toggle and consent checkbox", async () => {
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    render(<BatchRecruitmentForm onSubmit={handleSubmit} />);

    const textarea = screen.getByPlaceholderText(/https:\/\/tuyendung\.example\/job-1/);
    fireEvent.change(textarea, { target: { value: "https://example.com/job-ai" } });

    const enableAiCheckbox = screen.getByLabelText(/Bật hỗ trợ phân tích ngữ nghĩa AI/i);
    fireEvent.click(enableAiCheckbox);

    const consentCheckbox = screen.getByLabelText(/Tôi đồng ý gửi nội dung/i);
    expect(consentCheckbox).toBeInTheDocument();
    fireEvent.click(consentCheckbox);

    const submitBtn = screen.getByRole("button", { name: /Kiểm tra tất cả/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledTimes(1);
    });

    expect(handleSubmit).toHaveBeenCalledWith({
      items: [{ type: "url", value: "https://example.com/job-ai" }],
      use_ai: true,
      ai_consent: true,
    });
  });

  it("renders global error message when error prop is provided", () => {
    render(
      <BatchRecruitmentForm
        onSubmit={vi.fn()}
        error="Không thể kết nối đến máy chủ phân tích."
      />
    );

    expect(
      screen.getByText("Không thể kết nối đến máy chủ phân tích.")
    ).toBeInTheDocument();
  });

  it("disables submit button and shows loading label when isLoading=true", () => {
    render(<BatchRecruitmentForm onSubmit={vi.fn()} isLoading={true} />);

    const submitBtn = screen.getByRole("button", { name: /Đang gửi yêu cầu.../i });
    expect(submitBtn).toBeDisabled();
  });
});
