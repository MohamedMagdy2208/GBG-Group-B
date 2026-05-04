import type { LucideIcon } from "lucide-react";

type Tone = "navy" | "gold" | "success" | "warn" | "danger" | "neutral";

const TONE_STYLES: Record<Tone, { iconBg: string; iconText: string; ring: string }> = {
  navy: { iconBg: "bg-navy-50", iconText: "text-navy-700", ring: "ring-navy-100" },
  gold: { iconBg: "bg-gold-50", iconText: "text-gold-700", ring: "ring-gold-100" },
  success: { iconBg: "bg-success-50", iconText: "text-success-700", ring: "ring-success-500/15" },
  warn: { iconBg: "bg-warn-50", iconText: "text-warn-700", ring: "ring-warn-500/15" },
  danger: { iconBg: "bg-danger-50", iconText: "text-danger-700", ring: "ring-danger-500/15" },
  neutral: { iconBg: "bg-ink-100", iconText: "text-ink-700", ring: "ring-ink-200" },
};

type Props = {
  label: string;
  value: string | number;
  helper?: string;
  icon?: LucideIcon;
  tone?: Tone;
  trend?: { direction: "up" | "down" | "flat"; label: string };
};

export function StatTile({ label, value, helper, icon: Icon, tone = "navy", trend }: Props) {
  const styles = TONE_STYLES[tone];
  return (
    <div className="group rounded-3xl border border-ink-200/60 bg-white p-5 shadow-card transition-all duration-200 ease-apple hover:shadow-card-hover hover:-translate-y-[1px]">
      <div className="flex items-start justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-ink-500">{label}</p>
        {Icon ? (
          <span className={`grid h-9 w-9 place-items-center rounded-2xl ring-1 ${styles.iconBg} ${styles.iconText} ${styles.ring}`}>
            <Icon className="h-4 w-4" />
          </span>
        ) : null}
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight text-ink-900 tabular-nums">{value}</p>
      <div className="mt-1 flex items-center gap-2">
        {helper ? <p className="text-xs text-ink-500">{helper}</p> : null}
        {trend ? (
          <span
            className={`inline-flex items-center gap-0.5 text-[11px] font-semibold ${
              trend.direction === "up" ? "text-success-700" : trend.direction === "down" ? "text-danger-600" : "text-ink-500"
            }`}
          >
            {trend.direction === "up" ? "▲" : trend.direction === "down" ? "▼" : "•"} {trend.label}
          </span>
        ) : null}
      </div>
    </div>
  );
}
