/**
 * API client for the Applicant Validator backend.
 */

import type { PaginatedApplicantsResponse, SortField, SortOrder, ApplicantDetail } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

interface FetchApplicantsParams {
  page?: number;
  pageSize?: number;
  sortBy?: SortField;
  sortOrder?: SortOrder;
  riskLevel?: string;
  isReviewed?: boolean;
  assignedTa?: string;
  source?: string;
  flagType?: string;
}

export async function fetchApplicants({
  page = 1,
  pageSize = 20,
  sortBy = "created_at",
  sortOrder = "desc",
  riskLevel,
  isReviewed,
  assignedTa,
  source,
  flagType,
}: FetchApplicantsParams = {}): Promise<PaginatedApplicantsResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  if (riskLevel) {
    params.set("risk_level", riskLevel);
  }
  if (isReviewed !== undefined) {
    params.set("is_reviewed", isReviewed.toString());
  }
  if (assignedTa) {
    params.set("assigned_ta", assignedTa);
  }
  if (source) {
    params.set("source", source);
  }
  if (flagType) {
    params.set("flag_type", flagType);
  }

  const response = await fetch(`${API_BASE_URL}/applicants?${params.toString()}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch applicants: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchApplicant(applicantId: string): Promise<ApplicantDetail> {
  const response = await fetch(`${API_BASE_URL}/applicants/${applicantId}`);

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Applicant not found");
    }
    throw new Error(`Failed to fetch applicant: ${response.statusText}`);
  }

  return response.json();
}

export async function updateApplicantReviewed(
  applicantId: string,
  isReviewed: boolean,
  reviewedBy?: string
): Promise<ApplicantDetail> {
  const response = await fetch(`${API_BASE_URL}/applicants/${applicantId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      is_reviewed: isReviewed,
      reviewed_by: reviewedBy,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to update applicant: ${response.statusText}`);
  }

  return response.json();
}

// Sync API types and functions
export type SyncStatus = "idle" | "running" | "completed" | "failed";

export interface SyncStatusResponse {
  status: SyncStatus;
  progress: number;
  total: number;
  message: string;
  last_sync_at: string | null;
  last_sync_count: number;
  error: string | null;
}

export interface SyncResponse {
  message: string;
  status: SyncStatus;
}

export async function getSyncStatus(): Promise<SyncStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/sync/status`);

  if (!response.ok) {
    throw new Error(`Failed to get sync status: ${response.statusText}`);
  }

  return response.json();
}

export async function startSync(days: number): Promise<SyncResponse> {
  const response = await fetch(`${API_BASE_URL}/sync/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ days }),
  });

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error("Sync already in progress");
    }
    throw new Error(`Failed to start sync: ${response.statusText}`);
  }

  return response.json();
}

export async function getApplicantCount(): Promise<{ count: number }> {
  const response = await fetch(`${API_BASE_URL}/sync/count`);

  if (!response.ok) {
    throw new Error(`Failed to get applicant count: ${response.statusText}`);
  }

  return response.json();
}

export async function getTAs(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/applicants/tas`);

  if (!response.ok) {
    throw new Error(`Failed to fetch TAs: ${response.statusText}`);
  }

  const data = await response.json();
  return data.tas;
}

export async function getSources(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/applicants/sources`);

  if (!response.ok) {
    throw new Error(`Failed to fetch sources: ${response.statusText}`);
  }

  const data = await response.json();
  return data.sources;
}

// Flag Types for filtering
export interface FlagTypeOption {
  code: string;
  name: string;
  category: string;
}

export async function getFlagTypes(): Promise<FlagTypeOption[]> {
  const response = await fetch(`${API_BASE_URL}/applicants/flag-types`);

  if (!response.ok) {
    throw new Error(`Failed to fetch flag types: ${response.statusText}`);
  }

  const data = await response.json();
  return data.flag_types;
}

// Risk Levels for filtering
export async function getRiskLevels(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/applicants/risk-levels`);

  if (!response.ok) {
    throw new Error(`Failed to fetch risk levels: ${response.statusText}`);
  }

  const data = await response.json();
  return data.risk_levels;
}

// Validation Rules API
export interface ValidationRule {
  name: string;
  description: string;
  category: string;
  severity: string;
  version: string;
  checks_fields: string[];
  trigger_examples: string[];
  rationale: string;
  is_active: boolean;
}

export interface ValidationRulesResponse {
  rules: ValidationRule[];
  total: number;
}

export async function getValidationRules(): Promise<ValidationRulesResponse> {
  const response = await fetch(`${API_BASE_URL}/rules`);

  if (!response.ok) {
    throw new Error(`Failed to fetch validation rules: ${response.statusText}`);
  }

  return response.json();
}

// Validation Data API - Disposable Domains
export interface DisposableDomainsResponse {
  domains: string[];
  total: number;
}

export interface DisposableDomainsStatusResponse {
  data_type: string;
  last_sync: {
    id: string;
    source_name: string;
    completed_at: string;
    records_total: number;
  } | null;
  domain_count: number;
}

export async function getDisposableDomains(
  limit: number = 100,
  offset: number = 0
): Promise<DisposableDomainsResponse> {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  const response = await fetch(`${API_BASE_URL}/validation-data/disposable-domains?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch disposable domains: ${response.statusText}`);
  }

  return response.json();
}

export async function getDisposableDomainsStatus(): Promise<DisposableDomainsStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/validation-data/disposable-domains/status`);

  if (!response.ok) {
    throw new Error(`Failed to fetch status: ${response.statusText}`);
  }

  return response.json();
}

export async function addDisposableDomain(
  domain: string,
  notes?: string
): Promise<{ domain: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/validation-data/disposable-domains`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain, notes }),
  });

  if (!response.ok) {
    throw new Error(`Failed to add domain: ${response.statusText}`);
  }

  return response.json();
}

export async function removeDisposableDomain(
  domain: string
): Promise<{ domain: string; status: string }> {
  const response = await fetch(
    `${API_BASE_URL}/validation-data/disposable-domains/${encodeURIComponent(domain)}`,
    { method: "DELETE" }
  );

  if (!response.ok) {
    throw new Error(`Failed to remove domain: ${response.statusText}`);
  }

  return response.json();
}

export async function syncDisposableDomains(): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/validation-data/disposable-domains/sync`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Failed to start sync: ${response.statusText}`);
  }

  return response.json();
}

// Validation Data API - VoIP Carriers
export interface VoIPCarrier {
  id: string;
  name: string;
  match_type: string;
  confidence: string;
}

export interface VoIPCarriersResponse {
  carriers: VoIPCarrier[];
  total: number;
}

export async function getVoIPCarriers(): Promise<VoIPCarriersResponse> {
  const response = await fetch(`${API_BASE_URL}/validation-data/voip-carriers`);

  if (!response.ok) {
    throw new Error(`Failed to fetch VoIP carriers: ${response.statusText}`);
  }

  return response.json();
}

export async function addVoIPCarrier(
  name: string,
  matchType: string = "substring",
  confidence: string = "high",
  notes?: string
): Promise<{ domain: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/validation-data/voip-carriers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name,
      match_type: matchType,
      confidence,
      notes,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to add carrier: ${response.statusText}`);
  }

  return response.json();
}

// Validation Data API - VoIP Area Codes
export interface VoIPAreaCodesResponse {
  area_codes: string[];
  total: number;
}

export async function getVoIPAreaCodes(): Promise<VoIPAreaCodesResponse> {
  const response = await fetch(`${API_BASE_URL}/validation-data/voip-area-codes`);

  if (!response.ok) {
    throw new Error(`Failed to fetch VoIP area codes: ${response.statusText}`);
  }

  return response.json();
}

export async function seedValidationData(): Promise<{
  status: string;
  voip_carriers: { carriers_added: number };
  voip_area_codes: { area_codes_added: number };
}> {
  const response = await fetch(`${API_BASE_URL}/validation-data/seed-all`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Failed to seed data: ${response.statusText}`);
  }

  return response.json();
}

// Integration Settings API
export interface IntegrationSetting {
  provider: string;
  display_name: string;
  is_enabled: boolean;
  has_credentials: boolean;
  api_key_masked: string | null;
  api_secret_masked: string | null;
  account_id: string | null;
  fraud_score_threshold: number | null;
  monthly_usage: number;
  monthly_limit: number | null;
  last_test_at: string | null;
  last_test_success: boolean | null;
  last_test_message: string | null;
  notes: string | null;
  config_json: string | null;
}

export interface IntegrationListResponse {
  integrations: IntegrationSetting[];
}

export interface UpdateIntegrationRequest {
  is_enabled?: boolean;
  api_key?: string;
  api_secret?: string;
  account_id?: string;
  fraud_score_threshold?: number;
  notes?: string;
  config_json?: string;
}

export interface TestIntegrationResponse {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
}

export async function getIntegrations(): Promise<IntegrationListResponse> {
  const response = await fetch(`${API_BASE_URL}/settings/integrations`);

  if (!response.ok) {
    throw new Error(`Failed to fetch integrations: ${response.statusText}`);
  }

  return response.json();
}

export async function getIntegration(provider: string): Promise<IntegrationSetting> {
  const response = await fetch(`${API_BASE_URL}/settings/integrations/${provider}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch integration: ${response.statusText}`);
  }

  return response.json();
}

export async function updateIntegration(
  provider: string,
  data: UpdateIntegrationRequest
): Promise<IntegrationSetting> {
  const response = await fetch(`${API_BASE_URL}/settings/integrations/${provider}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update integration: ${response.statusText}`);
  }

  return response.json();
}

export async function testIntegration(provider: string): Promise<TestIntegrationResponse> {
  const response = await fetch(`${API_BASE_URL}/settings/integrations/${provider}/test`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Failed to test integration: ${response.statusText}`);
  }

  return response.json();
}

export async function resetIntegrationUsage(provider: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE_URL}/settings/integrations/${provider}/reset-usage`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Failed to reset usage: ${response.statusText}`);
  }

  return response.json();
}

// Re-validation API types and functions
export type RevalidateStatus = "idle" | "running" | "completed" | "failed";

export interface RevalidateStatusResponse {
  status: RevalidateStatus;
  progress: number;
  total: number;
  message: string;
  last_run_at: string | null;
  error: string | null;
  applicants_processed: number;
  flags_raised: number;
  flags_cleared: number;
  risk_level_changes: number;
  current_applicant_name: string | null;
}

export interface RevalidateRequest {
  days?: number;
  clear_existing_flags?: boolean;
}

export interface RevalidateResponse {
  message: string;
  status: RevalidateStatus;
}

export async function getRevalidateStatus(): Promise<RevalidateStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/revalidate/status`);

  if (!response.ok) {
    throw new Error(`Failed to get revalidation status: ${response.statusText}`);
  }

  return response.json();
}

export async function startRevalidation(request: RevalidateRequest = {}): Promise<RevalidateResponse> {
  const response = await fetch(`${API_BASE_URL}/revalidate/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      days: request.days || null,
      clear_existing_flags: request.clear_existing_flags !== false, // default true
    }),
  });

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error("Re-validation already in progress");
    }
    throw new Error(`Failed to start re-validation: ${response.statusText}`);
  }

  return response.json();
}

// Admin API types and functions
export type PurgeStatus = "idle" | "running" | "completed" | "failed";

export interface DatabaseStatsResponse {
  applicants_count: number;
  flags_count: number;
  validation_runs_count: number;
  flag_types_count: number;
  linkedin_profiles_count: number;
}

export interface PurgeStatusResponse {
  status: PurgeStatus;
  message: string;
  last_run_at: string | null;
  error: string | null;
  applicants_deleted: number;
  flags_deleted: number;
  validation_runs_deleted: number;
}

export interface PurgeRequest {
  confirm: boolean;
  keep_flag_types?: boolean;
}

export interface PurgeResponse {
  message: string;
  status: PurgeStatus;
}

export async function getDatabaseStats(): Promise<DatabaseStatsResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/stats`);

  if (!response.ok) {
    throw new Error(`Failed to get database stats: ${response.statusText}`);
  }

  return response.json();
}

export async function getPurgeStatus(): Promise<PurgeStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/purge/status`);

  if (!response.ok) {
    throw new Error(`Failed to get purge status: ${response.statusText}`);
  }

  return response.json();
}

export async function purgeDatabase(request: PurgeRequest): Promise<PurgeResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/purge`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      confirm: request.confirm,
      keep_flag_types: request.keep_flag_types !== false, // default true
    }),
  });

  if (!response.ok) {
    if (response.status === 409) {
      throw new Error("Purge already in progress");
    }
    if (response.status === 400) {
      throw new Error("Must confirm purge operation");
    }
    throw new Error(`Failed to start purge: ${response.statusText}`);
  }

  return response.json();
}

// Single Applicant Validation API
export interface ValidateApplicantResponse {
  applicant: ApplicantDetail;
  rules_passed: number;
  rules_failed: number;
  rules_skipped: number;
  flags_raised: number;
  previous_risk_level: string | null;
  new_risk_level: string | null;
  message: string;
}

export async function validateApplicant(applicantId: string): Promise<ValidateApplicantResponse> {
  const response = await fetch(`${API_BASE_URL}/applicants/${applicantId}/validate`, {
    method: "POST",
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error("Applicant not found");
    }
    throw new Error(`Failed to validate applicant: ${response.statusText}`);
  }

  return response.json();
}

// Validation Settings API
export interface ValidationSettingsResponse {
  mass_applicant_threshold: number;
}

export interface UpdateValidationSettingsRequest {
  mass_applicant_threshold?: number;
}

export async function getValidationSettings(): Promise<ValidationSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/settings/validation`);

  if (!response.ok) {
    throw new Error(`Failed to fetch validation settings: ${response.statusText}`);
  }

  return response.json();
}

export async function updateValidationSettings(
  data: UpdateValidationSettingsRequest
): Promise<ValidationSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/settings/validation`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update validation settings: ${response.statusText}`);
  }

  return response.json();
}

// Auth Settings API
export interface AuthSettingsResponse {
  auth_allowed_domain: string;
  auth_jwt_expiry_hours: string;
  auth_cookie_name: string;
  auth_cookie_secure: string;
  auth_min_password_length: string;
}

export interface UpdateAuthSettingsRequest {
  auth_allowed_domain?: string;
  auth_jwt_expiry_hours?: string;
  auth_cookie_name?: string;
  auth_cookie_secure?: string;
  auth_min_password_length?: string;
}

export async function getAuthSettings(): Promise<AuthSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/auth-settings`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch auth settings: ${response.statusText}`);
  }

  return response.json();
}

export async function updateAuthSettings(
  data: UpdateAuthSettingsRequest
): Promise<AuthSettingsResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/auth-settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error(`Failed to update auth settings: ${response.statusText}`);
  }

  return response.json();
}
