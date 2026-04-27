import type React from "react";

export function PageHeader({ title, kicker, action }: { title: string; kicker?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-semibold uppercase tracking-normal text-radar">{kicker}</p>
        <h1 className="text-2xl font-semibold text-slate-950">{title}</h1>
      </div>
      {action}
    </div>
  );
}
