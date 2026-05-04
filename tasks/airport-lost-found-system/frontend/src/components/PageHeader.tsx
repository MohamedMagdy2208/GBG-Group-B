import type React from "react";

// Legacy header — renders the new Apple-style Section header inline so older pages still work.
export function PageHeader({ title, kicker, action }: { title: string; kicker?: string; action?: React.ReactNode }) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        {kicker ? (
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">{kicker}</p>
        ) : null}
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900 lg:text-3xl">{title}</h1>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}
