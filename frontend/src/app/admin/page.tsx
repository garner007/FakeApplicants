"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getDatabaseStats,
  getPurgeStatus,
  getValidationSettings,
  getAuthSettings,
  type DatabaseStatsResponse,
  type PurgeStatusResponse,
  type ValidationSettingsResponse,
  type AuthSettingsResponse,
} from "@/lib/api";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import {
  DatabaseStatsCard,
  ValidationSettingsCard,
  AuthSettingsCard,
  PurgeDatabaseCard,
} from "@/components/admin";

export default function AdminPage() {
  const [stats, setStats] = useState<DatabaseStatsResponse | null>(null);
  const [purgeStatus, setPurgeStatus] = useState<PurgeStatusResponse | null>(null);
  const [validationSettings, setValidationSettings] = useState<ValidationSettingsResponse | null>(null);
  const [authSettings, setAuthSettings] = useState<AuthSettingsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPurging, setIsPurging] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [statsData, statusData, settingsData, authData] = await Promise.all([
        getDatabaseStats(),
        getPurgeStatus(),
        getValidationSettings(),
        getAuthSettings(),
      ]);
      setStats(statsData);
      setPurgeStatus(statusData);
      setValidationSettings(settingsData);
      setAuthSettings(authData);
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

  const handlePurgeStarted = async () => {
    setIsPurging(true);
    setError(null);
    await loadData();
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
    setIsPurging(false);
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

        <DatabaseStatsCard stats={stats} onRefresh={loadData} />

        <ValidationSettingsCard
          settings={validationSettings}
          onSettingsUpdated={setValidationSettings}
          onError={handleError}
        />

        <AuthSettingsCard
          settings={authSettings}
          onSettingsUpdated={setAuthSettings}
          onError={handleError}
        />

        <PurgeDatabaseCard
          stats={stats}
          purgeStatus={purgeStatus}
          isRunning={isRunning}
          onPurgeStarted={handlePurgeStarted}
          onError={handleError}
        />
      </div>
    </div>
  );
}
