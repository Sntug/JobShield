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
  weight?: number | null;
  explanation_vi?: string | null;
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

// R4: Community Reports, Moderation, Public Warnings, Risk Indicators, Admin Stats

export type EvidenceType = "text" | "url" | "image";

export interface ReportEvidence {
  id: string;
  evidence_type: EvidenceType;
  content?: string | null;
  source_url?: string | null;
  file_name?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  created_at: string;
}

export interface ReportEvidenceCreate {
  evidence_type: EvidenceType;
  content?: string;
  source_url?: string;
  storage_key?: string;
  file_name?: string;
  mime_type?: string;
  size_bytes?: number;
}

export interface ModerationAction {
  id: string;
  action_type: "review" | "request_evidence" | "verify" | "reject";
  from_status: string;
  to_status: string;
  decision_summary: string;
  created_at: string;
}

export interface ModerationActionAdmin extends ModerationAction {
  moderator_id: string;
  moderator_name?: string | null;
  report_version_after: number;
  reviewed_evidence_ids?: string[] | null;
  private_note?: string | null;
}

export interface Report {
  id: string;
  reason: string;
  description: string;
  status: "pending" | "under_review" | "verified" | "rejected";
  version: number;
  analysis_id?: string | null;
  created_at: string;
  updated_at: string;
  evidences: ReportEvidence[];
  moderation_actions: ModerationAction[];
}

export interface ReportCreate {
  reason: string;
  description: string;
  analysis_id?: string | null;
  evidences?: ReportEvidenceCreate[];
}

export interface ReportListResponse {
  items: Report[];
  total: number;
  page: number;
  page_size: number;
}

export interface ReportAdmin extends Report {
  reporter_id?: string | null;
  reporter_email?: string | null;
  reporter_name?: string | null;
  moderation_actions: ModerationActionAdmin[];
}

export interface ReportAdminListResponse {
  items: ReportAdmin[];
  total: number;
  page: number;
  page_size: number;
}

export interface ModerationActionCreate {
  action_type: "review" | "request_evidence" | "verify" | "reject";
  to_status: "pending" | "under_review" | "verified" | "rejected";
  decision_summary: string;
  private_note?: string | null;
  expected_version: number;
  reviewed_evidence_ids?: string[] | null;
}

export interface RiskIndicator {
  id: string;
  code: string;
  name: string;
  description: string;
  explanation_vi: string;
  weight: number;
  enabled: boolean;
  updated_at: string;
}

export interface RiskIndicatorListResponse {
  items: RiskIndicator[];
}

export interface RiskIndicatorUpdateRequest {
  enabled?: boolean;
  weight?: number;
  description?: string;
}

export interface EmployerAdmin {
  id: string;
  legal_name: string;
  tax_id?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  sources_count: number;
}

export interface EmployerAdminCreate {
  legal_name: string;
  tax_id?: string | null;
}

export interface EmployerAdminUpdate {
  legal_name?: string;
  tax_id?: string | null;
  is_active?: boolean;
}

export interface EmployerAdminListResponse {
  items: EmployerAdmin[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminStats {
  total_users: number;
  total_analyses: number;
  total_reports: number;
  pending_reports: number;
  under_review_reports: number;
  verified_reports: number;
  rejected_reports: number;
  total_verified_employers: number;
  total_warnings: number;
  active_warnings: number;
  risk_distribution: Record<string, number>;
  report_status_distribution: Record<string, number>;
}

export interface PublicWarning {
  id: string;
  revision: number;
  status: "published" | "superseded" | "withdrawn";
  title_vi: string;
  public_summary_vi: string;
  public_sources_snapshot: Array<Record<string, unknown>>;
  published_at?: string | null;
  created_at: string;
  previous_warning_id?: string | null;
  next_warning_id?: string | null;
  withdrawn_at?: string | null;
  withdrawal_reason_vi?: string | null;
}

export interface PublicWarningListResponse {
  items: PublicWarning[];
  total: number;
  page: number;
  page_size: number;
}

export interface PublicWarningCreate {
  title_vi: string;
  public_summary_vi: string;
  report_id?: string | null;
  decision_id?: string | null;
  public_sources_snapshot?: Array<Record<string, unknown>>;
}

export interface PublicWarningSupersede {
  title_vi: string;
  public_summary_vi: string;
  public_sources_snapshot?: Array<Record<string, unknown>>;
}

export interface PublicWarningWithdraw {
  withdrawal_reason_vi: string;
}
