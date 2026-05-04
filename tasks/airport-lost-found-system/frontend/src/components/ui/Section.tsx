import type { ReactNode } from "react";

type Props = {
  kicker?: string;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
};

export function Section({ kicker, title, description, action, children, className = "" }: Props) {
  return (
    <section className={`space-y-4 ${className}`}>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          {kicker ? (
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">{kicker}</p>
          ) : null}
          <h1 className="font-display text-2xl font-semibold tracking-tight text-ink-900 lg:text-3xl">{title}</h1>
          {description ? <p className="mt-1 max-w-2xl text-sm text-ink-500">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </header>
      {children}
    </section>
  );
}
