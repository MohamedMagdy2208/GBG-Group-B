import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Boxes, ClipboardList, PackagePlus, ScanLine, Search, TrendingUp } from "lucide-react";
import type React from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
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
    <div className="space-y-5">
      <PageHeader title="Staff Dashboard" kicker={user ? `${user.name} - ${user.role}` : "Operations"} />
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard label="Open lost reports" value={summary?.open_lost_reports ?? 0} icon={ClipboardList} accent="radar" />
        <StatCard label="Registered found" value={summary?.registered_found_items ?? 0} icon={Boxes} />
        <StatCard label="Pending matches" value={summary?.pending_matches ?? 0} icon={Search} accent="amber" />
        <StatCard label="Average score" value={summary?.average_match_score ?? 0} icon={TrendingUp} accent="radar" />
      </div>

      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amberline" />
            <h2 className="font-semibold text-slate-950">Operations Queue</h2>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <QueueMetric label="High confidence" value={highConfidencePending.length} tone="high" />
            <QueueMetric label="Risk review" value={blockedOrSensitive.length} tone="risk" />
            <QueueMetric label="Open reports" value={summary?.open_lost_reports ?? 0} />
          </div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="font-semibold text-slate-950">Quick Actions</h2>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <QuickAction to="/staff/found/new" label="Register found" icon={PackagePlus} />
            <QuickAction to="/staff/matches" label="Review matches" icon={Search} />
            <QuickAction to="/staff/scan" label="Scan QR" icon={ScanLine} />
          </div>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 p-4">
          <h2 className="font-semibold text-slate-950">Recent Lost Reports</h2>
          <Link to="/staff/lost" className="text-sm font-semibold text-radar hover:text-slate-950">
            View all
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-normal text-slate-500">
              <tr>
                <th className="p-3">Code</th>
                <th>Item</th>
                <th>Category</th>
                <th>Location</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {lostReports.slice(0, 6).map((report) => (
                <tr key={report.id} className="hover:bg-slate-50">
                  <td className="p-3 font-semibold text-slate-950">
                    <Link to={`/staff/lost/${report.id}`}>{report.report_code}</Link>
                  </td>
                  <td>{report.item_title}</td>
                  <td>{report.category}</td>
                  <td>{report.lost_location}</td>
                  <td>
                    <Badge value={report.status} />
                  </td>
                </tr>
              ))}
              {lostReports.length === 0 ? (
                <tr>
                  <td className="p-4 text-slate-500" colSpan={5}>
                    No lost reports yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4">
          <h2 className="font-semibold text-slate-950">Priority Matches</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {matches.slice(0, 6).map((match) => (
            <Link key={match.id} to="/staff/matches" className="grid gap-3 p-4 hover:bg-slate-50 sm:grid-cols-[1fr_120px_120px]">
              <div>
                <p className="font-semibold text-slate-950">
                  {match.lost_report?.item_title ?? "Lost item"} to {match.found_item?.item_title ?? "Found item"}
                </p>
                <p className="mt-1 text-sm text-slate-500">{match.ai_match_summary}</p>
              </div>
              <Badge value={match.confidence_level} />
              <p className="text-lg font-semibold text-slate-950">{match.match_score.toFixed(0)}%</p>
            </Link>
          ))}
          {matches.length === 0 ? <p className="p-4 text-sm text-slate-500">No candidate matches yet.</p> : null}
        </div>
      </section>
    </div>
  );
}

function QueueMetric({ label, value, tone = "normal" }: { label: string; value: number; tone?: "normal" | "high" | "risk" }) {
  const toneClass = tone === "risk" ? "text-rose-700" : tone === "high" ? "text-radar" : "text-slate-950";
  return (
    <div className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
      <p className="text-xs font-semibold uppercase tracking-normal text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</p>
    </div>
  );
}

function QuickAction({ to, label, icon: Icon }: { to: string; label: string; icon: React.ComponentType<{ className?: string }> }) {
  return (
    <Link to={to} className="focus-ring inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
      <Icon className="h-4 w-4" />
      {label}
    </Link>
  );
}
