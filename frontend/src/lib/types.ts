/**
 * API types for the Applicant Validator.
 */

export interface Flag {
  id: string;
  flag_type_code: string;
  flag_type_name: string;
  category: string;
  severity: string;
  message: string;
  is_active: boolean;
  created_at: string;
}

export interface Posting {
  id: string;
  lever_posting_id: string;
  title: string;
  team: string | null;
  department: string | null;
  location: string | null;
  commitment: string | null;
  state: string | null;
}

export interface Applicant {
  id: string;
  lever_id: string;
  name: string;
  email: string;
  phone: string | null;
  location: string | null;
  risk_level: string | null;
  flag_count: number;
  opportunity_count: number;
  is_reviewed: boolean;
  reviewed_at: string | null;
  created_at: string;
  lever_created_at: string | null;
  flags: Flag[];
  sources: string[];
  assigned_ta: string | null;
}

export interface ApplicantDetail extends Applicant {
  linkedin_url: string | null;
  resume_url: string | null;
  validation_score: number | null;
  reviewed_by: string | null;
  updated_at: string;
  postings: Posting[];
}

export interface PaginatedApplicantsResponse {
  items: Applicant[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export type SortField = "created_at" | "updated_at" | "name" | "risk_level" | "flag_count" | "sources" | "assigned_ta" | "lever_created_at";
export type SortOrder = "asc" | "desc";
