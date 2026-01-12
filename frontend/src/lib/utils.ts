import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export type BadgeVariant = "default" | "secondary" | "destructive" | "outline"

/**
 * Get the badge variant for a risk level
 */
export function getRiskBadgeVariant(riskLevel: string | null): BadgeVariant {
  switch (riskLevel?.toLowerCase()) {
    case "critical":
    case "high":
      return "destructive"
    case "medium":
      return "secondary"
    case "low":
      return "outline"
    default:
      return "default"
  }
}

export type DateFormatStyle = "short" | "long"

/**
 * Format a date string for display
 * @param dateString - ISO date string
 * @param monthStyle - "short" (Jan) or "long" (January)
 */
export function formatDate(dateString: string, monthStyle: DateFormatStyle = "short"): string {
  return new Date(dateString).toLocaleDateString("en-US", {
    year: "numeric",
    month: monthStyle,
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
