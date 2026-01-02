"use client";

import { useEffect, useState, useCallback } from "react";
import { ApplicantsTable } from "@/components/applicants-table";
import { Button } from "@/components/ui/button";
import { fetchApplicants } from "@/lib/api";
import type { Applicant, SortField, SortOrder } from "@/lib/types";

export default function Home() {
  const [applicants, setApplicants] = useState<Applicant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [sortBy, setSortBy] = useState<SortField>("created_at");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const loadApplicants = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchApplicants({
        page,
        pageSize: 20,
        sortBy,
        sortOrder,
      });
      setApplicants(response.items);
      setTotalPages(response.total_pages);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load applicants");
    } finally {
      setLoading(false);
    }
  }, [page, sortBy, sortOrder]);

  useEffect(() => {
    loadApplicants();
  }, [loadApplicants]);

  const handleSort = (field: SortField) => {
    if (field === sortBy) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-8 px-4">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Applicant Validator</h1>
          <p className="text-gray-600 mt-2">
            Review and validate job applicants for potential fraud indicators.
          </p>
        </header>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
            {error}
            <Button
              variant="outline"
              size="sm"
              className="ml-4"
              onClick={loadApplicants}
            >
              Retry
            </Button>
          </div>
        )}

        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            {loading ? "Loading..." : `${total} applicants found`}
          </p>
        </div>

        {loading && applicants.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">Loading applicants...</div>
          </div>
        ) : (
          <>
            <ApplicantsTable
              applicants={applicants}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              onApplicantUpdated={loadApplicants}
            />

            {totalPages > 1 && (
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1 || loading}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages || loading}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
