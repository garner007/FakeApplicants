"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { DatabaseStatsResponse } from "@/lib/api";

function formatNumber(num: number): string {
  return num.toLocaleString();
}

interface DatabaseStatsCardProps {
  stats: DatabaseStatsResponse | null;
  onRefresh: () => void;
}

export function DatabaseStatsCard({ stats, onRefresh }: DatabaseStatsCardProps) {
  return (
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
          <Button variant="outline" size="sm" onClick={onRefresh}>
            Refresh Stats
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
