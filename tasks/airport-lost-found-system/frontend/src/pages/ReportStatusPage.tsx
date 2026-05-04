import { FormEvent, useEffect, useState } from "react";
import axios from "axios";
import { Search } from "lucide-react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { Button, Card, Field, Input, Section } from "../components/ui";
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
    <Section
      kicker="Passenger verification"
      title="Check report status"
      description="Enter the report code we sent you, plus the email or phone you used. Found-item details stay hidden until staff verify your identity in person."
    >
      <div className="mx-auto max-w-xl space-y-4">
        <Card as="form" {...({ onSubmit: verify } as any)} className="space-y-4">
          <Field label="Report code" hint="Format: LR-XXXXXXXX">
            <Input
              name="report_code"
              defaultValue={params.get("code") ?? ""}
              placeholder="LR-XXXXXXXX"
              required
              autoComplete="off"
              className="font-mono"
            />
          </Field>
          <Field label="Email or phone you used">
            <Input name="contact" placeholder="you@example.com or +20…" required />
          </Field>
          {error ? (
            <p className="rounded-2xl border border-danger-500/20 bg-danger-50 px-3 py-2 text-sm font-medium text-danger-700">{error}</p>
          ) : null}
          <Button type="submit" loading={busy} disabled={!session} fullWidth size="lg" leftIcon={<Search className="h-4 w-4" />}>
            Check status
          </Button>
        </Card>
        {message ? (
          <Card className="bg-gradient-to-br from-navy-50 via-white to-gold-50/40">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">Update</p>
            <p className="mt-1 text-sm leading-relaxed text-ink-800">{message}</p>
          </Card>
        ) : null}
      </div>
    </Section>
  );
}
