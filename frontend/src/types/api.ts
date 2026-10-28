/**
 * Schema types matching JobShield backend API contract.
 */

export interface JobExtracted {
  company_name: string | null;
  job_title: string | null;
  salary: string | null;
  location: string | null;
  employment_type: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  recruitment_website: string | null;
  application_requirements: string | null;
  required_payments: string | null;
  suspicious_instructions: string | null;
}

export interface IndicatorItem {
  category_vi: string;
  rule_id: string;
  matched_quote: string;
}

export interface MatchedSource {
  source_revision?: number;
  evidence_excerpt_vi?: string;
  id?: string;
  url?: string;
  label_vi?: string;
  verified_at?: string;
  is_demo?: boolean;
}

export interface EvidenceData {
  matched_sources: MatchedSource[];
  missing_vi?: string[];
  limitations_vi?: string[];
  is_demo: boolean;
}

export interface AnalysisResponse {
  id: string;
  guest_session_token?: string | null;
  risk_label_vi: string;
  verification_label_vi: string;
  finding_vi: string;
  job: JobExtracted;
  indicators: IndicatorItem[];
  evidence: EvidenceData;
  actions_vi: string[];
  engine_version: string;
  rules_version: string;
  created_at: string;
  expires_at?: string | null;
  is_saved?: boolean;
}

export interface AnalysisListResponse {
  items: AnalysisResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface AnalysisCreate {
  text: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface ClaimGuestResponse {
  claimed_count: number;
  claimed_ids: string[];
}

export interface UserStats {
  total_analyses: number;
  saved_analyses: number;
  risk_distribution: Record<string, number>;
}

export interface SavedAnalysisItem {
  analysis_id: string;
  saved_at: string;
  analysis: AnalysisResponse;
}

export interface SavedAnalysisListResponse {
  items: SavedAnalysisItem[];
  total: number;
  page: number;
  page_size: number;
}

export type VerificationField = "company_name" | "tax_id" | "contact_email" | "recruitment_website" | "social_channel_url" | "bank_account";

export interface VerificationCreate {
  company_name?: string;
  tax_id?: string;
  contact_email?: string;
  recruitment_website?: string;
  social_channel_url?: string;
  bank_account?: { account_number: string; bank_name: string; account_holder: string };
}

export interface VerificationFieldCheck {
  field: VerificationField;
  status: "matched" | "conflicting" | "unverified";
  reason_vi: string;
  source_ids: string[];
}

export interface VerificationResponse {
  request_id: string;
  verification_label_vi: "Khớp nguồn đã xác minh" | "Thông tin xung đột" | "Chưa xác minh" | "Không đủ dữ liệu";
  summary_vi: string;
  findings_vi: string[];
  field_checks: VerificationFieldCheck[];
  matched_sources: Array<Required<Pick<MatchedSource, "id" | "url" | "label_vi" | "verified_at">> & { source_revision: number; evidence_excerpt_vi: string }>;
  missing_fields_vi: string[];
  limitations_vi: string[];
  recommended_actions_vi: string[];
  verification_version: string;
  checked_at: string;
}

export interface ExtractionResponse {
  request_id: string;
  success: boolean;
  source_type: "image" | "url";
  text: string | null;
  failure_vi: string | null;
  source_name?: string | null;
  confidence?: number | null;
}

export interface URLExtractionRequest {
  url: string;
}

export interface ImageExtractionRequest {
  image_base64: string;
  filename?: string;
  content_type?: string;
}
