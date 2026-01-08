"use client";

import { useEffect, useState, useCallback } from "react";
import { ApplicantsTable } from "@/components/applicants-table";
import { RevalidateFilterPanel } from "@/components/revalidate-panel";
import { SyncPanel } from "@/components/sync-panel";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { fetchApplicants, getTAs, getSources } from "@/lib/api";
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
  const [tas, setTAs] = useState<string[]>([]);
  const [selectedTa, setSelectedTa] = useState<string>("");
  const [sources, setSources] = useState<string[]>([]);
  const [selectedSource, setSelectedSource] = useState<string>("");

  const loadApplicants = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchApplicants({
        page,
        pageSize: 20,
        sortBy,
        sortOrder,
        assignedTa: selectedTa || undefined,
        source: selectedSource || undefined,
      });
      setApplicants(response.items);
      setTotalPages(response.total_pages);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load applicants");
    } finally {
      setLoading(false);
    }
  }, [page, sortBy, sortOrder, selectedTa, selectedSource]);

  const loadTAs = useCallback(async () => {
    try {
      const taList = await getTAs();
      setTAs(taList);
    } catch (err) {
      console.error("Failed to load TAs:", err);
    }
  }, []);

  const loadSources = useCallback(async () => {
    try {
      const sourceList = await getSources();
      setSources(sourceList);
    } catch (err) {
      console.error("Failed to load sources:", err);
    }
  }, []);

  useEffect(() => {
    loadApplicants();
  }, [loadApplicants]);

  useEffect(() => {
    loadTAs();
  }, [loadTAs]);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  const handleSort = (field: SortField) => {
    if (field === sortBy) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
    setPage(1);
  };

  const handleTaChange = (value: string) => {
    setSelectedTa(value === "all" ? "" : value);
    setPage(1);
  };

  const handleSourceChange = (value: string) => {
    setSelectedSource(value === "all" ? "" : value);
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Applicants</h1>
          <p className="text-gray-600 mt-2">
            Review and validate job applicants for potential fraud indicators.
          </p>
        </div>

        <div className="mb-6 space-y-4">
          <SyncPanel onSyncComplete={loadApplicants} onRevalidateComplete={loadApplicants} />
          <RevalidateFilterPanel onRevalidateComplete={loadApplicants} />
        </div>

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
          <div className="flex items-center gap-4">
            <p className="text-sm text-gray-600">
              {loading ? "Loading..." : `${total} applicants found`}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Filter by TA:</span>
              <Select value={selectedTa || "all"} onValueChange={handleTaChange}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="All TAs" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All TAs</SelectItem>
                  {tas.map((ta) => (
                    <SelectItem key={ta} value={ta}>
                      {ta}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700">Filter by Source:</span>
              <Select value={selectedSource || "all"} onValueChange={handleSourceChange}>
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="All Sources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  {sources.map((source) => (
                    <SelectItem key={source} value={source}>
                      {source}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
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
