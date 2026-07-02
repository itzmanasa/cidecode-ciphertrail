import type { HTMLAttributes } from "react";
import { cn } from "../../utils/cn";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: "primary" | "success" | "warning" | "danger" | "neutral";
}

const tones = {
  primary: "bg-primary-50 text-primary-700 ring-primary-500/10",
  success: "bg-success-50 text-success ring-success/15",
  warning: "bg-warning-50 text-warning ring-warning/15",
  danger: "bg-danger-50 text-danger ring-danger/15",
  neutral: "bg-ink-100 text-ink-700 ring-ink-300/30",
};

export function Badge({ className, tone = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-semibold ring-1",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
