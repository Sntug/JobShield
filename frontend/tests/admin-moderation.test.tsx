import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ModerationForm } from "@/components/admin/moderation-form";
import * as apiClient from "@/lib/api-client";
import { ReportAdmin } from "@/types/api";

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe("ModerationForm Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const sampleReport: ReportAdmin = {
    id: "rep-1234-5678-90ab",
    reason: "Thu phí trước",
    description: "Bắt chuyển 500k",
    status: "pending",
    version: 1,
    analysis_id: null,
    created_at: "2026-10-28T09:00:00Z",
    updated_at: "2026-10-28T09:00:00Z",
    evidences: [],
    moderation_actions: [],
    reporter_id: "user-1",
    reporter_email: "reporter@example.com",
    reporter_name: "Nguyễn Văn B",
  };

  it("renders moderation options, current version, and validates decision summary", async () => {
    renderWithClient(
      <ModerationForm
        report={sampleReport}
        onSuccess={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByText(/Xác nhận có rủi ro/i)).toBeInTheDocument();
    expect(screen.getByText(/Từ chối báo cáo/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Lưu quyết định kiểm duyệt" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/tóm tắt quyết định/i);
  });

  it("submits moderation with expected_version and triggers onSuccess", async () => {
    const onSuccess = vi.fn();
    const moderateSpy = vi.spyOn(apiClient, "moderateReport").mockResolvedValue({
      ...sampleReport,
      status: "verified",
      version: 2,
    });

    renderWithClient(
      <ModerationForm
        report={sampleReport}
        onSuccess={onSuccess}
        onCancel={vi.fn()}
      />
    );

    fireEvent.change(screen.getByLabelText(/Tóm tắt quyết định/i), {
      target: { value: "Đã xác nhận dấu hiệu thu phí trái quy định." },
    });
    fireEvent.change(screen.getByLabelText(/Ghi chú nội bộ/i), {
      target: { value: "IP nghi vấn" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Lưu quyết định kiểm duyệt" }));

    await waitFor(() => {
      expect(moderateSpy).toHaveBeenCalledWith("rep-1234-5678-90ab", {
        action_type: "verify",
        to_status: "verified",
        decision_summary: "Đã xác nhận dấu hiệu thu phí trái quy định.",
        private_note: "IP nghi vấn",
        expected_version: 1,
      });
      expect(onSuccess).toHaveBeenCalled();
    });
  });

  it("displays conflict error when another moderator modified the report", async () => {
    vi.spyOn(apiClient, "moderateReport").mockRejectedValue(
      new Error(
        "Xung đột phiên bản: Báo cáo đã được cập nhật bởi quản trị viên khác. Vui lòng làm mới trang."
      )
    );

    renderWithClient(
      <ModerationForm
        report={sampleReport}
        onSuccess={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    fireEvent.change(screen.getByLabelText(/Tóm tắt quyết định/i), {
      target: { value: "Xác minh" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Lưu quyết định kiểm duyệt" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/Xung đột phiên bản/i);
  });
});
