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
import { getSyncStatus, startSync, type SyncStatusResponse } from "@/lib/api";
import { RevalidateButton } from "@/components/revalidate-panel";

interface SyncPanelProps {
  onSyncComplete?: () => void;
  onRevalidateComplete?: () => void;
}

const PRESET_DAYS = [
  { value: "1", label: "Last 1 day" },
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
  { value: "180", label: "Last 180 days" },
  { value: "custom", label: "Custom..." },
];

export function SyncPanel({ onSyncComplete, onRevalidateComplete }: SyncPanelProps) {
  const [selectedDays, setSelectedDays] = useState("7");
  const [customDays, setCustomDays] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [syncStatus, setSyncStatus] = useState<SyncStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const status = await getSyncStatus();
      setSyncStatus(status);

      // If sync just completed, trigger refresh
      if (status.status === "completed" && onSyncComplete) {
        onSyncComplete();
      }
    } catch (err) {
      console.error("Failed to fetch sync status:", err);
    }
  }, [onSyncComplete]);

  // Poll for status when sync is running
  useEffect(() => {
    fetchStatus();

    const interval = setInterval(() => {
      if (syncStatus?.status === "running") {
        fetchStatus();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [fetchStatus, syncStatus?.status]);

  const handleDaysChange = (value: string) => {
    setSelectedDays(value);
    setShowCustomInput(value === "custom");
    if (value !== "custom") {
      setCustomDays("");
    }
  };

  const getDaysValue = (): number => {
    if (selectedDays === "custom") {
      return parseInt(customDays, 10) || 7;
    }
    return parseInt(selectedDays, 10);
  };

  const handleSync = async () => {
    setError(null);
    const days = getDaysValue();

    if (days < 1 || days > 365) {
      setError("Days must be between 1 and 365");
      return;
    }

    try {
      await startSync(days);
      fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start sync");
    }
  };

  const isRunning = syncStatus?.status === "running";
  const progress = syncStatus?.progress || 0;
  const total = syncStatus?.total || 0;
  const progressPercent = total > 0 ? Math.round((progress / total) * 100) : 0;

  return (
    <div className="flex items-center gap-3 p-4 bg-white border rounded-lg shadow-sm">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Sync from Lever:</span>
        <Select value={selectedDays} onValueChange={handleDaysChange} disabled={isRunning}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Select days" />
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

        <Button onClick={handleSync} disabled={isRunning || (showCustomInput && !customDays)}>
          {isRunning ? "Syncing..." : "Sync Now"}
        </Button>
      </div>

      {isRunning && (
        <div className="flex items-center gap-2 ml-4">
          <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <span className="text-sm text-gray-600">
            {progress}/{total} ({progressPercent}%)
          </span>
        </div>
      )}

      {syncStatus?.status === "completed" && syncStatus.last_sync_at && (
        <span className="text-sm text-green-600 ml-4">
          Last sync: {syncStatus.last_sync_count} applicants
        </span>
      )}

      {syncStatus?.status === "failed" && (
        <span className="text-sm text-red-600 ml-4">Sync failed: {syncStatus.error}</span>
      )}

      {error && <span className="text-sm text-red-600 ml-4">{error}</span>}

      {syncStatus?.message && isRunning && (
        <span className="text-sm text-gray-500 ml-2">{syncStatus.message}</span>
      )}

      <RevalidateButton onRevalidateComplete={onRevalidateComplete} />
    </div>
  );
}
