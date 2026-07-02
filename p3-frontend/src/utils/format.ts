export function formatINR(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value?: number | null): string {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return new Intl.NumberFormat("en-IN").format(value);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function riskColor(risk?: string): { bg: string; text: string; ring: string } {
  switch ((risk || "").toLowerCase()) {
    case "high":
    case "critical":
      return { bg: "bg-danger-50", text: "text-danger", ring: "ring-danger/20" };
    case "medium":
      return { bg: "bg-warning-50", text: "text-warning", ring: "ring-warning/20" };
    default:
      return { bg: "bg-success-50", text: "text-success", ring: "ring-success/20" };
  }
}

export function truncateMiddle(str: string, head = 6, tail = 4): string {
  if (str.length <= head + tail + 3) return str;
  return `${str.slice(0, head)}…${str.slice(-tail)}`;
}
