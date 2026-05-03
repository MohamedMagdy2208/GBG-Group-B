import { FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";

type CustodyEvent = {
  id: number;
  action: string;
  location?: string | null;
  notes?: string | null;
  timestamp: string;
};

export function CustodyTimelinePage() {
  const { id } = useParams();
  const client = useQueryClient();
  const { data = [] } = useQuery({
    queryKey: ["custody", id],
    queryFn: async () => (await api.get<CustodyEvent[]>(`/found-items/${id}/custody-events`)).data,
  });
  const mutation = useMutation({
    mutationFn: async (payload: Record<string, FormDataEntryValue>) => (await api.post(`/found-items/${id}/custody-events`, payload)).data,
    onSuccess: () => client.invalidateQueries({ queryKey: ["custody", id] }),
  });
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    mutation.mutate({ action: form.get("action")!, location: form.get("location")!, notes: form.get("notes")! });
    event.currentTarget.reset();
  }
  return (
    <section className="space-y-4">
      <PageHeader title="Custody Timeline" kicker={`Found item ${id}`} />
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <ol className="space-y-4">
            {data.map((event) => (
              <li key={event.id} className="border-l-2 border-sky pl-4">
                <p className="font-semibold capitalize text-slate-950">{event.action.replaceAll("_", " ")}</p>
                <p className="text-sm text-slate-500">{event.location} · {new Date(event.timestamp).toLocaleString()}</p>
                <p className="mt-1 text-sm text-slate-700">{event.notes}</p>
              </li>
            ))}
          </ol>
        </div>
        <form onSubmit={submit} className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <select className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="action" defaultValue="note">
            {["stored", "moved", "matched", "claimed", "released", "disposed", "note"].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
          <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="location" placeholder="Location" />
          <textarea className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="notes" placeholder="Notes" />
          <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Add event</button>
        </form>
      </div>
    </section>
  );
}
