import type { ReactNode } from "react";

type Tone = "neutral" | "navy" | "gold" | "success" | "warn" | "danger" | "info";

const TONE_STYLES: Record<Tone, string> = {
  neutral: "bg-ink-100 text-ink-700 ring-ink-200/60",
  navy: "bg-navy-50 text-navy-800 ring-navy-200/60",
  gold: "bg-gold-50 text-gold-800 ring-gold-200/60",
  success: "bg-success-50 text-success-700 ring-success-500/20",
  warn: "bg-warn-50 text-warn-700 ring-warn-500/20",
  danger: "bg-danger-50 text-danger-700 ring-danger-500/20",
  info: "bg-navy-50 text-navy-700 ring-navy-200/60",
};

const DOT_COLOR: Record<Tone, string> = {
  neutral: "bg-ink-400",
  navy: "bg-navy-500",
  gold: "bg-gold-500",
  success: "bg-success-500",
  warn: "bg-warn-500",
  danger: "bg-danger-500",
  info: "bg-navy-500",
};

type Props = {
  tone?: Tone;
  children: ReactNode;
  withDot?: boolean;
  className?: string;
};

export function Pill({ tone = "neutral", children, withDot = false, className = "" }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-tight ring-1 ring-inset ${TONE_STYLES[tone]} ${className}`}
    >
      {withDot ? <span className={`h-1.5 w-1.5 rounded-full ${DOT_COLOR[tone]}`} /> : null}
      <span className="capitalize">{children}</span>
    </span>
  );
}

const STATUS_TONE_MAP: Record<string, Tone> = {
  // confidence
  high: "success",
  medium: "warn",
  low: "neutral",
  // match status
  pending: "warn",
  approved: "success",
  rejected: "danger",
  needs_more_info: "navy",
  // claim status
  submitted: "info",
  released: "success",
  blocked: "danger",
  // found item status
  registered: "navy",
  matched: "info",
  claimed: "warn",
  disposed: "neutral",
  // lost report status
  open: "warn",
  resolved: "success",
  // risk
  normal: "neutral",
  high_value: "gold",
  sensitive: "warn",
  dangerous: "danger",
  // user status
  active: "success",
  disabled: "neutral",
  // severity
  info: "navy",
  warning: "warn",
  critical: "danger",
  // jobs
  succeeded: "success",
  failed: "danger",
  processing: "info",
  dead_letter: "danger",
};

export function StatusPill({ value, withDot = true }: { value?: string | null; withDot?: boolean }) {
  if (!value) return null;
  const tone = STATUS_TONE_MAP[value] ?? "neutral";
  return (
    <Pill tone={tone} withDot={withDot}>
      {value.replaceAll("_", " ")}
    </Pill>
  );
}
