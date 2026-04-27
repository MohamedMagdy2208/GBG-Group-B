const toneMap: Record<string, string> = {
  high: "bg-emerald-100 text-emerald-800 border-emerald-200",
  medium: "bg-amber-100 text-amber-800 border-amber-200",
  low: "bg-sky-100 text-sky-800 border-sky-200",
  pending: "bg-amber-100 text-amber-800 border-amber-200",
  approved: "bg-emerald-100 text-emerald-800 border-emerald-200",
  submitted: "bg-sky-100 text-sky-800 border-sky-200",
  released: "bg-emerald-100 text-emerald-800 border-emerald-200",
  blocked: "bg-rose-100 text-rose-800 border-rose-200",
  rejected: "bg-rose-100 text-rose-800 border-rose-200",
  warning: "bg-amber-100 text-amber-800 border-amber-200",
  critical: "bg-rose-100 text-rose-800 border-rose-200",
  info: "bg-slate-100 text-slate-700 border-slate-200",
  high_value: "bg-amber-100 text-amber-800 border-amber-200",
  sensitive: "bg-violet-100 text-violet-800 border-violet-200",
  dangerous: "bg-rose-100 text-rose-800 border-rose-200",
  normal: "bg-slate-100 text-slate-700 border-slate-200",
  active: "bg-emerald-100 text-emerald-800 border-emerald-200",
  disabled: "bg-rose-100 text-rose-800 border-rose-200",
  succeeded: "bg-emerald-100 text-emerald-800 border-emerald-200",
  failed: "bg-rose-100 text-rose-800 border-rose-200",
  processing: "bg-sky-100 text-sky-800 border-sky-200",
  dead_letter: "bg-rose-100 text-rose-800 border-rose-200",
  matched: "bg-sky-100 text-sky-800 border-sky-200",
  open: "bg-emerald-100 text-emerald-800 border-emerald-200",
};

export function Badge({ value }: { value?: string | null }) {
  const key = value ?? "unknown";
  const tone = toneMap[key] ?? "bg-slate-100 text-slate-700 border-slate-200";
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs font-semibold capitalize ${tone}`}>
      {key.replaceAll("_", " ")}
    </span>
  );
}
