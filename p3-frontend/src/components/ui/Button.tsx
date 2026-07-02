import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../utils/cn";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
}

const variants = {
  primary: "bg-grad-primary text-white shadow-glow hover:opacity-95",
  secondary: "bg-primary-50 text-primary-700 hover:bg-primary-100",
  ghost: "text-ink-700 hover:bg-ink-100/60",
  outline: "border border-ink-200 text-ink-700 hover:bg-ink-100/50 bg-white",
  danger: "bg-danger text-white hover:opacity-90",
};

const sizes = {
  sm: "h-8 px-3 text-xs",
  md: "h-9 px-4 text-sm",
  lg: "h-11 px-6 text-sm",
};

export function Button({ className, variant = "primary", size = "md", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-medium transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  );
}
