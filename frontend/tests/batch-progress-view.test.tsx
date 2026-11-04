import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BatchProgressView } from "@/components/analysis/batch-progress-view";
import { BatchAnalysisResponse } from "@/types/api";

const mockBatch: BatchAnalysisResponse = {
  id: "batch-uuid-12345",
  status: "processing",
  total_items: 4,
  processed_items: 2,
  created_at: "2026-11-03T10:00:00Z",
  items: [
    {
      id: "item-1",
      item_order: 1,
      input_type: "url",
      input_value: "https://example.com/job-1",
      status: "success",
      analysis_id: "analysis-1",
      analysis: {
        id: "analysis-1",
        risk_label_vi: "Rủi ro cao",
        verification_label_vi: "Chưa xác minh",
        finding_vi: "Phát hiện dấu hiệu nạp tiền.",
        job: {
          company_name: "Công ty Lừa Đảo",
          job_title: "Cộng tác viên Shopee",
          salary: "1 triệu/ngày",
          location: "Tại nhà",
          employment_type: "Bán thời gian",
          contact_email: null,
          contact_phone: null,
          recruitment_website: null,
          application_requirements: null,
          required_payments: "Yêu cầu nạp tiền",
          suspicious_instructions: null,
        },
        indicators: [
          {
            category_vi: "Nạp tiền",
            rule_id: "RULE_DEPOSIT",
            matched_quote: "Yêu cầu nạp tiền",
          },
        ],
        evidence: {
          matched_sources: [],
          missing_vi: [],
          limitations_vi: [],
          is_demo: false,
        },
        actions_vi: ["Không nạp tiền."],
        engine_version: "1.0",
        rules_version: "2026.11",
        created_at: "2026-11-03T10:00:00Z",
      },
    },
    {
      id: "item-2",
      item_order: 2,
      input_type: "text",
      input_value: "Công ty Cổ phần Công nghệ An Toàn tuyển dụng Frontend Engineer lương thỏa thuận.",
      status: "processing",
    },
    {
      id: "item-3",
      item_order: 3,
      input_type: "url",
      input_value: "https://blocked.example/post",
      status: "error",
      error_message: "Không thể lấy nội dung từ đường dẫn (trang bị chặn hoặc lỗi mạng).",
    },
    {
      id: "item-4",
      item_order: 4,
      input_type: "text",
      input_value: "Nội dung đang chờ lượt xử lý...",
      status: "pending",
    },
  ],
};

describe("BatchProgressView", () => {
  it("renders visual progress bar and counter with correct aria attributes", () => {
    render(<BatchProgressView batch={mockBatch} isPolling={true} />);

    const progressbar = screen.getByRole("progressbar");
    expect(progressbar).toBeInTheDocument();
    expect(progressbar).toHaveAttribute("aria-valuenow", "50");
    expect(progressbar).toHaveAttribute("aria-valuemin", "0");
    expect(progressbar).toHaveAttribute("aria-valuemax", "100");

    expect(screen.getByText("Đã xử lý 2/4 tin")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
  });

  it("displays batch status badge correctly", () => {
    const { rerender } = render(<BatchProgressView batch={mockBatch} isPolling={true} />);
    expect(screen.getByTestId("batch-status-badge")).toHaveTextContent("Đang xử lý...");

    rerender(
      <BatchProgressView
        batch={{ ...mockBatch, status: "completed", processed_items: 4 }}
        isPolling={false}
      />
    );
    expect(screen.getByTestId("batch-status-badge")).toHaveTextContent("Hoàn thành");

    rerender(
      <BatchProgressView
        batch={{ ...mockBatch, status: "cancelled" }}
        isPolling={false}
      />
    );
    expect(screen.getByTestId("batch-status-badge")).toHaveTextContent("Đã hủy");

    rerender(
      <BatchProgressView
        batch={{ ...mockBatch, status: "failed" }}
        isPolling={false}
      />
    );
    expect(screen.getByTestId("batch-status-badge")).toHaveTextContent("Thất bại");
  });

  it("renders list of items with order numbers, previews, and respective badges", () => {
    render(<BatchProgressView batch={mockBatch} />);

    // Item 1: Success
    expect(screen.getByText("Cộng tác viên Shopee")).toBeInTheDocument();
    expect(screen.getByText("Công ty Lừa Đảo")).toBeInTheDocument();
    expect(screen.getByText("Rủi ro cao")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Xem chi tiết" })).toBeInTheDocument();

    // Item 2: Processing
    expect(screen.getByText(/Công nghệ An Toàn tuyển dụng/)).toBeInTheDocument();
    expect(screen.getAllByText("Đang xử lý...").length).toBeGreaterThanOrEqual(1);

    // Item 3: Error
    expect(
      screen.getByText("Không thể lấy nội dung từ đường dẫn (trang bị chặn hoặc lỗi mạng).")
    ).toBeInTheDocument();

    // Item 4: Pending
    expect(screen.getByText("Đang chờ")).toBeInTheDocument();
  });

  it("toggles in-place detail view when clicking 'Xem chi tiết' and returns with 'Quay lại danh sách'", () => {
    render(<BatchProgressView batch={mockBatch} />);

    const viewDetailBtn = screen.getByRole("button", { name: "Xem chi tiết" });
    fireEvent.click(viewDetailBtn);

    // Should now show AnalysisResults for Item 1
    expect(screen.getByText("Phát hiện dấu hiệu nạp tiền.")).toBeInTheDocument();
    expect(screen.getByText(/Chi tiết tin #1/i)).toBeInTheDocument();

    // Back button in AnalysisResults or top nav
    const backBtn = screen.getAllByRole("button", { name: /Quay lại danh sách/i })[0];
    fireEvent.click(backBtn);

    // Should return to batch list
    expect(screen.getByText("Đã xử lý 2/4 tin")).toBeInTheDocument();
    expect(screen.getByText("Cộng tác viên Shopee")).toBeInTheDocument();
  });

  it("handles retry and fallback switch on error items", () => {
    const handleRetry = vi.fn();
    const handleSwitchToText = vi.fn();

    render(
      <BatchProgressView
        batch={mockBatch}
        onRetryItem={handleRetry}
        onSwitchToText={handleSwitchToText}
      />
    );

    const retryBtn = screen.getByRole("button", { name: /Thử lại/i });
    fireEvent.click(retryBtn);
    expect(handleRetry).toHaveBeenCalledWith(mockBatch.items[2]);

    const switchBtn = screen.getByRole("button", { name: /Dán văn bản thay thế/i });
    fireEvent.click(switchBtn);
    expect(handleSwitchToText).toHaveBeenCalledWith(mockBatch.items[2]);
  });

  it("shows 'Hủy lượt' button while active and calls onCancel", () => {
    const handleCancel = vi.fn();
    render(<BatchProgressView batch={mockBatch} isPolling={true} onCancel={handleCancel} />);

    const cancelBtn = screen.getByRole("button", { name: /Hủy lượt/i });
    fireEvent.click(cancelBtn);
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });

  it("shows a recoverable batch error and calls the manual retry action", () => {
    const handleRetry = vi.fn();
    render(
      <BatchProgressView
        batch={mockBatch}
        error="Không thể cập nhật trạng thái."
        onRetry={handleRetry}
      />
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Không thể cập nhật trạng thái.");
    fireEvent.click(screen.getByRole("button", { name: /Thử tải lại/i }));
    expect(handleRetry).toHaveBeenCalledTimes(1);
  });

  it("disables repeated cancellation while the cancel request is running", () => {
    render(
      <BatchProgressView batch={mockBatch} isPolling={true} isCancelling onCancel={vi.fn()} />
    );

    expect(screen.getByRole("button", { name: /Đang hủy/i })).toBeDisabled();
  });

  it("does not offer another cancel after cancellation while a started item settles", () => {
    render(
      <BatchProgressView
        batch={{ ...mockBatch, status: "cancelled" }}
        isPolling={true}
        onCancel={vi.fn()}
      />
    );

    expect(screen.queryByRole("button", { name: /Hủy lượt/i })).not.toBeInTheDocument();
  });

  it("shows 'Kiểm tra lượt mới' when batch is completed/cancelled and calls onReset", () => {
    const handleReset = vi.fn();
    render(
      <BatchProgressView
        batch={{ ...mockBatch, status: "completed", processed_items: 4 }}
        isPolling={false}
        onReset={handleReset}
      />
    );

    expect(screen.queryByRole("button", { name: /Hủy lượt/i })).not.toBeInTheDocument();

    const newBatchBtn = screen.getByRole("button", { name: /Kiểm tra lượt mới/i });
    fireEvent.click(newBatchBtn);
    expect(handleReset).toHaveBeenCalledTimes(1);
  });
});
