import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { ChatSession } from "../types";

export function ReportStatusPage() {
  const [params] = useSearchParams();
  const [session, setSession] = useState<ChatSession | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.post<ChatSession>("/chat/sessions").then((response) => setSession(response.data));
  }, []);

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    const data = new FormData(event.currentTarget);
    const response = await api.post(`/chat/sessions/${session.id}/verify-report`, {
      report_code: data.get("report_code"),
      contact: data.get("contact"),
    });
    setMessage(response.data.assistant_message.message_text);
  }

  return (
    <section className="max-w-xl">
      <PageHeader title="Report Status" kicker="Passenger verification" />
      <form onSubmit={verify} className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="report_code" defaultValue={params.get("code") ?? ""} placeholder="Report code" required />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="contact" placeholder="Email or phone" required />
        <button className="focus-ring rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white">Check status</button>
      </form>
      {message && <div className="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm font-medium text-sky-900">{message}</div>}
    </section>
  );
}
