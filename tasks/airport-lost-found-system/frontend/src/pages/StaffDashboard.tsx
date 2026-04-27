import { useQuery } from "@tanstack/react-query";
import { Boxes, ClipboardList, Search, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import type { AnalyticsSummary, MatchCandidate } from "../types";

export function StaffDashboard() {
  const { data: summary } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: async () => (await api.get<AnalyticsSummary>("/analytics/summary")).data,
  });
  const { data: matches = [] } = useQuery({
    queryKey: ["matches"],
    queryFn: async () => (await api.get<MatchCandidate[]>("/matches")).data,
  });

  return (
    <div className="space-y-5">
      <PageHeader title="Staff Dashboard" kicker="Operations" />
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Open lost reports" value={summary?.open_lost_reports ?? 0} icon={ClipboardList} accent="radar" />
        <StatCard label="Registered found" value={summary?.registered_found_items ?? 0} icon={Boxes} />
        <StatCard label="Pending matches" value={summary?.pending_matches ?? 0} icon={Search} accent="amber" />
        <StatCard label="Average score" value={summary?.average_match_score ?? 0} icon={TrendingUp} accent="radar" />
      </div>
      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4">
          <h2 className="font-semibold text-slate-950">Priority Matches</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {matches.slice(0, 6).map((match) => (
            <Link key={match.id} to="/staff/matches" className="grid gap-3 p-4 hover:bg-slate-50 sm:grid-cols-[1fr_120px_120px]">
              <div>
                <p className="font-semibold text-slate-950">{match.lost_report?.item_title ?? "Lost item"} ↔ {match.found_item?.item_title ?? "Found item"}</p>
                <p className="mt-1 text-sm text-slate-500">{match.ai_match_summary}</p>
              </div>
              <Badge value={match.confidence_level} />
              <p className="text-lg font-semibold text-slate-950">{match.match_score.toFixed(0)}%</p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
