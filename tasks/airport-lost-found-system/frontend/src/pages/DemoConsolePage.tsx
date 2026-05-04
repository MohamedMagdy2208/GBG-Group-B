import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Play, RotateCcw, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { Badge } from "../components/Badge";

type Scenario = { key: string; title: string; summary: string };

type DemoEvent = {
  step: number;
  label: string;
  payload: Record<string, unknown>;
  at: string;
};

type DemoRun = {
  run_id: string;
  scenario: string;
  status: "running" | "succeeded" | "failed" | "cleaned";
  events: DemoEvent[];
  created_records: Record<string, number[]>;
  started_at: string;
  finished_at: string | null;
  error: string | null;
};

export function DemoConsolePage() {
  const queryClient = useQueryClient();
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const scenariosQuery = useQuery({
    queryKey: ["demo-scenarios"],
    queryFn: async () => (await api.get<{ scenarios: Scenario[] }>("/admin/demo/scenarios")).data.scenarios,
  });

  const runsQuery = useQuery({
    queryKey: ["demo-runs"],
    queryFn: async () => (await api.get<{ runs: DemoRun[] }>("/admin/demo/runs")).data.runs,
    refetchInterval: 4000,
  });

  const activeRun = runsQuery.data?.find((run) => run.run_id === activeRunId) ?? null;

  const startMutation = useMutation({
    mutationFn: async (scenarioKey: string) =>
      (await api.post<DemoRun>(`/admin/demo/scenarios/${scenarioKey}`)).data,
    onSuccess: (run) => {
      setActiveRunId(run.run_id);
      queryClient.invalidateQueries({ queryKey: ["demo-runs"] });
      queryClient.invalidateQueries({ queryKey: ["matches"] });
      queryClient.invalidateQueries({ queryKey: ["lost-reports"] });
      queryClient.invalidateQueries({ queryKey: ["found-items"] });
    },
  });

  const cleanupMutation = useMutation({
    mutationFn: async (runId: string) => (await api.delete(`/admin/demo/runs/${runId}`)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["demo-runs"] });
    },
  });

  useEffect(() => {
    if (!activeRunId && runsQuery.data && runsQuery.data.length) {
      setActiveRunId(runsQuery.data[runsQuery.data.length - 1].run_id);
    }
  }, [activeRunId, runsQuery.data]);

  return (
    <section className="grid gap-5">
      <PageHeader
        title="Demo Console"
        kicker="Admin"
        action={
          <span className="text-xs text-slate-500">
            Each scenario seeds a passenger, a lost report, and a found item, runs the AI pipeline, and walks through approval and release.
          </span>
        }
      />

      <div className="grid gap-3 md:grid-cols-3">
        {scenariosQuery.isLoading ? (
          <p className="text-sm text-slate-500">Loading scenarios...</p>
        ) : (
          (scenariosQuery.data ?? []).map((scenario) => (
            <article key={scenario.key} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-slate-900">{scenario.title}</h3>
              <p className="mt-1 text-xs text-slate-600">{scenario.summary}</p>
              <button
                type="button"
                onClick={() => startMutation.mutate(scenario.key)}
                disabled={startMutation.isPending}
                className="focus-ring mt-3 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
              >
                <Play size={14} />
                {startMutation.isPending && startMutation.variables === scenario.key ? "Running..." : "Run scenario"}
              </button>
            </article>
          ))
        )}
      </div>

      {startMutation.isError ? (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {axios.isAxiosError(startMutation.error) && typeof startMutation.error.response?.data?.detail === "string"
            ? startMutation.error.response?.data?.detail
            : "Could not start the scenario."}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1fr,2fr]">
        <aside className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <header className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-900">Recent runs</h3>
            <button
              type="button"
              onClick={() => runsQuery.refetch()}
              className="focus-ring rounded p-1 text-slate-500 hover:bg-slate-100"
              aria-label="Refresh runs"
            >
              <RotateCcw size={14} />
            </button>
          </header>
          <ul className="mt-3 grid gap-2">
            {(runsQuery.data ?? []).slice().reverse().map((run) => (
              <li key={run.run_id}>
                <button
                  type="button"
                  onClick={() => setActiveRunId(run.run_id)}
                  className={`flex w-full items-center justify-between rounded-lg border px-2 py-1.5 text-left text-xs ${
                    activeRunId === run.run_id ? "border-slate-900 bg-slate-50" : "border-slate-200"
                  }`}
                >
                  <span className="font-mono text-[11px] text-slate-700">{run.run_id}</span>
                  <Badge value={run.status} />
                </button>
              </li>
            ))}
            {(runsQuery.data ?? []).length === 0 ? <li className="text-xs text-slate-500">No runs yet.</li> : null}
          </ul>
        </aside>

        <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          {activeRun ? (
            <>
              <header className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-slate-900">{activeRun.scenario}</h3>
                  <p className="text-xs text-slate-500">
                    Run <span className="font-mono">{activeRun.run_id}</span> · started {new Date(activeRun.started_at).toLocaleTimeString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge value={activeRun.status} />
                  {activeRun.status !== "cleaned" ? (
                    <button
                      type="button"
                      onClick={() => cleanupMutation.mutate(activeRun.run_id)}
                      disabled={cleanupMutation.isPending}
                      className="focus-ring inline-flex items-center gap-1 rounded-lg border border-rose-200 px-2 py-1 text-xs text-rose-700 disabled:opacity-60"
                    >
                      <Trash2 size={12} />
                      Clean up
                    </button>
                  ) : null}
                </div>
              </header>

              {activeRun.error ? (
                <p className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{activeRun.error}</p>
              ) : null}

              <ol className="mt-4 grid gap-2">
                {activeRun.events.map((event) => (
                  <li key={event.step} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                    <div className="flex items-center justify-between text-xs text-slate-500">
                      <span>Step {event.step}</span>
                      <span>{new Date(event.at).toLocaleTimeString()}</span>
                    </div>
                    <p className="mt-0.5 text-sm font-medium text-slate-900">{event.label}</p>
                    {Object.keys(event.payload).length ? (
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words rounded bg-white px-2 py-1 text-[11px] text-slate-700">
                        {JSON.stringify(event.payload, null, 0)}
                      </pre>
                    ) : null}
                  </li>
                ))}
              </ol>
            </>
          ) : (
            <p className="text-sm text-slate-500">Select or start a run to see the timeline.</p>
          )}
        </article>
      </div>
    </section>
  );
}
