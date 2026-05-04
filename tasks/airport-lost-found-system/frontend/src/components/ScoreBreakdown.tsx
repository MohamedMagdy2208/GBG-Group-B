import type { MatchCandidate } from "../types";

const metrics: Array<[keyof MatchCandidate, string]> = [
  ["azure_search_score", "AI Search"],
  ["category_score", "Category"],
  ["text_score", "Text"],
  ["color_score", "Color"],
  ["location_score", "Location"],
  ["time_score", "Time"],
  ["flight_score", "Flight"],
  ["unique_identifier_score", "Identifier"],
];

export function ScoreBreakdown({ match }: { match: MatchCandidate }) {
  const imageScore = Number((match.evidence_spans_json as { image_score?: number } | undefined)?.image_score ?? 0);
  return (
    <div className="space-y-2">
      {metrics.map(([key, label]) => {
        const value = Number(match[key] ?? 0);
        return (
          <div key={key} className="grid grid-cols-[88px_1fr_42px] items-center gap-2 text-xs">
            <span className="font-medium text-slate-500">{label}</span>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-sky" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
            </div>
            <span className="text-right font-semibold text-slate-700">{value.toFixed(0)}</span>
          </div>
        );
      })}
      <div className="grid grid-cols-[88px_1fr_42px] items-center gap-2 text-xs">
        <span className="font-medium text-violet-700">Image</span>
        <div className="h-2 overflow-hidden rounded-full bg-slate-100">
          <div className="h-full rounded-full bg-violet-500" style={{ width: `${Math.max(0, Math.min(100, imageScore))}%` }} />
        </div>
        <span className="text-right font-semibold text-violet-700">{imageScore.toFixed(0)}</span>
      </div>
    </div>
  );
}
