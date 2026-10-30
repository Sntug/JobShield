import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AnalysisResults } from "@/components/analysis/analysis-results";
import { AnalysisResponse } from "@/types/api";

const mockAnalysis: AnalysisResponse = {
  id: "test-uuid-12345",
  risk_label_vi: "Rủi ro cao",
  verification_label_vi: "Chưa xác minh",
  finding_vi: "Có yêu cầu thanh toán rõ trong tin tuyển dụng.",
  job: {
    company_name: "Công ty Mẫu Thu Phí",
    job_title: "Nhân viên nhập liệu",
    salary: "8 triệu đồng/tháng",
    location: "online",
    employment_type: "bán thời gian",
    contact_email: "nhanviec@thu-phi.invalid",
    contact_phone: null,
    recruitment_website: null,
    application_requirements: null,
    required_payments: "đóng phí tuyển dụng 500.000 đồng để nhận việc",
    suspicious_instructions: null,
  },
  indicators: [
    {
      category_vi: "Phí tuyển dụng trước",
      rule_id: "RULE_UPFRONT_FEE",
      matched_quote: "đóng phí tuyển dụng 500.000 đồng để nhận việc",
    },
  ],
  evidence: {
    matched_sources: [],
    missing_vi: ["Nguồn nhà tuyển dụng đã xác minh"],
    limitations_vi: ["Dữ liệu tổng hợp DEMO."],
    is_demo: true,
  },
  actions_vi: ["Tạm dừng thanh toán phí hoặc đặt cọc."],
  engine_version: "0.1.0",
  rules_version: "2026.10",
  created_at: "2026-10-17T15:00:00Z",
  expires_at: "2026-10-18T15:00:00Z",
};

describe("AnalysisResults", () => {
  it("explains that no indicators do not establish safety", () => {
    render(<AnalysisResults analysis={{ ...mockAnalysis, indicators: [], risk_label_vi: "Không đủ thông tin" }} onReset={vi.fn()} />);
    expect(screen.getByText(/Chưa phát hiện dấu hiệu cảnh báo trong văn bản/i)).toBeInTheDocument();
    expect(screen.getByText(/không chứng minh tin tuyển dụng an toàn/i)).toBeInTheDocument();
  });

  it("labels demo sources independently of the overall analysis", () => {
    render(<AnalysisResults analysis={{ ...mockAnalysis, evidence: {
      ...mockAnalysis.evidence, is_demo: false,
      matched_sources: [{ id: "demo-source", label_vi: "Nguồn mẫu", is_demo: true }],
    } }} onReset={vi.fn()} />);
    expect(screen.getByText(/Nguồn DEMO/i)).toBeInTheDocument();
  });

  it("makes missing extracted fields explicit", () => {
    render(<AnalysisResults analysis={mockAnalysis} onReset={vi.fn()} />);
    expect(screen.getAllByText("Chưa có thông tin").length).toBeGreaterThan(0);
  });

  it("renders risk badges, finding, indicators with verbatim quote, and 11 fields", () => {
    const handleReset = vi.fn();
    render(<AnalysisResults analysis={mockAnalysis} onReset={handleReset} />);

    expect(screen.getByText(/Mức độ: Rủi ro cao/i)).toBeInTheDocument();
    expect(screen.getByText(/Xác minh: Chưa xác minh/i)).toBeInTheDocument();
    expect(screen.getByText(/Dữ liệu DEMO/i)).toBeInTheDocument();
    expect(screen.getByText("Có yêu cầu thanh toán rõ trong tin tuyển dụng.")).toBeInTheDocument();

    // Verbatim quote (appears in indicator badge and required_payments field)
    const quotes = screen.getAllByText(/đóng phí tuyển dụng 500.000 đồng để nhận việc/i);
    expect(quotes.length).toBeGreaterThanOrEqual(1);

    // 11 fields
    expect(screen.getByText("Công ty Mẫu Thu Phí")).toBeInTheDocument();
    expect(screen.getByText("Nhân viên nhập liệu")).toBeInTheDocument();
    expect(screen.getByText("8 triệu đồng/tháng")).toBeInTheDocument();

    // Missing info & unverified source
    expect(screen.getByText("Nguồn nhà tuyển dụng đã xác minh")).toBeInTheDocument();
    expect(screen.getByText(/Chưa xác minh qua nguồn độc lập/i)).toBeInTheDocument();

    // Action
    expect(screen.getByText("Tạm dừng thanh toán phí hoặc đặt cọc.")).toBeInTheDocument();

    // Reset button
    const resetBtn = screen.getByRole("button", { name: /Phân tích tin khác/i });
    fireEvent.click(resetBtn);
    expect(handleReset).toHaveBeenCalledTimes(1);
  });

  it("renders AI semantic analysis card when ai_insights is success", () => {
    const analysisWithAi: AnalysisResponse = {
      ...mockAnalysis,
      ai_insights: {
        status: "success",
        provider: "gemini",
        model: "gemini-2.5-flash",
        semantic_summary_vi: "Tin có dấu hiệu lừa đảo cộng tác viên nạp tiền.",
        suspicious_patterns_vi: [
            "Hứa hẹn thu nhập cao bất thường",
            "Yêu cầu nạp tiền",
        ],
        reasoning_vi: "Mô hình nhiệm vụ nạp tiền lừa đảo tiền cọc.",
        confidence_note_vi: "Đánh giá sơ bộ.",
        limitations_vi: ["Không thay thế thẩm tra pháp lý."],
      },
    };

    render(<AnalysisResults analysis={analysisWithAi} onReset={vi.fn()} />);

    expect(screen.getByTestId("ai-insights-card")).toBeInTheDocument();
    expect(screen.getByText(/AI Hoạt động/i)).toBeInTheDocument();
    expect(screen.getByText("Tin có dấu hiệu lừa đảo cộng tác viên nạp tiền.")).toBeInTheDocument();
    expect(screen.getByText("Hứa hẹn thu nhập cao bất thường")).toBeInTheDocument();
    expect(screen.getByText("Mô hình nhiệm vụ nạp tiền lừa đảo tiền cọc.")).toBeInTheDocument();
  });

  it("renders fallback notice when ai_insights has fallback_no_consent", () => {
    const analysisWithFallback: AnalysisResponse = {
      ...mockAnalysis,
      ai_insights: {
        status: "fallback_no_consent",
        suspicious_patterns_vi: [],
        limitations_vi: ["Người dùng chưa đồng ý gửi dữ liệu ra ngoài."],
      },
    };

    render(<AnalysisResults analysis={analysisWithFallback} onReset={vi.fn()} />);

    expect(screen.getByTestId("ai-insights-card")).toBeInTheDocument();
    expect(screen.getByText(/Chưa cấp quyền AI \(Quy tắc chuẩn\)/i)).toBeInTheDocument();
    expect(screen.getByText("Người dùng chưa đồng ý gửi dữ liệu ra ngoài.")).toBeInTheDocument();
  });
});
