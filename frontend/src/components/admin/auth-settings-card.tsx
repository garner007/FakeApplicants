"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { updateAuthSettings, type AuthSettingsResponse } from "@/lib/api";

interface AuthSettingsCardProps {
  settings: AuthSettingsResponse | null;
  onSettingsUpdated: (settings: AuthSettingsResponse) => void;
  onError: (error: string) => void;
}

export function AuthSettingsCard({
  settings,
  onSettingsUpdated,
  onError,
}: AuthSettingsCardProps) {
  const [allowedDomain, setAllowedDomain] = useState<string>("");
  const [jwtExpiryHours, setJwtExpiryHours] = useState<string>("24");
  const [cookieSecure, setCookieSecure] = useState<boolean>(false);
  const [minPasswordLength, setMinPasswordLength] = useState<string>("8");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings) {
      setAllowedDomain(settings.auth_allowed_domain);
      setJwtExpiryHours(settings.auth_jwt_expiry_hours);
      setCookieSecure(settings.auth_cookie_secure === "true");
      setMinPasswordLength(settings.auth_min_password_length);
    }
  }, [settings]);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await updateAuthSettings({
        auth_allowed_domain: allowedDomain,
        auth_jwt_expiry_hours: jwtExpiryHours,
        auth_cookie_secure: cookieSecure ? "true" : "false",
        auth_min_password_length: minPasswordLength,
      });
      onSettingsUpdated(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to save auth settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="text-2xl">🔐</span>
          Authentication Settings
        </CardTitle>
        <CardDescription>
          Configure authentication and security settings. JWT secret is auto-generated and stored securely.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="allowed-domain" className="text-sm font-medium">
              Allowed Email Domain
            </Label>
            <Input
              id="allowed-domain"
              type="text"
              placeholder="company.com"
              value={allowedDomain}
              onChange={(e) => setAllowedDomain(e.target.value)}
              className="w-64"
              disabled={saving}
            />
            <p className="text-xs text-gray-500">
              Restrict user accounts to this email domain. Leave empty to allow all domains.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="jwt-expiry" className="text-sm font-medium">
              Session Duration (hours)
            </Label>
            <Input
              id="jwt-expiry"
              type="number"
              min={1}
              max={8760}
              value={jwtExpiryHours}
              onChange={(e) => setJwtExpiryHours(e.target.value)}
              className="w-24"
              disabled={saving}
            />
            <p className="text-xs text-gray-500">
              How long user sessions remain valid (1-8760 hours). Current: {settings?.auth_jwt_expiry_hours ?? 24}h
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="min-password" className="text-sm font-medium">
              Minimum Password Length
            </Label>
            <Input
              id="min-password"
              type="number"
              min={6}
              max={128}
              value={minPasswordLength}
              onChange={(e) => setMinPasswordLength(e.target.value)}
              className="w-24"
              disabled={saving}
            />
            <p className="text-xs text-gray-500">
              Minimum characters required for passwords (6-128).
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="cookie-secure"
              checked={cookieSecure}
              onCheckedChange={setCookieSecure}
              disabled={saving}
            />
            <Label htmlFor="cookie-secure" className="text-sm">
              Require HTTPS for session cookies (enable in production)
            </Label>
          </div>

          <div className="flex items-center gap-4">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : "Save Auth Settings"}
            </Button>
            {saved && (
              <span className="text-sm text-green-600">Auth settings saved successfully!</span>
            )}
          </div>

          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-md">
            <div className="flex items-start gap-3">
              <span className="text-lg">ℹ️</span>
              <div>
                <h4 className="font-semibold text-blue-800">Secure JWT Secret</h4>
                <p className="text-sm text-blue-700 mt-1">
                  The JWT signing secret is auto-generated on first startup and stored in the database.
                  It cannot be viewed or modified through this interface for security reasons.
                </p>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
