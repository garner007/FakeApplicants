"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { fetchApplicant, updateApplicantReviewed, validateApplicant } from "@/lib/api";
import { getRiskBadgeVariant, formatDate } from "@/lib/utils";
import type { ApplicantDetail, Flag } from "@/lib/types";

// getSeverityBadgeVariant uses the same logic as getRiskBadgeVariant
const getSeverityBadgeVariant = getRiskBadgeVariant;

// formatDateLong uses "long" month format for this page
const formatDateLong = (dateString: string) => formatDate(dateString, "long");

function FlagCard({ flag }: { flag: Flag }) {
  return (
    <div className="border rounded-lg p-4 bg-white">
      <div className="flex items-start justify-between mb-2">
        <div>
          <h4 className="font-medium text-gray-900">{flag.flag_type_name}</h4>
          <p className="text-sm text-gray-500">{flag.category}</p>
        </div>
        <Badge variant={getSeverityBadgeVariant(flag.severity)}>
          {flag.severity}
        </Badge>
      </div>
      <p className="text-sm text-gray-700 mt-2">{flag.message}</p>
      <p className="text-xs text-gray-400 mt-2">
        Flagged: {formatDateLong(flag.created_at)}
      </p>
    </div>
  );
}

export default function ApplicantDetailPage() {
  const params = useParams();
  const router = useRouter();
  const applicantId = params.id as string;

  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{
    message: string;
    type: "success" | "warning" | "info";
  } | null>(null);

  const loadApplicant = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchApplicant(applicantId);
      setApplicant(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load applicant");
    } finally {
      setLoading(false);
    }
  }, [applicantId]);

  useEffect(() => {
    loadApplicant();
  }, [loadApplicant]);

  const handleReviewedChange = async (checked: boolean) => {
    if (!applicant) return;
    setUpdating(true);
    try {
      const updated = await updateApplicantReviewed(applicant.id, checked);
      setApplicant(updated);
    } catch (err) {
      console.error("Failed to update:", err);
    } finally {
      setUpdating(false);
    }
  };

  const handleValidate = async () => {
    if (!applicant) return;
    setValidating(true);
    setValidationResult(null);
    try {
      const result = await validateApplicant(applicant.id);
      setApplicant(result.applicant);

      // Determine result type based on flags
      let resultType: "success" | "warning" | "info" = "success";
      if (result.flags_raised > 0) {
        resultType = result.new_risk_level === "critical" || result.new_risk_level === "high"
          ? "warning"
          : "info";
      }

      setValidationResult({
        message: `${result.message} (${result.rules_passed} passed, ${result.rules_failed} failed, ${result.rules_skipped} skipped)`,
        type: resultType,
      });

      // Auto-hide success messages after 5 seconds
      if (resultType === "success") {
        setTimeout(() => setValidationResult(null), 5000);
      }
    } catch (err) {
      setValidationResult({
        message: err instanceof Error ? err.message : "Failed to validate applicant",
        type: "warning",
      });
    } finally {
      setValidating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="flex items-center justify-center h-64">
          <p className="text-gray-500">Loading applicant...</p>
        </div>
      </div>
    );
  }

  if (error || !applicant) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="container mx-auto py-8 px-4">
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-700">{error || "Applicant not found"}</p>
            <Button variant="outline" className="mt-4" onClick={() => router.push("/")}>
              Back to List
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const activeFlags = applicant.flags.filter((f) => f.is_active);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container mx-auto py-8 px-4 max-w-4xl">

        {/* Main Card */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{applicant.name}</h1>
              <p className="text-gray-500 mt-1">{applicant.email}</p>
            </div>
            <div className="flex items-center gap-4">
              {applicant.risk_level && (
                <Badge variant={getRiskBadgeVariant(applicant.risk_level)} className="text-sm px-3 py-1">
                  {applicant.risk_level.toUpperCase()} RISK
                </Badge>
              )}
              <Button
                onClick={handleValidate}
                disabled={validating}
                size="sm"
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {validating ? "Validating..." : "Validate"}
              </Button>
            </div>
          </div>

          {/* Validation Result Banner */}
          {validationResult && (
            <div
              className={`mb-6 p-4 rounded-md flex items-center justify-between ${
                validationResult.type === "success"
                  ? "bg-green-50 border border-green-200"
                  : validationResult.type === "warning"
                  ? "bg-yellow-50 border border-yellow-200"
                  : "bg-blue-50 border border-blue-200"
              }`}
            >
              <p
                className={`text-sm ${
                  validationResult.type === "success"
                    ? "text-green-700"
                    : validationResult.type === "warning"
                    ? "text-yellow-700"
                    : "text-blue-700"
                }`}
              >
                {validationResult.message}
              </p>
              <button
                onClick={() => setValidationResult(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                &times;
              </button>
            </div>
          )}

          {/* Info Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-3">Contact Information</h3>
              <dl className="space-y-2">
                <div>
                  <dt className="text-xs text-gray-400">Email</dt>
                  <dd className="text-sm text-gray-900">{applicant.email}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Phone</dt>
                  <dd className="text-sm text-gray-900">
                    {applicant.phone || <span className="text-gray-400 italic">None provided</span>}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Location</dt>
                  <dd className="text-sm text-gray-900">
                    {applicant.location || <span className="text-gray-400 italic">None provided</span>}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">LinkedIn</dt>
                  <dd className="text-sm">
                    {applicant.linkedin_url ? (
                      <a
                        href={applicant.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        View Profile
                      </a>
                    ) : (
                      <span className="text-gray-400 italic">None provided</span>
                    )}
                  </dd>
                </div>
              </dl>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-3">Validation Details</h3>
              <dl className="space-y-2">
                <div>
                  <dt className="text-xs text-gray-400">Validation Score</dt>
                  <dd className="text-sm text-gray-900">
                    {applicant.validation_score !== null ? `${applicant.validation_score}%` : "N/A"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Active Flags</dt>
                  <dd className="text-sm text-gray-900">{activeFlags.length}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Jobs Applied</dt>
                  <dd className={`text-sm ${applicant.opportunity_count >= 5 ? "text-orange-600 font-medium" : "text-gray-900"}`}>
                    {applicant.opportunity_count}
                    {applicant.opportunity_count >= 5 && (
                      <span className="ml-2 text-xs text-orange-500">(Mass applicant)</span>
                    )}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400">Lever Profile</dt>
                  <dd className="text-sm">
                    <a
                      href={`https://hire.lever.co/candidates/${applicant.lever_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      View in Lever
                    </a>
                  </dd>
                </div>
                {applicant.resume_url && (
                  <div>
                    <dt className="text-xs text-gray-400">Resume</dt>
                    <dd className="text-sm">
                      <a
                        href={applicant.resume_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        View Resume
                      </a>
                    </dd>
                  </div>
                )}
                <div>
                  <dt className="text-xs text-gray-400">Created</dt>
                  <dd className="text-sm text-gray-900">{formatDateLong(applicant.created_at)}</dd>
                </div>
              </dl>
            </div>
          </div>

          {/* Review Status */}
          <div className="border-t pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Checkbox
                  id="reviewed"
                  checked={applicant.is_reviewed}
                  disabled={updating}
                  onCheckedChange={(checked) => handleReviewedChange(checked === true)}
                />
                <label htmlFor="reviewed" className="text-sm font-medium text-gray-700">
                  Mark as Reviewed
                </label>
              </div>
              {applicant.is_reviewed && applicant.reviewed_at && (
                <p className="text-sm text-gray-500">
                  Reviewed {formatDateLong(applicant.reviewed_at)}
                  {applicant.reviewed_by && ` by ${applicant.reviewed_by}`}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Jobs Applied Section */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Jobs Applied ({applicant.opportunity_count})
            </h2>
            {applicant.opportunity_count >= 5 && (
              <Badge variant="secondary" className="bg-orange-100 text-orange-700">
                Mass Applicant
              </Badge>
            )}
          </div>

          {applicant.opportunity_count === 0 ? (
            <p className="text-gray-500 text-sm">No job applications found for this applicant.</p>
          ) : (
            <div className="space-y-3">
              {applicant.postings && applicant.postings.length > 0 ? (
                <>
                  {applicant.postings.map((posting) => (
                    <div
                      key={posting.id}
                      className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border"
                    >
                      <div>
                        <h4 className="font-medium text-gray-900">{posting.title}</h4>
                        <div className="flex flex-wrap gap-2 mt-1 text-xs text-gray-500">
                          {posting.team && <span>{posting.team}</span>}
                          {posting.department && (
                            <>
                              {posting.team && <span>•</span>}
                              <span>{posting.department}</span>
                            </>
                          )}
                          {posting.location && (
                            <>
                              {(posting.team || posting.department) && <span>•</span>}
                              <span>{posting.location}</span>
                            </>
                          )}
                          {posting.commitment && (
                            <>
                              {(posting.team || posting.department || posting.location) && (
                                <span>•</span>
                              )}
                              <span>{posting.commitment}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <a
                        href={`https://hire.lever.co/postings/${posting.lever_posting_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline text-sm shrink-0 ml-4"
                      >
                        View in Lever
                      </a>
                    </div>
                  ))}
                  {applicant.opportunity_count > applicant.postings.length && (
                    <p className="text-gray-500 text-sm pt-2 border-t">
                      + {applicant.opportunity_count - applicant.postings.length} additional application(s) pending sync from Lever
                    </p>
                  )}
                </>
              ) : (
                <p className="text-gray-500 text-sm">
                  Applied to {applicant.opportunity_count} job(s), but posting details not yet synced.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Flags Section */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Flags ({activeFlags.length})
          </h2>

          {activeFlags.length === 0 ? (
            <p className="text-gray-500 text-sm">No active flags for this applicant.</p>
          ) : (
            <div className="space-y-4">
              {activeFlags.map((flag) => (
                <FlagCard key={flag.id} flag={flag} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
