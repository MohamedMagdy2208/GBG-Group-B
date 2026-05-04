import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, AlertTriangle, Boxes, ClipboardList, PackagePlus, ScanLine, Search, TrendingUp } from "lucide-react";
import type React from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Card } from "../components/ui/Card";
import { Section } from "../components/ui/Section";
import { StatTile } from "../components/ui/StatTile";
import { StatusPill } from "../components/ui/Pill";
import { useAuth } from "../hooks/useAuth";
import type { AnalyticsSummary, LostReport, MatchCandidate } from "../types";

export function StaffDashboard() {
  const { user } = useAuth();
  const { data: summary } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: async () => (await api.get<AnalyticsSummary>("/analytics/summary")).data,
  });
  const { data: matches = [] } = useQuery({
    queryKey: ["matches"],
    queryFn: async () => (await api.get<MatchCandidate[]>("/matches")).data,
  });
  const { data: lostReports = [] } = useQuery({
    queryKey: ["lost-reports", "dashboard"],
    queryFn: async () => (await api.get<LostReport[]>("/lost-reports")).data,
  });
  const highConfidencePending = matches.filter((match) => match.confidence_level === "high" && match.status === "pending");
  const blockedOrSensitive = matches.filter((match) => ["high_value", "sensitive", "dangerous"].includes(match.found_item?.risk_level ?? ""));

  return (
    <Section
      kicker={user ? `${user.name} · ${user.role}` : "Operations"}
      title="Operations dashboard"
      description="Today's open reports, registered found items, and the matches that need a human in the loop."
    >
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatTile label="Open lost reports" value={summary?.open_lost_reports ?? 0} icon={ClipboardList} tone="navy" helper="Awaiting a match" />
        <StatTile label="Registered found" value={summary?.registered_found_items ?? 0} icon={Boxes} tone="success" helper="In storage" />
        <StatTile label="Pending matches" value={summary?.pending_matches ?? 0} icon={Search} tone="warn" helper="Need staff approval" />
        <StatTile label="Average score" value={Math.round(summary?.average_match_score ?? 0)} icon={TrendingUp} tone="gold" helper="Top candidates" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="grid h-9 w-9 place-items-center rounded-2xl bg-warn-50 text-warn-700 ring-1 ring-warn-500/15">
                <AlertTriangle className="h-4 w-4" />
              </span>
              <div>
                <p className="font-display text-base font-semibold tracking-tight text-ink-900">Operations queue</p>
                <p className="text-xs text-ink-500">Where staff attention is needed right now</p>
              </div>
            </div>
            <Link to="/staff/matches" className="focus-ring text-xs font-semibold text-navy-700 hover:underline">
              Open matches →
            </Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <QueueMetric label="High confidence" value={highConfidencePending.length} tone="success" />
            <QueueMetric label="Risk review" value={blockedOrSensitive.length} tone="danger" />
            <QueueMetric label="Open reports" value={summary?.open_lost_reports ?? 0} tone="navy" />
          </div>
        </Card>
        <Card>
          <p className="font-display text-base font-semibold tracking-tight text-ink-900">Quick actions</p>
          <p className="mt-0.5 text-xs text-ink-500">Common workflows in one click.</p>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <QuickAction to="/staff/found/new" label="Register found" icon={PackagePlus} />
            <QuickAction to="/staff/matches" label="Review matches" icon={Search} />
            <QuickAction to="/staff/scan" label="Scan QR" icon={ScanLine} />
          </div>
        </Card>
      </div>

      <Card className="overflow-hidden p-0" padded={false}>
        <div className="flex items-center justify-between border-b border-ink-200/60 px-5 py-4">
          <div>
            <p className="font-display text-base font-semibold tracking-tight text-ink-900">Recent lost reports</p>
            <p className="text-xs text-ink-500">Latest passenger filings.</p>
          </div>
          <Link to="/staff/lost" className="focus-ring inline-flex items-center gap-1 text-xs font-semibold text-navy-700 hover:underline">
            View all <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-50/60 text-[11px] uppercase tracking-wider text-ink-500">
              <tr>
                <th className="px-5 py-3 font-semibold">Code</th>
                <th className="font-semibold">Item</th>
                <th className="font-semibold">Category</th>
                <th className="font-semibold">Location</th>
                <th className="font-semibold">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100">
              {lostReports.slice(0, 6).map((report) => (
                <tr key={report.id} className="transition-colors hover:bg-ink-50/40">
                  <td className="px-5 py-3 font-mono text-xs font-semibold text-navy-700">
                    <Link to={`/staff/lost/${report.id}`} className="hover:underline">{report.report_code}</Link>
                  </td>
                  <td className="text-sm text-ink-800">{report.item_title}</td>
                  <td className="text-sm text-ink-600">{report.category ?? "—"}</td>
                  <td className="text-sm text-ink-600">{report.lost_location ?? "—"}</td>
                  <td><StatusPill value={report.status} /></td>
                </tr>
              ))}
              {lostReports.length === 0 ? (
                <tr><td className="px-5 py-6 text-sm text-ink-500" colSpan={5}>No lost reports yet.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="overflow-hidden p-0" padded={false}>
        <div className="flex items-center justify-between border-b border-ink-200/60 px-5 py-4">
          <div>
            <p className="font-display text-base font-semibold tracking-tight text-ink-900">Priority matches</p>
            <p className="text-xs text-ink-500">Highest scoring candidates needing review.</p>
          </div>
          <Link to="/staff/matches" className="focus-ring inline-flex items-center gap-1 text-xs font-semibold text-navy-700 hover:underline">
            All matches <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="divide-y divide-ink-100">
          {matches.slice(0, 6).map((match) => {
            const score = Math.round(match.match_score);
            const scoreTone = score >= 85 ? "text-success-700" : score >= 70 ? "text-warn-700" : "text-ink-600";
            return (
              <Link
                key={match.id}
                to="/staff/matches"
                className="grid items-center gap-3 px-5 py-4 transition-colors hover:bg-ink-50/40 sm:grid-cols-[1fr_140px_80px]"
              >
                <div>
                  <p className="font-display text-sm font-semibold tracking-tight text-ink-900">
                    {match.lost_report?.item_title ?? "Lost item"} <span className="text-ink-400">→</span> {match.found_item?.item_title ?? "Found item"}
                  </p>
                  <p className="mt-1 line-clamp-2 text-xs text-ink-500">{match.ai_match_summary}</p>
                </div>
                <StatusPill value={match.confidence_level} />
                <p className={`font-display text-xl font-semibold tabular-nums ${scoreTone}`}>{score}<span className="text-sm text-ink-400">%</span></p>
              </Link>
            );
          })}
          {matches.length === 0 ? <p className="px-5 py-6 text-sm text-ink-500">No candidate matches yet.</p> : null}
        </div>
      </Card>
    </Section>
  );
}

function QueueMetric({ label, value, tone = "navy" }: { label: string; value: number; tone?: "navy" | "success" | "danger" | "warn" }) {
  const tones = {
    navy: "text-navy-800 bg-navy-50 ring-navy-100",
    success: "text-success-700 bg-success-50 ring-success-500/15",
    danger: "text-danger-700 bg-danger-50 ring-danger-500/15",
    warn: "text-warn-700 bg-warn-50 ring-warn-500/15",
  } as const;
  return (
    <div className={`rounded-2xl px-4 py-3 ring-1 ring-inset ${tones[tone]}`}>
      <p className="text-[11px] font-semibold uppercase tracking-wider opacity-80">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function QuickAction({ to, label, icon: Icon }: { to: string; label: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <Link
      to={to}
      className="focus-ring group flex flex-col items-center gap-2 rounded-2xl border border-ink-200 bg-white px-3 py-4 text-center transition-all hover:border-navy-300 hover:bg-navy-50"
    >
      <span className="grid h-9 w-9 place-items-center rounded-2xl bg-ink-100 text-ink-700 transition-colors group-hover:bg-white group-hover:text-navy-700">
        <Icon className="h-4 w-4" />
      </span>
      <span className="text-xs font-semibold tracking-tight text-ink-800">{label}</span>
    </Link>
  );
}
