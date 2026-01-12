"use client";

import { useEffect, useState, useCallback } from "react";
import { getIntegrations, type IntegrationSetting } from "@/lib/api";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import { IntegrationCard } from "@/components/settings";

export default function SettingsPage() {
  const [integrations, setIntegrations] = useState<IntegrationSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const response = await getIntegrations();
      setIntegrations(response.integrations);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load settings");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="container mx-auto py-8 px-4">
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">Loading settings...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Integration Settings</h1>
          <p className="text-gray-600 mt-2">
            Configure API integrations for enhanced validation capabilities.
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

        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex items-start gap-3">
            <span className="text-2xl">💡</span>
            <div>
              <h3 className="font-semibold text-blue-900">Getting Started</h3>
              <p className="text-blue-800 text-sm mt-1">
                Add your API credentials below to enable enhanced validation features.
                IPQualityScore is recommended for phone validation with a free tier of 1,000 lookups/month.
                Credentials are stored securely and can be updated at any time.
              </p>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Phone Validation</h2>
          <div className="grid gap-4">
            {integrations
              .filter((i) => ["ipqualityscore", "twilio"].includes(i.provider))
              .map((integration) => (
                <IntegrationCard
                  key={integration.provider}
                  integration={integration}
                  onUpdate={loadData}
                />
              ))}
          </div>
        </div>

        {integrations.some((i) => !["ipqualityscore", "twilio"].includes(i.provider)) && (
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-800 mb-4">Other Integrations</h2>
            <div className="grid gap-4">
              {integrations
                .filter((i) => !["ipqualityscore", "twilio"].includes(i.provider))
                .map((integration) => (
                  <IntegrationCard
                    key={integration.provider}
                    integration={integration}
                    onUpdate={loadData}
                  />
                ))}
            </div>
          </div>
        )}

        <div className="mt-8 p-4 bg-gray-100 rounded-md">
          <h3 className="font-semibold text-gray-800 mb-2">Security Note</h3>
          <p className="text-sm text-gray-600">
            API credentials are stored in the database and masked in the UI for security.
            For production deployments, consider using environment variables or a secrets
            manager for additional protection.
          </p>
        </div>
      </div>
    </div>
  );
}
