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
  expires_at: string;
}

export interface AnalysisCreate {
  text: string;
}
