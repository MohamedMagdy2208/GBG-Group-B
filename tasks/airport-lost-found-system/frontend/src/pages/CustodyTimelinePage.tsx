import { FormEvent, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Loader2 } from "lucide-react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { useToast } from "../components/Toast";

type CustodyEvent = {
  id: number;
  action: string;
  location?: string | null;
  notes?: string | null;
  timestamp: string;
};

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function CustodyTimelinePage() {
  const { id } = useParams();
  const client = useQueryClient();
  const toast = useToast();
  const formRef = useRef<HTMLFormElement | null>(null);
  const { data = [], isLoading } = useQuery({
    queryKey: ["custody", id],
    queryFn: async () => (await api.get<CustodyEvent[]>(`/found-items/${id}/custody-events`)).data,
  });
  const mutation = useMutation({
    mutationFn: async (payload: Record<string, string>) => (await api.post(`/found-items/${id}/custody-events`, payload)).data,
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["custody", id] });
      toast.push("Custody event added.", "success");
      formRef.current?.reset();
    },
    onError: (error) => toast.push(describeError(error, "Could not add custody event."), "error"),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({
      action: String(form.get("action") ?? "note"),
      location: String(form.get("location") ?? ""),
      notes: String(form.get("notes") ?? ""),
    });
  }
  return (
    <section className="space-y-4">
      <PageHeader title="Custody Timeline" kicker={`Found item ${id}`} />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          {isLoading ? (
            <p className="text-sm text-slate-500">Loading custody events...</p>
          ) : data.length === 0 ? (
            <EmptyState title="No custody events yet" description="Use the form on the right to add the first event." />
          ) : (
            <ol className="space-y-4">
              {data.map((event) => (
                <li key={event.id} className="border-l-2 border-sky pl-4">
                  <p className="font-semibold capitalize text-slate-950">{event.action.replaceAll("_", " ")}</p>
                  <p className="text-sm text-slate-500">{event.location ?? "—"} · {new Date(event.timestamp).toLocaleString()}</p>
                  {event.notes ? <p className="mt-1 text-sm text-slate-700">{event.notes}</p> : null}
                </li>
              ))}
            </ol>
          )}
        </div>
        <form ref={formRef} onSubmit={submit} className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <select className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="action" defaultValue="note">
            {["stored", "moved", "matched", "claimed", "released", "disposed", "note"].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
          <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="location" placeholder="Location" />
          <textarea className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="notes" placeholder="Notes" />
          <button
            type="submit"
            disabled={mutation.isPending}
            className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {mutation.isPending ? <Loader2 size={14} className="animate-spin" /> : null}
            {mutation.isPending ? "Adding..." : "Add event"}
          </button>
        </form>
      </div>
    </section>
  );
}
