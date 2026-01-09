"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getDatabaseStats,
  getPurgeStatus,
  purgeDatabase,
  type DatabaseStatsResponse,
  type PurgeStatusResponse,
  type PurgeStatus,
} from "@/lib/api";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

function formatNumber(num: number): string {
  return num.toLocaleString();
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusBadge({ status }: { status: PurgeStatus }) {
  const styles = {
    idle: "bg-gray-100 text-gray-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

export default function AdminPage() {
  const [stats, setStats] = useState<DatabaseStatsResponse | null>(null);
  const [purgeStatus, setPurgeStatus] = useState<PurgeStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [keepFlagTypes, setKeepFlagTypes] = useState(true);
  const [isPurging, setIsPurging] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [statsData, statusData] = await Promise.all([
        getDatabaseStats(),
        getPurgeStatus(),
      ]);
      setStats(statsData);
      setPurgeStatus(statusData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Poll for status when purge is running
  useEffect(() => {
    if (purgeStatus?.status === "running") {
      const interval = setInterval(async () => {
        try {
          const [statusData, statsData] = await Promise.all([
            getPurgeStatus(),
            getDatabaseStats(),
          ]);
          setPurgeStatus(statusData);
          setStats(statsData);
          if (statusData.status !== "running") {
            setIsPurging(false);
          }
        } catch {
          // Ignore errors during polling
        }
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [purgeStatus?.status]);

  const handlePurge = async () => {
    setIsPurging(true);
    setError(null);
    try {
      await purgeDatabase({
        confirm: true,
        keep_flag_types: keepFlagTypes,
      });
      // Status will update via polling
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start purge");
      setIsPurging(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="container mx-auto py-8 px-4">
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">Loading admin data...</div>
          </div>
        </div>
      </div>
    );
  }

  const isRunning = purgeStatus?.status === "running" || isPurging;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Admin</h1>
          <p className="text-gray-600 mt-2">
            Database administration and maintenance tools.
          </p>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
            {error}
            <Button variant="outline" size="sm" className="ml-4" onClick={loadData}>
              Retry
            </Button>
          </div>
        )}

        {/* Database Statistics */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">📊</span>
              Database Statistics
            </CardTitle>
            <CardDescription>
              Current database record counts
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-4 bg-blue-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-blue-700">
                  {stats ? formatNumber(stats.applicants_count) : "-"}
                </div>
                <div className="text-sm text-blue-600">Applicants</div>
              </div>
              <div className="p-4 bg-orange-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-orange-700">
                  {stats ? formatNumber(stats.flags_count) : "-"}
                </div>
                <div className="text-sm text-orange-600">Flags</div>
              </div>
              <div className="p-4 bg-purple-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-purple-700">
                  {stats ? formatNumber(stats.validation_runs_count) : "-"}
                </div>
                <div className="text-sm text-purple-600">Validation Runs</div>
              </div>
              <div className="p-4 bg-green-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-green-700">
                  {stats ? formatNumber(stats.flag_types_count) : "-"}
                </div>
                <div className="text-sm text-green-600">Flag Types</div>
              </div>
              <div className="p-4 bg-cyan-50 rounded-lg text-center">
                <div className="text-2xl font-bold text-cyan-700">
                  {stats ? formatNumber(stats.linkedin_profiles_count) : "-"}
                </div>
                <div className="text-sm text-cyan-600">LinkedIn Profiles</div>
              </div>
            </div>
            <div className="mt-4 flex justify-end">
              <Button variant="outline" size="sm" onClick={loadData}>
                Refresh Stats
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Purge Database */}
        <Card className="border-l-4 border-l-red-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700">
              <span className="text-2xl">🗑️</span>
              Purge Database
            </CardTitle>
            <CardDescription>
              Remove all applicant data from the database. This action cannot be undone.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {/* Purge Status */}
            {purgeStatus && purgeStatus.status !== "idle" && (
              <div className={`mb-4 p-4 rounded-md ${
                purgeStatus.status === "running" ? "bg-blue-50 border border-blue-200" :
                purgeStatus.status === "completed" ? "bg-green-50 border border-green-200" :
                purgeStatus.status === "failed" ? "bg-red-50 border border-red-200" :
                "bg-gray-50 border border-gray-200"
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">
                    {purgeStatus.status === "running" ? "Purge in progress..." : "Last Purge"}
                  </span>
                  <StatusBadge status={purgeStatus.status} />
                </div>
                <p className="text-sm text-gray-600">{purgeStatus.message}</p>
                {purgeStatus.error && (
                  <p className="text-sm text-red-600 mt-1">{purgeStatus.error}</p>
                )}
                {purgeStatus.last_run_at && (
                  <p className="text-xs text-gray-500 mt-2">
                    Completed: {formatDate(purgeStatus.last_run_at)}
                  </p>
                )}
                {purgeStatus.status === "completed" && (
                  <div className="mt-2 grid grid-cols-3 gap-2 text-center text-sm">
                    <div className="bg-white p-2 rounded">
                      <span className="font-semibold">{purgeStatus.applicants_deleted}</span>
                      <span className="text-gray-500 ml-1">applicants</span>
                    </div>
                    <div className="bg-white p-2 rounded">
                      <span className="font-semibold">{purgeStatus.flags_deleted}</span>
                      <span className="text-gray-500 ml-1">flags</span>
                    </div>
                    <div className="bg-white p-2 rounded">
                      <span className="font-semibold">{purgeStatus.validation_runs_deleted}</span>
                      <span className="text-gray-500 ml-1">runs</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Warning */}
            <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
              <div className="flex items-start gap-3">
                <span className="text-xl">⚠️</span>
                <div>
                  <h4 className="font-semibold text-yellow-800">Warning</h4>
                  <p className="text-sm text-yellow-700 mt-1">
                    This will permanently delete all applicants, flags, validation runs,
                    LinkedIn profiles, and related data. This action cannot be undone.
                  </p>
                </div>
              </div>
            </div>

            {/* Options */}
            <div className="mb-4 p-4 bg-gray-50 rounded-md">
              <h4 className="font-medium mb-3">Purge Options</h4>
              <div className="flex items-center space-x-2">
                <Switch
                  id="keep-flag-types"
                  checked={keepFlagTypes}
                  onCheckedChange={setKeepFlagTypes}
                  disabled={isRunning}
                />
                <Label htmlFor="keep-flag-types" className="text-sm">
                  Keep flag type definitions (recommended)
                </Label>
              </div>
              <p className="text-xs text-gray-500 mt-2">
                Flag types define the validation rules. Keeping them allows re-validation
                without needing to re-seed the database.
              </p>
            </div>

            {/* Purge Button */}
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="destructive"
                  disabled={isRunning || (stats?.applicants_count === 0)}
                >
                  {isRunning ? "Purging..." : "Purge Database"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                  <AlertDialogDescription asChild>
                    <div>
                      <p>This will permanently delete:</p>
                      <ul className="list-disc ml-6 mt-2 space-y-1">
                        <li><strong>{stats?.applicants_count}</strong> applicants</li>
                        <li><strong>{stats?.flags_count}</strong> flags</li>
                        <li><strong>{stats?.validation_runs_count}</strong> validation runs</li>
                        <li><strong>{stats?.linkedin_profiles_count}</strong> LinkedIn profiles</li>
                        {!keepFlagTypes && <li><strong>{stats?.flag_types_count}</strong> flag types</li>}
                      </ul>
                      <p className="mt-3 font-semibold text-red-600">
                        This action cannot be undone.
                      </p>
                    </div>
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={handlePurge}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    Yes, Purge Everything
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            {stats?.applicants_count === 0 && (
              <p className="text-sm text-gray-500 mt-2">
                Database is already empty.
              </p>
            )}
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
