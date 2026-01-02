"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { fetchApplicant, updateApplicantReviewed } from "@/lib/api";
import type { ApplicantDetail, Flag } from "@/lib/types";

function getRiskBadgeVariant(riskLevel: string | null): "default" | "secondary" | "destructive" | "outline" {
  switch (riskLevel?.toLowerCase()) {
    case "critical":
      return "destructive";
    case "high":
      return "destructive";
    case "medium":
      return "secondary";
    case "low":
      return "outline";
    default:
      return "default";
  }
}

function getSeverityBadgeVariant(severity: string): "default" | "secondary" | "destructive" | "outline" {
  switch (severity.toLowerCase()) {
    case "critical":
      return "destructive";
    case "high":
      return "destructive";
    case "medium":
      return "secondary";
    case "low":
      return "outline";
    default:
      return "default";
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

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
        Flagged: {formatDate(flag.created_at)}
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500">Loading applicant...</p>
      </div>
    );
  }

  if (error || !applicant) {
    return (
      <div className="min-h-screen bg-gray-50">
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
      <div className="container mx-auto py-8 px-4 max-w-4xl">
        {/* Header */}
        <div className="mb-6">
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            &larr; Back to Applicants
          </Link>
        </div>

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
            </div>
          </div>

          {/* Info Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-3">Contact Information</h3>
              <dl className="space-y-2">
                <div>
                  <dt className="text-xs text-gray-400">Email</dt>
                  <dd className="text-sm text-gray-900">{applicant.email}</dd>
                </div>
                {applicant.phone && (
                  <div>
                    <dt className="text-xs text-gray-400">Phone</dt>
                    <dd className="text-sm text-gray-900">{applicant.phone}</dd>
                  </div>
                )}
                {applicant.location && (
                  <div>
                    <dt className="text-xs text-gray-400">Location</dt>
                    <dd className="text-sm text-gray-900">{applicant.location}</dd>
                  </div>
                )}
                {applicant.linkedin_url && (
                  <div>
                    <dt className="text-xs text-gray-400">LinkedIn</dt>
                    <dd className="text-sm">
                      <a
                        href={applicant.linkedin_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        View Profile
                      </a>
                    </dd>
                  </div>
                )}
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
                  <dd className="text-sm text-gray-900">{formatDate(applicant.created_at)}</dd>
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
                  Reviewed {formatDate(applicant.reviewed_at)}
                  {applicant.reviewed_by && ` by ${applicant.reviewed_by}`}
                </p>
              )}
            </div>
          </div>
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
