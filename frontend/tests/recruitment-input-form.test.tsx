import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { RecruitmentInputForm } from "@/components/analysis/recruitment-input-form";
import * as apiClient from "@/lib/api-client";

vi.mock("@/lib/api-client", async () => {
  const actual = await vi.importActual<typeof apiClient>("@/lib/api-client");
  return {
    ...actual,
    extractFromImage: vi.fn(),
    extractFromUrl: vi.fn(),
  };
});

describe("RecruitmentInputForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders textarea, character counter, tabs, and submit button", () => {
    const handleSubmit = vi.fn();
    render(<RecruitmentInputForm onSubmit={handleSubmit} />);

    expect(screen.getByRole("tab", { name: "Văn bản" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Hình ảnh/i })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: /Liên kết/i })).toHaveAttribute("aria-selected", "false");

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

  it("handles AI toggle and consent flow correctly on submit", async () => {
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    render(<RecruitmentInputForm onSubmit={handleSubmit} />);

    const textarea = screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/i);
    fireEvent.change(textarea, { target: { value: "Tin tuyển dụng có bật AI" } });

    const aiToggle = screen.getByRole("checkbox", {
      name: /Bật hỗ trợ phân tích ngữ nghĩa AI chuyên sâu/i,
    });
    expect(aiToggle).not.toBeChecked();

    // Bật AI toggle
    fireEvent.click(aiToggle);
    expect(aiToggle).toBeChecked();

    // Khối lưu ý quyền riêng tư và checkbox consent xuất hiện
    expect(screen.getByText(/Lưu ý quyền riêng tư:/i)).toBeInTheDocument();
    const consentCheckbox = screen.getByRole("checkbox", {
      name: /Tôi đồng ý gửi nội dung tin tuyển dụng này tới dịch vụ AI/i,
    });
    expect(consentCheckbox).not.toBeChecked();

    // Submit khi bật AI nhưng chưa tích consent
    const submitBtn = screen.getByRole("button", { name: /Phân tích tin tuyển dụng/i });
    fireEvent.click(submitBtn);
    expect(handleSubmit).toHaveBeenCalledWith("Tin tuyển dụng có bật AI", {
      use_ai: true,
      ai_consent: false,
    });

    // Tích consent và submit lại
    fireEvent.click(consentCheckbox);
    expect(consentCheckbox).toBeChecked();
    fireEvent.click(submitBtn);
    expect(handleSubmit).toHaveBeenCalledWith("Tin tuyển dụng có bật AI", {
      use_ai: true,
      ai_consent: true,
    });
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

  it("switches to Image mode and extracts text successfully", async () => {
    vi.mocked(apiClient.extractFromImage).mockResolvedValueOnce({
      request_id: "req-1",
      success: true,
      source_type: "image",
      text: "Công ty ABC tuyển Lập trình viên Backend lương 15 triệu.",
      failure_vi: null,
    });

    render(<RecruitmentInputForm onSubmit={vi.fn()} />);

    // Chuyển sang tab Hình ảnh
    fireEvent.click(screen.getByRole("tab", { name: /Hình ảnh/i }));
    expect(screen.getByText(/Chọn ảnh chụp tin tuyển dụng/i)).toBeInTheDocument();

    const file = new File(["dummy png"], "job-ad.png", { type: "image/png" });
    const fileInput = document.getElementById("recruitment-image-file") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    const extractBtn = screen.getByRole("button", { name: /Trích xuất văn bản từ ảnh/i });
    expect(extractBtn).not.toBeDisabled();
    fireEvent.click(extractBtn);

    await waitFor(() => {
      expect(apiClient.extractFromImage).toHaveBeenCalledWith(file);
    });

    const textarea = screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/i);
    expect(textarea).toHaveValue("Công ty ABC tuyển Lập trình viên Backend lương 15 triệu.");
    expect(screen.getByText(/Đã trích xuất văn bản từ ảnh thành công/i)).toBeInTheDocument();
  });

  it("handles OCR failure and allows user to manually edit or paste text", async () => {
    vi.mocked(apiClient.extractFromImage).mockResolvedValueOnce({
      request_id: "req-fail",
      success: false,
      source_type: "image",
      text: null,
      failure_vi: "Ảnh DEMO bị mờ, không đọc được chữ.",
    });

    const handleSubmit = vi.fn();
    render(<RecruitmentInputForm onSubmit={handleSubmit} />);

    fireEvent.click(screen.getByRole("tab", { name: /Hình ảnh/i }));

    const file = new File(["blurry"], "blurry.png", { type: "image/png" });
    const fileInput = document.getElementById("recruitment-image-file") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: /Trích xuất văn bản từ ảnh/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Ảnh DEMO bị mờ, không đọc được chữ.");
    });

    // Người dùng tự dán văn bản thủ công vào textarea
    const textarea = screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/i);
    fireEvent.change(textarea, { target: { value: "Nội dung nhập tay thay thế cho ảnh mờ." } });

    const submitBtn = screen.getByRole("button", { name: /Phân tích tin tuyển dụng/i });
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);
    expect(handleSubmit).toHaveBeenCalledWith("Nội dung nhập tay thay thế cho ảnh mờ.");
  });

  it("switches to URL mode and extracts text successfully", async () => {
    vi.mocked(apiClient.extractFromUrl).mockResolvedValueOnce({
      request_id: "req-url",
      success: true,
      source_type: "url",
      text: "Tin tuyển dụng trích xuất từ trang web: Tuyển QA Automation.",
      failure_vi: null,
    });

    render(<RecruitmentInputForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("tab", { name: /Liên kết/i }));

    const urlInput = screen.getByPlaceholderText(/https:\/\/tuyendung\.example/i);
    fireEvent.change(urlInput, { target: { value: "https://tuyendung.example/qa" } });

    const extractBtn = screen.getByRole("button", { name: /Lấy nội dung từ liên kết/i });
    fireEvent.click(extractBtn);

    await waitFor(() => {
      expect(apiClient.extractFromUrl).toHaveBeenCalledWith("https://tuyendung.example/qa");
    });

    const textarea = screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/i);
    expect(textarea).toHaveValue("Tin tuyển dụng trích xuất từ trang web: Tuyển QA Automation.");
  });

  it("handles URL blocked scenario and allows manual paste", async () => {
    vi.mocked(apiClient.extractFromUrl).mockResolvedValueOnce({
      request_id: "req-url-blocked",
      success: false,
      source_type: "url",
      text: null,
      failure_vi: "Trang DEMO yêu cầu đăng nhập; không trích xuất nội dung.",
    });

    render(<RecruitmentInputForm onSubmit={vi.fn()} />);

    fireEvent.click(screen.getByRole("tab", { name: /Liên kết/i }));

    const urlInput = screen.getByPlaceholderText(/https:\/\/tuyendung\.example/i);
    fireEvent.change(urlInput, { target: { value: "https://tin-demo.example/dang-nhap" } });

    fireEvent.click(screen.getByRole("button", { name: /Lấy nội dung từ liên kết/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Trang DEMO yêu cầu đăng nhập; không trích xuất nội dung.");
    });

    // Cho phép người dùng nhập văn bản vào textarea
    const textarea = screen.getByPlaceholderText(/Dán toàn bộ văn bản tin tuyển dụng/i);
    fireEvent.change(textarea, { target: { value: "Nội dung copy thủ công sau khi đăng nhập." } });
    expect(textarea).toHaveValue("Nội dung copy thủ công sau khi đăng nhập.");
  });
});
