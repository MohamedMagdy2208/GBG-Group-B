import { FormEvent, useEffect, useState } from "react";
import axios from "axios";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { ChatSession } from "../types";

export function ReportStatusPage() {
  const [params] = useSearchParams();
  const [session, setSession] = useState<ChatSession | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.post<ChatSession>("/chat/sessions").then((response) => setSession(response.data)).catch(() => setError("Status lookup is temporarily unavailable."));
  }, []);

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;
    setBusy(true);
    setError("");
    setMessage("");
    const data = new FormData(event.currentTarget);
    try {
      const response = await api.post(`/chat/sessions/${session.id}/verify-report`, {
        report_code: data.get("report_code"),
        contact: data.get("contact"),
      });
      setMessage(response.data.assistant_message.message_text);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 403) {
        setError("We could not verify that report with the contact information provided.");
      } else {
        setError("We could not check the report right now. Please try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="max-w-xl">
      <PageHeader title="Report Status" kicker="Passenger verification" />
      <div className="mb-4 rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
        Status lookup requires the report code and matching email or phone. Found-item storage details stay hidden until staff complete verification.
      </div>
      <form onSubmit={verify} className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="report_code" defaultValue={params.get("code") ?? ""} placeholder="Report code" required />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="contact" placeholder="Email or phone" required />
        {error ? <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-700">{error}</p> : null}
        <button disabled={!session || busy} className="focus-ring rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
          {busy ? "Checking..." : "Check status"}
        </button>
      </form>
      {message && <div className="mt-4 rounded-lg border border-sky-200 bg-sky-50 p-4 text-sm font-medium text-sky-900">{message}</div>}
    </section>
  );
}
