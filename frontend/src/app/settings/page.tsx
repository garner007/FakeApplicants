"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getIntegrations,
  updateIntegration,
  testIntegration,
  type IntegrationSetting,
} from "@/lib/api";
import { Header } from "@/components/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function getProviderIcon(provider: string): string {
  switch (provider) {
    case "ipqualityscore":
      return "🛡️";
    case "twilio":
      return "📱";
    case "lever":
      return "📋";
    case "linkedin":
      return "💼";
    default:
      return "⚙️";
  }
}

function getProviderDescription(provider: string): string {
  switch (provider) {
    case "ipqualityscore":
      return "Phone validation with VoIP detection and fraud scoring. Free tier: 1,000 lookups/month.";
    case "twilio":
      return "Real-time carrier type lookup for phone numbers. Pay per lookup (~$0.005).";
    case "lever":
      return "ATS integration for syncing applicant data.";
    case "linkedin":
      return "Profile enrichment and verification.";
    default:
      return "Third-party integration.";
  }
}

function getProviderDocsUrl(provider: string): string | null {
  switch (provider) {
    case "ipqualityscore":
      return "https://www.ipqualityscore.com/documentation/phone-number-validation-api/overview";
    case "twilio":
      return "https://www.twilio.com/docs/lookup/v2-api";
    case "lever":
      return "https://hire.lever.co/developer/documentation";
    case "linkedin":
      return "https://learn.microsoft.com/en-us/linkedin/";
    default:
      return null;
  }
}

interface IntegrationCardProps {
  integration: IntegrationSetting;
  onUpdate: () => void;
}

function IntegrationCard({ integration, onUpdate }: IntegrationCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [accountId, setAccountId] = useState("");
  const [fraudThreshold, setFraudThreshold] = useState(
    integration.fraud_score_threshold?.toString() || "85"
  );
  const [leverEnvironment, setLeverEnvironment] = useState(() => {
    // Parse existing config_json to get environment
    if (integration.config_json) {
      try {
        const config = JSON.parse(integration.config_json);
        return config.environment || "sandbox";
      } catch {
        return "sandbox";
      }
    }
    return "sandbox";
  });

  const handleToggleEnabled = async () => {
    setError(null);
    try {
      await updateIntegration(integration.provider, {
        is_enabled: !integration.is_enabled,
      });
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update");
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    try {
      const updates: Record<string, unknown> = {};

      if (apiKey) {
        updates.api_key = apiKey;
      }
      if (apiSecret) {
        updates.api_secret = apiSecret;
      }
      if (accountId) {
        updates.account_id = accountId;
      }
      if (integration.provider === "ipqualityscore" && fraudThreshold) {
        updates.fraud_score_threshold = parseInt(fraudThreshold, 10);
      }
      if (integration.provider === "lever") {
        // Store environment in config_json
        updates.config_json = JSON.stringify({ environment: leverEnvironment });
      }

      await updateIntegration(integration.provider, updates);
      setApiKey("");
      setApiSecret("");
      setAccountId("");
      setIsEditing(false);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    setError(null);
    try {
      const result = await testIntegration(integration.provider);
      setTestResult(result);
      onUpdate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to test");
    } finally {
      setIsTesting(false);
    }
  };

  const docsUrl = getProviderDocsUrl(integration.provider);

  return (
    <Card
      className={`border-l-4 ${
        integration.is_enabled && integration.has_credentials
          ? "border-l-green-500"
          : integration.has_credentials
          ? "border-l-yellow-500"
          : "border-l-gray-300"
      }`}
    >
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{getProviderIcon(integration.provider)}</span>
            <div>
              <CardTitle className="text-lg">{integration.display_name}</CardTitle>
              <CardDescription className="mt-1">
                {getProviderDescription(integration.provider)}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center space-x-2">
              <Switch
                id={`${integration.provider}-enabled`}
                checked={integration.is_enabled}
                onCheckedChange={handleToggleEnabled}
                disabled={!integration.has_credentials}
              />
              <Label htmlFor={`${integration.provider}-enabled`}>
                {integration.is_enabled ? "Enabled" : "Disabled"}
              </Label>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-4">
          {/* Status badges */}
          <div className="flex flex-wrap gap-2">
            {integration.has_credentials ? (
              <Badge variant="outline" className="text-green-600 border-green-600">
                Credentials Configured
              </Badge>
            ) : (
              <Badge variant="outline" className="text-yellow-600 border-yellow-600">
                No Credentials
              </Badge>
            )}
            {integration.last_test_success !== null && (
              <Badge
                variant="outline"
                className={
                  integration.last_test_success
                    ? "text-green-600 border-green-600"
                    : "text-red-600 border-red-600"
                }
              >
                {integration.last_test_success ? "Test Passed" : "Test Failed"}
              </Badge>
            )}
            {integration.monthly_limit && (
              <Badge variant="outline">
                Usage: {integration.monthly_usage} / {integration.monthly_limit}
              </Badge>
            )}
          </div>

          {/* Current credentials (masked) */}
          {integration.has_credentials && !isEditing && (
            <div className="p-3 bg-gray-50 rounded-md space-y-2">
              {integration.api_key_masked && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 w-24">API Key:</span>
                  <code className="bg-gray-200 px-2 py-0.5 rounded">
                    {integration.api_key_masked}
                  </code>
                </div>
              )}
              {integration.api_secret_masked && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 w-24">API Secret:</span>
                  <code className="bg-gray-200 px-2 py-0.5 rounded">
                    {integration.api_secret_masked}
                  </code>
                </div>
              )}
              {integration.account_id && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 w-24">Account ID:</span>
                  <code className="bg-gray-200 px-2 py-0.5 rounded">
                    {integration.account_id}
                  </code>
                </div>
              )}
              {integration.fraud_score_threshold !== null && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-500 w-24">Fraud Threshold:</span>
                  <span>{integration.fraud_score_threshold}</span>
                </div>
              )}
            </div>
          )}

          {/* Edit form */}
          {isEditing && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-md space-y-3">
              <h4 className="font-medium text-blue-900">
                Update Credentials
              </h4>
              <p className="text-xs text-blue-700">
                Leave fields empty to keep existing values. Enter new values to update.
              </p>

              {integration.provider === "ipqualityscore" && (
                <>
                  <div>
                    <Label htmlFor="api-key" className="text-sm">
                      API Key
                    </Label>
                    <Input
                      id="api-key"
                      type="password"
                      placeholder="Enter API key"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="fraud-threshold" className="text-sm">
                      Fraud Score Threshold (0-100)
                    </Label>
                    <Input
                      id="fraud-threshold"
                      type="number"
                      min="0"
                      max="100"
                      placeholder="85"
                      value={fraudThreshold}
                      onChange={(e) => setFraudThreshold(e.target.value)}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Phone numbers with fraud scores at or above this threshold will be flagged as high risk.
                    </p>
                  </div>
                </>
              )}

              {integration.provider === "twilio" && (
                <>
                  <div>
                    <Label htmlFor="account-sid" className="text-sm">
                      Account SID
                    </Label>
                    <Input
                      id="account-sid"
                      type="text"
                      placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                      value={accountId}
                      onChange={(e) => setAccountId(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="auth-token" className="text-sm">
                      Auth Token
                    </Label>
                    <Input
                      id="auth-token"
                      type="password"
                      placeholder="Enter auth token"
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                    />
                  </div>
                </>
              )}

              {integration.provider === "lever" && (
                <>
                  <div>
                    <Label htmlFor="lever-api-key" className="text-sm">
                      API Key
                    </Label>
                    <Input
                      id="lever-api-key"
                      type="password"
                      placeholder="Enter Lever API key"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Get your API key from{" "}
                      <a
                        href="https://hire.lever.co/settings/integrations/api"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-600 hover:underline"
                      >
                        Lever Settings
                      </a>
                    </p>
                  </div>
                  <div>
                    <Label htmlFor="lever-environment" className="text-sm">
                      Environment
                    </Label>
                    <select
                      id="lever-environment"
                      value={leverEnvironment}
                      onChange={(e) => setLeverEnvironment(e.target.value)}
                      className="w-full h-9 px-3 rounded-md border border-input bg-transparent text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                    >
                      <option value="sandbox">Sandbox</option>
                      <option value="production">Production</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Use Sandbox for testing, Production for live data.
                    </p>
                  </div>
                </>
              )}

              {integration.provider === "linkedin" && (
                <>
                  <div>
                    <Label htmlFor="linkedin-client-id" className="text-sm">
                      Client ID
                    </Label>
                    <Input
                      id="linkedin-client-id"
                      type="text"
                      placeholder="Enter LinkedIn Client ID"
                      value={accountId}
                      onChange={(e) => setAccountId(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="linkedin-client-secret" className="text-sm">
                      Client Secret
                    </Label>
                    <Input
                      id="linkedin-client-secret"
                      type="password"
                      placeholder="Enter LinkedIn Client Secret"
                      value={apiSecret}
                      onChange={(e) => setApiSecret(e.target.value)}
                    />
                  </div>
                </>
              )}

              <div className="flex gap-2 pt-2">
                <Button onClick={handleSave} disabled={isSaving} size="sm">
                  {isSaving ? "Saving..." : "Save"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setIsEditing(false)}
                  size="sm"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Test result */}
          {testResult && (
            <div
              className={`p-3 rounded-md text-sm ${
                testResult.success
                  ? "bg-green-50 border border-green-200 text-green-700"
                  : "bg-red-50 border border-red-200 text-red-700"
              }`}
            >
              <strong>{testResult.success ? "Success:" : "Failed:"}</strong>{" "}
              {testResult.message}
            </div>
          )}

          {/* Last test info */}
          {integration.last_test_at && (
            <p className="text-xs text-gray-500">
              Last tested: {new Date(integration.last_test_at).toLocaleString()}
              {integration.last_test_message && ` - ${integration.last_test_message}`}
            </p>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-2">
            {!isEditing && (
              <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                {integration.has_credentials ? "Update Credentials" : "Add Credentials"}
              </Button>
            )}
            {integration.has_credentials && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleTest}
                disabled={isTesting}
              >
                {isTesting ? "Testing..." : "Test Connection"}
              </Button>
            )}
            {docsUrl && (
              <a href={docsUrl} target="_blank" rel="noopener noreferrer">
                <Button variant="ghost" size="sm">
                  View Docs
                </Button>
              </a>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

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
