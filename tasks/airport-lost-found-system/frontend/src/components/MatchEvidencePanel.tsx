import { useMemo } from "react";
import type { EvidenceFacet, EvidenceSpan, EvidenceSpans } from "../types";

type Side = "lost" | "found";

const FACET_COLOR: Record<EvidenceFacet, string> = {
  identifier: "bg-rose-200 text-rose-900",
  color: "bg-amber-200 text-amber-900",
  category: "bg-sky-200 text-sky-900",
  location: "bg-emerald-200 text-emerald-900",
  flight: "bg-violet-200 text-violet-900",
  text: "bg-slate-200 text-slate-900",
};

const FACET_PRECEDENCE: EvidenceFacet[] = ["identifier", "color", "category", "location", "flight", "text"];

function pickSpansForSide(spans: EvidenceSpans | undefined, side: Side) {
  const sideSpans = spans?.[side] ?? {};
  const flat: Array<{ facet: EvidenceFacet; span: EvidenceSpan }> = [];
  (Object.entries(sideSpans) as [EvidenceFacet, EvidenceSpan[]][]).forEach(([facet, list]) => {
    (list ?? []).forEach((span) => flat.push({ facet, span }));
  });
  // De-duplicate overlapping spans by facet precedence.
  flat.sort((a, b) => {
    if (a.span.start !== b.span.start) return a.span.start - b.span.start;
    return FACET_PRECEDENCE.indexOf(a.facet) - FACET_PRECEDENCE.indexOf(b.facet);
  });
  const cleaned: Array<{ facet: EvidenceFacet; span: EvidenceSpan }> = [];
  let cursor = -1;
  for (const item of flat) {
    if (item.span.start < cursor) continue;
    cleaned.push(item);
    cursor = item.span.end;
  }
  return cleaned;
}

function highlight(text: string, items: Array<{ facet: EvidenceFacet; span: EvidenceSpan }>) {
  if (!text) return null;
  if (!items.length) return <span>{text}</span>;
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  items.forEach(({ facet, span }, idx) => {
    if (span.start > cursor) {
      parts.push(<span key={`plain-${idx}`}>{text.slice(cursor, span.start)}</span>);
    }
    parts.push(
      <mark key={`mark-${idx}`} className={`rounded px-0.5 ${FACET_COLOR[facet]}`} title={facet}>
        {text.slice(span.start, span.end)}
      </mark>,
    );
    cursor = span.end;
  });
  if (cursor < text.length) {
    parts.push(<span key="tail">{text.slice(cursor)}</span>);
  }
  return parts;
}

type Props = {
  spans?: EvidenceSpans;
  lostText: string;
  foundText: string;
};

export function MatchEvidencePanel({ spans, lostText, foundText }: Props) {
  const lostHighlights = useMemo(() => pickSpansForSide(spans, "lost"), [spans]);
  const foundHighlights = useMemo(() => pickSpansForSide(spans, "found"), [spans]);
  const facetsActive: EvidenceFacet[] = useMemo(() => {
    const set = new Set<EvidenceFacet>();
    [...lostHighlights, ...foundHighlights].forEach(({ facet }) => set.add(facet));
    return FACET_PRECEDENCE.filter((facet) => set.has(facet));
  }, [lostHighlights, foundHighlights]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900">Why this match?</h3>
        <div className="flex flex-wrap gap-1.5">
          {facetsActive.length === 0 ? (
            <span className="text-xs text-slate-500">No span overlap detected — review summary above.</span>
          ) : (
            facetsActive.map((facet) => (
              <span key={facet} className={`inline-flex rounded px-1.5 py-0.5 text-xs font-medium capitalize ${FACET_COLOR[facet]}`}>
                {facet}
              </span>
            ))
          )}
        </div>
      </header>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <article>
          <p className="text-xs font-semibold uppercase text-slate-500">Lost report</p>
          <p className="mt-1 whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm leading-relaxed text-slate-800">
            {highlight(lostText, lostHighlights)}
          </p>
        </article>
        <article>
          <p className="text-xs font-semibold uppercase text-slate-500">Found item</p>
          <p className="mt-1 whitespace-pre-wrap rounded-lg border border-slate-100 bg-slate-50 p-3 text-sm leading-relaxed text-slate-800">
            {highlight(foundText, foundHighlights)}
          </p>
        </article>
      </div>
      {spans?.identifier_overlap?.length ? (
        <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-800">
          Unique identifier overlap: <span className="font-mono">{spans.identifier_overlap.join(", ")}</span>
        </p>
      ) : null}
      {spans?.shared_terms?.length ? (
        <p className="mt-2 text-xs text-slate-600">
          Shared terms: <span className="font-mono">{spans.shared_terms.join(", ")}</span>
        </p>
      ) : null}
    </section>
  );
}
