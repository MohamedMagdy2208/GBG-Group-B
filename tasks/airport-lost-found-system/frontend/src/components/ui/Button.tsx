import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "destructive" | "gold" | "outline";
type Size = "sm" | "md" | "lg";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  fullWidth?: boolean;
};

const VARIANT_STYLES: Record<Variant, string> = {
  primary:
    "bg-gradient-navy text-white shadow-navy hover:shadow-card-hover hover:brightness-110 active:scale-[0.98]",
  gold:
    "bg-gradient-gold text-navy-950 shadow-gold hover:brightness-105 active:scale-[0.98]",
  secondary:
    "bg-ink-100 text-ink-800 hover:bg-ink-200 active:scale-[0.98] border border-ink-200/60",
  outline:
    "bg-white text-ink-800 border border-ink-200 hover:border-ink-300 hover:bg-ink-50 active:scale-[0.98]",
  ghost:
    "bg-transparent text-ink-700 hover:bg-ink-100 active:scale-[0.98]",
  destructive:
    "bg-danger-500 text-white shadow-card hover:bg-danger-600 active:scale-[0.98]",
};

const SIZE_STYLES: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-12 px-5 text-base gap-2",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  leftIcon,
  rightIcon,
  fullWidth = false,
  disabled,
  className = "",
  children,
  ...rest
}: Props) {
  const isDisabled = disabled || loading;
  return (
    <button
      {...rest}
      disabled={isDisabled}
      className={`focus-ring inline-flex items-center justify-center rounded-full font-semibold tracking-tight transition-all duration-150 ease-apple disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 ${VARIANT_STYLES[variant]} ${SIZE_STYLES[size]} ${fullWidth ? "w-full" : ""} ${className}`}
    >
      {loading ? <Loader2 size={size === "sm" ? 12 : 14} className="animate-spin" /> : leftIcon}
      <span>{children}</span>
      {!loading ? rightIcon : null}
    </button>
  );
}
