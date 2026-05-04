import type { LucideIcon } from "lucide-react";
import { StatTile } from "./ui/StatTile";

type Props = {
  label: string;
  value: string | number;
  icon: LucideIcon;
  accent?: "sky" | "radar" | "amber" | "rose";
};

const ACCENT_TO_TONE = {
  sky: "navy",
  radar: "success",
  amber: "gold",
  rose: "danger",
} as const;

// Legacy wrapper — renders the new Apple-style StatTile.
export function StatCard({ label, value, icon, accent = "sky" }: Props) {
  return <StatTile label={label} value={value} icon={icon} tone={ACCENT_TO_TONE[accent]} />;
}
