"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getValidationRules, type ValidationRule } from "@/lib/api";
import { Header } from "@/components/header";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case "critical":
      return "bg-red-600 hover:bg-red-700";
    case "high":
      return "bg-orange-500 hover:bg-orange-600";
    case "medium":
      return "bg-yellow-500 hover:bg-yellow-600";
    case "low":
      return "bg-blue-500 hover:bg-blue-600";
    case "info":
      return "bg-gray-500 hover:bg-gray-600";
    default:
      return "bg-gray-500 hover:bg-gray-600";
  }
}

function getCategoryIcon(category: string): string {
  switch (category.toLowerCase()) {
    case "email":
      return "📧";
    case "phone":
      return "📱";
    case "identity":
      return "🪪";
    case "linkedin":
      return "💼";
    case "resume":
      return "📄";
    case "behavior":
      return "🔍";
    case "location":
      return "📍";
    default:
      return "⚡";
  }
}

function getDataManagementLink(ruleName: string): { href: string; label: string } | null {
  switch (ruleName) {
    case "disposable_email":
      return {
        href: "/validation-data/disposable-domains",
        label: "Manage Disposable Domains",
      };
    case "voip_phone":
      return {
        href: "/validation-data/voip",
        label: "Manage VoIP Data",
      };
    default:
      return null;
  }
}

export default function RulesPage() {
  const [rules, setRules] = useState<ValidationRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRules() {
      try {
        const response = await getValidationRules();
        setRules(response.rules);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load rules");
      } finally {
        setLoading(false);
      }
    }
    loadRules();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="container mx-auto py-8 px-4">
          <div className="flex items-center justify-center h-64">
            <div className="text-gray-500">Loading validation rules...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header />
        <div className="container mx-auto py-8 px-4">
          <div className="p-4 bg-red-50 border border-red-200 rounded-md text-red-700">
            {error}
          </div>
        </div>
      </div>
    );
  }

  // Group rules by category
  const rulesByCategory = rules.reduce((acc, rule) => {
    const category = rule.category;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(rule);
    return acc;
  }, {} as Record<string, ValidationRule[]>);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <div className="container mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Validation Rules</h1>
          <p className="text-gray-600 mt-2">
            These are the automated checks that run on each applicant to detect potential fraud indicators.
          </p>
        </div>

        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex items-start gap-3">
            <span className="text-2xl">ℹ️</span>
            <div>
              <h3 className="font-semibold text-blue-900">How Validation Works</h3>
              <p className="text-blue-800 text-sm mt-1">
                When applicants are synced from Lever, each one is automatically validated against these rules.
                If a rule fails, a flag is created with the corresponding severity level. The applicant&apos;s
                overall risk level is determined by the highest severity flag they have.
              </p>
            </div>
          </div>
        </div>

        <div className="mb-6 flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700">Severity Levels:</span>
          <div className="flex gap-2">
            <Badge className="bg-red-600">Critical</Badge>
            <Badge className="bg-orange-500">High</Badge>
            <Badge className="bg-yellow-500">Medium</Badge>
            <Badge className="bg-blue-500">Low</Badge>
            <Badge className="bg-gray-500">Info</Badge>
          </div>
        </div>

        <div className="grid gap-6">
          {Object.entries(rulesByCategory).map(([category, categoryRules]) => (
            <div key={category}>
              <h2 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                <span>{getCategoryIcon(category)}</span>
                <span className="capitalize">{category} Checks</span>
                <Badge variant="outline" className="ml-2">
                  {categoryRules.length} {categoryRules.length === 1 ? "rule" : "rules"}
                </Badge>
              </h2>
              <div className="grid gap-4">
                {categoryRules.map((rule) => (
                  <Card key={rule.name} className="border-l-4" style={{
                    borderLeftColor: rule.severity === "critical" ? "#dc2626" :
                      rule.severity === "high" ? "#f97316" :
                      rule.severity === "medium" ? "#eab308" :
                      rule.severity === "low" ? "#3b82f6" : "#6b7280"
                  }}>
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-lg flex items-center gap-2">
                            {rule.description}
                            <Badge className={getSeverityColor(rule.severity)}>
                              {rule.severity.toUpperCase()}
                            </Badge>
                          </CardTitle>
                          <CardDescription className="mt-1">
                            <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
                              {rule.name}
                            </code>
                            <span className="mx-2">•</span>
                            <span>v{rule.version}</span>
                            <span className="mx-2">•</span>
                            <span>Checks: {rule.checks_fields.join(", ")}</span>
                          </CardDescription>
                        </div>
                        {rule.is_active ? (
                          <Badge variant="outline" className="text-green-600 border-green-600">
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-gray-400 border-gray-400">
                            Inactive
                          </Badge>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent>
                      {rule.rationale && (
                        <div className="mb-4">
                          <h4 className="text-sm font-semibold text-gray-700 mb-1">Why This Matters</h4>
                          <p className="text-sm text-gray-600">{rule.rationale}</p>
                        </div>
                      )}
                      {rule.trigger_examples.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">Examples That Trigger This Rule</h4>
                          <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                            {rule.trigger_examples.map((example, idx) => (
                              <li key={idx}>
                                <code className="text-xs bg-gray-100 px-1 py-0.5 rounded">
                                  {example}
                                </code>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {getDataManagementLink(rule.name) && (
                        <div className="mt-4 pt-4 border-t">
                          <Link href={getDataManagementLink(rule.name)!.href}>
                            <Button variant="outline" size="sm">
                              {getDataManagementLink(rule.name)!.label} →
                            </Button>
                          </Link>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 p-4 bg-gray-100 rounded-md">
          <h3 className="font-semibold text-gray-800 mb-2">Total Active Rules: {rules.length}</h3>
          <p className="text-sm text-gray-600">
            Rules are applied automatically during sync operations. Results are stored as flags
            on each applicant record.
          </p>
        </div>
      </div>
    </div>
  );
}
