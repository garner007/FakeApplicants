"use client";

import { useState } from "react";
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
import { formatDate } from "@/lib/utils";
import {
  purgeDatabase,
  type DatabaseStatsResponse,
  type PurgeStatusResponse,
  type PurgeStatus,
} from "@/lib/api";

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

interface PurgeDatabaseCardProps {
  stats: DatabaseStatsResponse | null;
  purgeStatus: PurgeStatusResponse | null;
  isRunning: boolean;
  onPurgeStarted: () => void;
  onError: (error: string) => void;
}

export function PurgeDatabaseCard({
  stats,
  purgeStatus,
  isRunning,
  onPurgeStarted,
  onError,
}: PurgeDatabaseCardProps) {
  const [keepFlagTypes, setKeepFlagTypes] = useState(true);

  const handlePurge = async () => {
    try {
      await purgeDatabase({
        confirm: true,
        keep_flag_types: keepFlagTypes,
      });
      onPurgeStarted();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to start purge");
    }
  };

  return (
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
  );
}
