"use client";

import { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  getRevalidateStatus,
  startRevalidation,
  type RevalidateStatusResponse,
} from "@/lib/api";

interface RevalidatePanelProps {
  onRevalidateComplete?: () => void;
}

const PRESET_DAYS = [
  { value: "all", label: "All Applicants" },
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "180", label: "Last 180 days" },
  { value: "custom", label: "Custom..." },
];

// Inline button component for use alongside SyncPanel
export function RevalidateButton({ onRevalidateComplete }: RevalidatePanelProps) {
  const [revalidateStatus, setRevalidateStatus] = useState<RevalidateStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const status = await getRevalidateStatus();
      setRevalidateStatus(status);

      if (status.status === "completed" && onRevalidateComplete) {
        onRevalidateComplete();
      }
    } catch (err) {
      console.error("Failed to fetch revalidation status:", err);
    }
  }, [onRevalidateComplete]);

  useEffect(() => {
    fetchStatus();

    const interval = setInterval(() => {
      if (revalidateStatus?.status === "running") {
        fetchStatus();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [fetchStatus, revalidateStatus?.status]);

  const handleRevalidate = async () => {
    setError(null);

    try {
      await startRevalidation({
        clear_existing_flags: true,
      });
      fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start re-validation");
    }
  };

  const isRunning = revalidateStatus?.status === "running";
  const progress = revalidateStatus?.progress || 0;
  const total = revalidateStatus?.total || 0;
  const progressPercent = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <>
      <div className="border-l border-gray-300 h-6 mx-2" />
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Re-validate:</span>
        <Button
          onClick={handleRevalidate}
          disabled={isRunning}
          variant="outline"
        >
          {isRunning ? "Running..." : "Re-run All"}
        </Button>
      </div>

      {isRunning && (
        <div className="flex items-center gap-2 ml-2">
          <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-green-500 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="text-sm text-gray-600">
            {progress}/{total}
          </span>
        </div>
      )}

      {revalidateStatus?.status === "completed" && revalidateStatus.last_run_at && !isRunning && (
        <span className="text-sm text-green-600 ml-2">
          {revalidateStatus.applicants_processed} validated
        </span>
      )}

      {revalidateStatus?.status === "failed" && (
        <span className="text-sm text-red-600 ml-2">Failed</span>
      )}

      {error && <span className="text-sm text-red-600 ml-2">{error}</span>}
    </>
  );
}

// Full filter options panel (separate section)
export function RevalidateFilterPanel({ onRevalidateComplete }: RevalidatePanelProps) {
  const [selectedDays, setSelectedDays] = useState("all");
  const [customDays, setCustomDays] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [clearExistingFlags, setClearExistingFlags] = useState(true);
  const [revalidateStatus, setRevalidateStatus] = useState<RevalidateStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const status = await getRevalidateStatus();
      setRevalidateStatus(status);

      if (status.status === "completed" && onRevalidateComplete) {
        onRevalidateComplete();
      }
    } catch (err) {
      console.error("Failed to fetch revalidation status:", err);
    }
  }, [onRevalidateComplete]);

  useEffect(() => {
    fetchStatus();

    const interval = setInterval(() => {
      if (revalidateStatus?.status === "running") {
        fetchStatus();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [fetchStatus, revalidateStatus?.status]);

  const handleDaysChange = (value: string) => {
    setSelectedDays(value);
    setShowCustomInput(value === "custom");
    if (value !== "custom") {
      setCustomDays("");
    }
  };

  const getDaysValue = (): number | undefined => {
    if (selectedDays === "all") {
      return undefined;
    }
    if (selectedDays === "custom") {
      const days = parseInt(customDays, 10);
      return isNaN(days) ? undefined : days;
    }
    return parseInt(selectedDays, 10);
  };

  const handleRevalidate = async () => {
    setError(null);
    const days = getDaysValue();

    if (days !== undefined && (days < 1 || days > 365)) {
      setError("Days must be between 1 and 365");
      return;
    }

    try {
      await startRevalidation({
        days,
        clear_existing_flags: clearExistingFlags,
      });
      fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start re-validation");
    }
  };

  const isRunning = revalidateStatus?.status === "running";
  const progress = revalidateStatus?.progress || 0;
  const total = revalidateStatus?.total || 0;
  const progressPercent = total > 0 ? Math.round((progress / total) * 100) : 0;

  const hasFilters = selectedDays !== "all";

  return (
    <div className="p-4 bg-white border rounded-lg shadow-sm">
      <div className="flex items-center justify-between">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
        >
          <svg
            className={`w-4 h-4 transition-transform ${isExpanded ? "rotate-90" : ""}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Advanced Re-validation Options
          {hasFilters && (
            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
              Filters active
            </span>
          )}
        </button>

        {isRunning && (
          <div className="flex items-center gap-2">
            <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 transition-all duration-300"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-sm text-gray-600">
              {progress}/{total} ({progressPercent}%)
            </span>
            {revalidateStatus?.current_applicant_name && (
              <span className="text-sm text-gray-400">
                ({revalidateStatus.current_applicant_name})
              </span>
            )}
          </div>
        )}

        {revalidateStatus?.status === "completed" && revalidateStatus.last_run_at && !isRunning && (
          <div className="flex items-center gap-4 text-sm">
            <span className="text-green-600">
              Processed: {revalidateStatus.applicants_processed}
            </span>
            <span className="text-orange-600">
              Flags: {revalidateStatus.flags_raised}
            </span>
            <span className="text-blue-600">
              Changes: {revalidateStatus.risk_level_changes}
            </span>
          </div>
        )}

        {error && <span className="text-sm text-red-600">{error}</span>}
      </div>

      {isExpanded && (
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-2">
              <Label className="text-sm font-medium text-gray-700">
                Filter by Age:
              </Label>
              <Select
                value={selectedDays}
                onValueChange={handleDaysChange}
                disabled={isRunning}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="All Applicants" />
                </SelectTrigger>
                <SelectContent>
                  {PRESET_DAYS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {showCustomInput && (
                <Input
                  type="number"
                  min="1"
                  max="365"
                  placeholder="Days"
                  value={customDays}
                  onChange={(e) => setCustomDays(e.target.value)}
                  className="w-[80px]"
                  disabled={isRunning}
                />
              )}
            </div>

            <div className="flex items-center gap-2">
              <Checkbox
                id="clear-flags"
                checked={clearExistingFlags}
                onCheckedChange={(checked) => setClearExistingFlags(checked === true)}
                disabled={isRunning}
              />
              <Label
                htmlFor="clear-flags"
                className="text-sm text-gray-700 cursor-pointer"
              >
                Clear existing flags
              </Label>
            </div>

            <Button
              onClick={handleRevalidate}
              disabled={isRunning || (showCustomInput && !customDays)}
              variant="default"
            >
              {isRunning ? "Re-validating..." : "Re-run with Filter"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// Legacy export for backwards compatibility
export function RevalidatePanel({ onRevalidateComplete }: RevalidatePanelProps) {
  return <RevalidateFilterPanel onRevalidateComplete={onRevalidateComplete} />;
}
