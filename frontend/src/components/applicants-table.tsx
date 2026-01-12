"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Applicant, SortField, SortOrder } from "@/lib/types";
import { updateApplicantReviewed } from "@/lib/api";
import { getRiskBadgeVariant, formatDate } from "@/lib/utils";

interface ApplicantsTableProps {
  applicants: Applicant[];
  sortBy: SortField;
  sortOrder: SortOrder;
  onSort: (field: SortField) => void;
  onApplicantUpdated: () => void;
}

function SortIcon({ field, currentField, currentOrder }: { field: SortField; currentField: SortField; currentOrder: SortOrder }) {
  if (field !== currentField) {
    return <span className="ml-1 text-gray-400">↕</span>;
  }
  return <span className="ml-1">{currentOrder === "asc" ? "↑" : "↓"}</span>;
}

export function ApplicantsTable({
  applicants,
  sortBy,
  sortOrder,
  onSort,
  onApplicantUpdated,
}: ApplicantsTableProps) {
  const [updatingIds, setUpdatingIds] = useState<Set<string>>(new Set());

  const handleReviewedChange = async (applicant: Applicant, checked: boolean) => {
    setUpdatingIds((prev) => new Set(prev).add(applicant.id));
    try {
      await updateApplicantReviewed(applicant.id, checked);
      onApplicantUpdated();
    } catch (error) {
      console.error("Failed to update applicant:", error);
    } finally {
      setUpdatingIds((prev) => {
        const next = new Set(prev);
        next.delete(applicant.id);
        return next;
      });
    }
  };

  const sortableFields: { field: SortField; label: string }[] = [
    { field: "name", label: "Name" },
    { field: "risk_level", label: "Risk Level" },
    { field: "flag_count", label: "Flags" },
    { field: "sources", label: "Sources" },
    { field: "assigned_ta", label: "Assigned TA" },
    { field: "lever_created_at", label: "Application Date" },
    { field: "created_at", label: "Date Loaded" },
  ];

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[50px]">Reviewed</TableHead>
            {sortableFields.map(({ field, label }) => (
              <TableHead key={field}>
                <Button
                  variant="ghost"
                  className="h-8 p-0 font-semibold hover:bg-transparent"
                  onClick={() => onSort(field)}
                >
                  {label}
                  <SortIcon field={field} currentField={sortBy} currentOrder={sortOrder} />
                </Button>
              </TableHead>
            ))}
            <TableHead>Email</TableHead>
            <TableHead>Location</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {applicants.length === 0 ? (
            <TableRow>
              <TableCell colSpan={10} className="h-24 text-center text-muted-foreground">
                No applicants found.
              </TableCell>
            </TableRow>
          ) : (
            applicants.map((applicant) => (
              <TableRow key={applicant.id}>
                <TableCell>
                  <Checkbox
                    checked={applicant.is_reviewed}
                    disabled={updatingIds.has(applicant.id)}
                    onCheckedChange={(checked) =>
                      handleReviewedChange(applicant, checked === true)
                    }
                  />
                </TableCell>
                <TableCell className="font-medium">
                  <Link
                    href={`/applicants/${applicant.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    {applicant.name}
                  </Link>
                </TableCell>
                <TableCell>
                  {applicant.risk_level ? (
                    <Badge variant={getRiskBadgeVariant(applicant.risk_level)}>
                      {applicant.risk_level}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell>
                  {applicant.flag_count > 0 ? (
                    <Badge variant="secondary">{applicant.flag_count}</Badge>
                  ) : (
                    <span className="text-muted-foreground">0</span>
                  )}
                </TableCell>
                <TableCell>
                  {applicant.sources && applicant.sources.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {applicant.sources.map((source, index) => (
                        <Badge key={index} variant="outline" className="text-xs">
                          {source}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell>
                  {applicant.assigned_ta ? (
                    <span className="text-sm">{applicant.assigned_ta}</span>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {applicant.lever_created_at ? formatDate(applicant.lever_created_at) : "-"}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(applicant.created_at)}
                </TableCell>
                <TableCell>{applicant.email}</TableCell>
                <TableCell className="text-muted-foreground">
                  {applicant.location || "-"}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
