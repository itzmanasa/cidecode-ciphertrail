import { Badge } from "./Badge";

const TONE_MAP: Record<string, "success" | "warning" | "danger" | "neutral"> = {
  success: "success",
  completed: "success",
  cleared: "success",
  reversed: "warning",
  pending: "warning",
  failed: "danger",
  declined: "danger",
  critical: "danger",
  high: "danger",
  medium: "warning",
  low: "success",
};

export function StatusBadge({ status }: { status?: string }) {
  const tone = TONE_MAP[(status || "").toLowerCase()] || "neutral";
  return <Badge tone={tone}>{status || "Unknown"}</Badge>;
}
