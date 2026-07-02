import { motion } from "framer-motion";
import CountUp from "react-countup";
import { Card } from "./Card";
import { cn } from "../../utils/cn";
import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  prefix,
  suffix,
  icon,
  tone = "primary",
  isString,
  delay = 0,
}: {
  label: string;
  value: number | string;
  prefix?: string;
  suffix?: string;
  icon?: ReactNode;
  tone?: "primary" | "success" | "warning" | "danger";
  isString?: boolean;
  delay?: number;
}) {
  const toneMap = {
    primary: "text-primary-600 bg-primary-50",
    success: "text-success bg-success-50",
    warning: "text-warning bg-warning-50",
    danger: "text-danger bg-danger-50",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
    >
      <Card className="p-4 hover:shadow-card transition-shadow duration-200">
        <div className="flex items-start justify-between">
          <span className="text-xs font-medium text-ink-500">{label}</span>
          {icon && (
            <span className={cn("flex h-8 w-8 items-center justify-center rounded-lg", toneMap[tone])}>
              {icon}
            </span>
          )}
        </div>
        <div className="mt-2 text-2xl font-bold tracking-tight text-ink-900">
          {isString || typeof value === "string" ? (
            value
          ) : (
            <CountUp end={value as number} duration={1.1} prefix={prefix} suffix={suffix} separator="," />
          )}
        </div>
      </Card>
    </motion.div>
  );
}
