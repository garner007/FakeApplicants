"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { updateValidationSettings, type ValidationSettingsResponse } from "@/lib/api";

interface ValidationSettingsCardProps {
  settings: ValidationSettingsResponse | null;
  onSettingsUpdated: (settings: ValidationSettingsResponse) => void;
  onError: (error: string) => void;
}

export function ValidationSettingsCard({
  settings,
  onSettingsUpdated,
  onError,
}: ValidationSettingsCardProps) {
  const [threshold, setThreshold] = useState<number>(settings?.mass_applicant_threshold ?? 5);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const updated = await updateValidationSettings({
        mass_applicant_threshold: threshold,
      });
      onSettingsUpdated(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="text-2xl">⚙️</span>
          Validation Settings
        </CardTitle>
        <CardDescription>
          Configure thresholds and parameters for applicant validation rules.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="mass-threshold" className="text-sm font-medium">
              Mass Applicant Threshold
            </Label>
            <div className="flex items-center gap-4">
              <Input
                id="mass-threshold"
                type="number"
                min={2}
                max={50}
                value={threshold}
                onChange={(e) => setThreshold(parseInt(e.target.value) || 5)}
                className="w-24"
                disabled={saving}
              />
              <span className="text-sm text-gray-500">applications</span>
            </div>
            <p className="text-xs text-gray-500">
              Applicants who apply to this many or more jobs will be flagged as &quot;Mass Applicants&quot;.
              Current setting: {settings?.mass_applicant_threshold ?? 5}
            </p>
          </div>

          <div className="flex items-center gap-4">
            <Button
              onClick={handleSave}
              disabled={saving || threshold === settings?.mass_applicant_threshold}
            >
              {saving ? "Saving..." : "Save Settings"}
            </Button>
            {saved && (
              <span className="text-sm text-green-600">Settings saved successfully!</span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
