import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VerificationResults } from "@/components/employers/verification-results";
import { VerificationResponse } from "@/types/api";

const result: VerificationResponse = {
  request_id: "test-request", verification_label_vi: "Chưa xác minh", summary_vi: "Khớp một phần, chưa đủ căn cứ.",
  findings_vi: ["Tài khoản chưa có nguồn đối chiếu."],
  field_checks: [
    { field: "contact_email", status: "matched", reason_vi: "Email khớp nguồn.", source_ids: ["source-test"] },
    { field: "bank_account", status: "unverified", reason_vi: "Chưa có căn cứ về tài khoản.", source_ids: [] },
  ],
  matched_sources: [{ id: "source-test", url: "https://mau.example/careers", label_vi: "Nguồn tổng hợp kiểm thử", verified_at: "2026-10-20T00:00:00Z", source_revision: 2, evidence_excerpt_vi: "Email được doanh nghiệp công bố." }],
  missing_fields_vi: ["Nguồn liên kết tài khoản với doanh nghiệp"], limitations_vi: ["Khớp nguồn không xác nhận tin tuyển dụng thật hoặc an toàn."],
  recommended_actions_vi: ["Xác nhận vị trí qua kênh độc lập."], verification_version: "1.2.0", checked_at: "2026-10-26T00:00:00Z",
};

describe("VerificationResults", () => {
  it("shows partial checks, provenance, missing information and limits separately", () => {
    render(<VerificationResults result={result} onReset={vi.fn()} />);
    expect(screen.getByRole("heading", { name: "Chưa xác minh" })).toBeInTheDocument();
    expect(screen.getByText("Chưa có căn cứ về tài khoản.")).toBeInTheDocument();
    expect(screen.getByText("Nguồn liên kết tài khoản với doanh nghiệp")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Mở nguồn: Nguồn tổng hợp kiểm thử" })).toHaveAttribute("href", "https://mau.example/careers");
    expect(screen.getByText(/Phiên bản nguồn: 2/)).toBeInTheDocument();
    expect(screen.getByText(/không xác nhận tin tuyển dụng thật hoặc an toàn/i)).toBeInTheDocument();
  });
  it("does not fabricate source evidence when no source exists", () => {
    render(<VerificationResults result={{ ...result, matched_sources: [], field_checks: [] }} onReset={vi.fn()} />);
    expect(screen.getByText(/Chưa có nguồn độc lập đủ căn cứ đối chiếu/i)).toBeInTheDocument();
  });
});
