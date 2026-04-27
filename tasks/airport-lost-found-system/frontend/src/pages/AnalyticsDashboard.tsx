import { useQuery } from "@tanstack/react-query";
import { Boxes, ClipboardList, Search, ShieldAlert, ShieldCheck, TrendingUp } from "lucide-react";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import type { AnalyticsSummary, FraudRiskAnalytics } from "../types";

export function AnalyticsDashboard() {
  const { data: summary } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: async () => (await api.get<AnalyticsSummary>("/analytics/summary")).data,
  });
  const { data: byCategory = [] } = useQuery({
    queryKey: ["items-by-category"],
    queryFn: async () => (await api.get<Array<{ category: string; count: number }>>("/analytics/items-by-category")).data,
  });
  const { data: highLoss = [] } = useQuery({
    queryKey: ["high-loss-areas"],
    queryFn: async () => (await api.get<Array<{ location: string; count: number }>>("/analytics/high-loss-areas")).data,
  });
  const { data: fraudRisk } = useQuery({
    queryKey: ["fraud-risk"],
    queryFn: async () => (await api.get<FraudRiskAnalytics>("/analytics/fraud-risk")).data,
  });

  return (
    <section className="space-y-5">
      <PageHeader title="Analytics Dashboard" kicker="Admin" />
      <div className="grid gap-4 md:grid-cols-5">
        <StatCard label="Open lost" value={summary?.open_lost_reports ?? 0} icon={ClipboardList} />
        <StatCard label="Found" value={summary?.registered_found_items ?? 0} icon={Boxes} accent="radar" />
        <StatCard label="Pending" value={summary?.pending_matches ?? 0} icon={Search} accent="amber" />
        <StatCard label="High confidence" value={summary?.high_confidence_matches ?? 0} icon={ShieldCheck} accent="radar" />
        <StatCard label="Avg score" value={summary?.average_match_score ?? 0} icon={TrendingUp} />
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard label="High fraud risk" value={fraudRisk?.high_risk_claims ?? 0} icon={ShieldAlert} accent="amber" />
        <StatCard label="Blocked claims" value={fraudRisk?.blocked_claims ?? 0} icon={ShieldCheck} />
        <StatCard label="Avg fraud score" value={fraudRisk?.average_fraud_score ?? 0} icon={TrendingUp} accent="radar" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Items by category" rows={byCategory.map((row) => [row.category, row.count])} />
        <Panel title="High-loss areas" rows={highLoss.map((row) => [row.location, row.count])} />
      </div>
    </section>
  );
}

function Panel({ title, rows }: { title: string; rows: Array<[string, number]> }) {
  const max = Math.max(1, ...rows.map(([, count]) => count));
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 className="font-semibold text-slate-950">{title}</h2>
      <div className="mt-4 space-y-3">
        {rows.slice(0, 10).map(([label, count]) => (
          <div key={label} className="grid grid-cols-[120px_1fr_36px] items-center gap-3 text-sm">
            <span className="truncate font-medium text-slate-600">{label}</span>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-radar" style={{ width: `${(count / max) * 100}%` }} />
            </div>
            <span className="text-right font-semibold">{count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
