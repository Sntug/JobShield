import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReportForm } from "@/components/reports/report-form";
import * as apiClient from "@/lib/api-client";

const push = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ReportForm Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form elements with accessible labels", () => {
    renderWithClient(<ReportForm initialAnalysisId="test-analysis-123" />);

    expect(screen.getByLabelText(/Lý do báo cáo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Mô tả chi tiết sự việc/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Mã phân tích liên quan/i)).toHaveValue("test-analysis-123");
    expect(screen.getByRole("button", { name: "Gửi báo cáo" })).toBeInTheDocument();
  });

  it("validates description must be at least 5 characters", async () => {
    renderWithClient(<ReportForm />);

    fireEvent.change(screen.getByLabelText(/Mô tả chi tiết sự việc/i), {
      target: { value: "Ngắn" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Gửi báo cáo" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/ít nhất 5 ký tự/i);
  });

  it("allows adding and removing text and url evidence", () => {
    renderWithClient(<ReportForm />);

    // Thêm bằng chứng văn bản
    const evidenceInput = screen.getByLabelText("Nội dung bằng chứng");
    fireEvent.change(evidenceInput, {
      target: { value: "Ảnh chụp màn hình đòi 500k" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Thêm" }));

    expect(screen.getByText("Ảnh chụp màn hình đòi 500k")).toBeInTheDocument();

    // Thêm bằng chứng URL hợp lệ
    fireEvent.change(screen.getByLabelText("Loại bằng chứng"), {
      target: { value: "url" },
    });
    fireEvent.change(screen.getByLabelText("Nội dung bằng chứng"), {
      target: { value: "https://example.com/fake-job" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Thêm" }));

    expect(screen.getByText("https://example.com/fake-job")).toBeInTheDocument();

    // Xóa mục bằng chứng đầu tiên
    const deleteButtons = screen.getAllByRole("button", { name: "Xóa" });
    fireEvent.click(deleteButtons[0]);

    expect(screen.queryByText("Ảnh chụp màn hình đòi 500k")).not.toBeInTheDocument();
    expect(screen.getByText("https://example.com/fake-job")).toBeInTheDocument();
  });

  it("submits report with valid data and renders success feedback", async () => {
    const mockReport = {
      id: "report-uuid-999",
      reason: "Phí tuyển dụng trước (đồng phục, tài liệu, hồ sơ)",
      description: "Yêu cầu chuyển tiền đặt cọc 300k vào số tài khoản cá nhân.",
      status: "pending" as const,
      version: 1,
      analysis_id: null,
      created_at: "2026-10-28T10:00:00Z",
      updated_at: "2026-10-28T10:00:00Z",
      evidences: [],
      moderation_actions: [],
    };

    vi.spyOn(apiClient, "submitReport").mockResolvedValue(mockReport);

    renderWithClient(<ReportForm />);

    fireEvent.change(screen.getByLabelText(/Mô tả chi tiết sự việc/i), {
      target: { value: "Yêu cầu chuyển tiền đặt cọc 300k vào số tài khoản cá nhân." },
    });

    fireEvent.click(screen.getByRole("button", { name: "Gửi báo cáo" }));

    expect(await screen.findByText("Gửi báo cáo thành công!")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Xem danh sách báo cáo của tôi" })).toBeInTheDocument();
  });
});
