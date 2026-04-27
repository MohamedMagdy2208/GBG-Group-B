import type { LucideIcon } from "lucide-react";

type Props = {
  label: string;
  value: string | number;
  icon: LucideIcon;
  accent?: "sky" | "radar" | "amber" | "rose";
};

const accents = {
  sky: "bg-sky/10 text-sky",
  radar: "bg-radar/10 text-radar",
  amber: "bg-amberline/10 text-amberline",
  rose: "bg-rose-100 text-rose-700",
};

export function StatCard({ label, value, icon: Icon, accent = "sky" }: Props) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
        </div>
        <div className={`grid h-10 w-10 place-items-center rounded-lg ${accents[accent]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}
