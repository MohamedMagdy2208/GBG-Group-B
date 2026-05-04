import { useQuery } from "@tanstack/react-query";
import { Boxes, ClipboardList, Search, ShieldAlert, ShieldCheck, TrendingUp } from "lucide-react";
import { api } from "../api/client";
import { Card } from "../components/ui/Card";
import { Section } from "../components/ui/Section";
import { StatTile } from "../components/ui/StatTile";
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
    <Section
      kicker="Admin"
      title="Analytics"
      description="Operational metrics across reports, found items, matches, and fraud risk."
    >
      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-5">
        <StatTile label="Open lost" value={summary?.open_lost_reports ?? 0} icon={ClipboardList} tone="navy" />
        <StatTile label="Found" value={summary?.registered_found_items ?? 0} icon={Boxes} tone="success" />
        <StatTile label="Pending" value={summary?.pending_matches ?? 0} icon={Search} tone="warn" />
        <StatTile label="High confidence" value={summary?.high_confidence_matches ?? 0} icon={ShieldCheck} tone="success" />
        <StatTile label="Avg score" value={Math.round(summary?.average_match_score ?? 0)} icon={TrendingUp} tone="gold" />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <StatTile label="High fraud risk" value={fraudRisk?.high_risk_claims ?? 0} icon={ShieldAlert} tone="warn" helper="Score ≥ 70/100" />
        <StatTile label="Blocked claims" value={fraudRisk?.blocked_claims ?? 0} icon={ShieldCheck} tone="danger" helper="Manual review required" />
        <StatTile label="Avg fraud score" value={Math.round(fraudRisk?.average_fraud_score ?? 0)} icon={TrendingUp} tone="navy" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Items by category" rows={byCategory.map((row) => [row.category, row.count])} accent="navy" />
        <Panel title="High-loss areas" rows={highLoss.map((row) => [row.location, row.count])} accent="gold" />
      </div>
    </Section>
  );
}

function Panel({ title, rows, accent = "navy" }: { title: string; rows: Array<[string, number]>; accent?: "navy" | "gold" }) {
  const max = Math.max(1, ...rows.map(([, count]) => count));
  const barClass = accent === "gold" ? "bg-gradient-gold" : "bg-gradient-navy";
  return (
    <Card>
      <p className="font-display text-base font-semibold tracking-tight text-ink-900">{title}</p>
      <div className="mt-4 space-y-3">
        {rows.length === 0 ? (
          <p className="text-sm text-ink-500">No data yet.</p>
        ) : (
          rows.slice(0, 10).map(([label, count]) => (
            <div key={label} className="grid grid-cols-[140px_1fr_42px] items-center gap-3 text-sm">
              <span className="truncate font-medium text-ink-700">{label}</span>
              <div className="h-2 overflow-hidden rounded-full bg-ink-100">
                <div className={`h-full rounded-full transition-all ${barClass}`} style={{ width: `${(count / max) * 100}%` }} />
              </div>
              <span className="text-right font-semibold tabular-nums text-ink-800">{count}</span>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}
