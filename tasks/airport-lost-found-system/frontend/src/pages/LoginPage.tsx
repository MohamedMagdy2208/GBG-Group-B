import { FormEvent, useState } from "react";
import axios from "axios";
import { Plane, ShieldCheck, UserCircle, Wrench } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button, Card, Field, Input } from "../components/ui";
import { useToast } from "../components/Toast";
import { useAuth } from "../hooks/useAuth";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.response?.status === 401) return "Invalid email or password.";
    if (error.response?.status === 423) return "Account is temporarily locked. Try again later.";
    if (error.message) return error.message;
  }
  return fallback;
}

export function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      const user = mode === "login"
        ? await login(String(data.get("email")), String(data.get("password")))
        : await register(
            String(data.get("name")),
            String(data.get("email")),
            String(data.get("password")),
            String(data.get("phone") || ""),
          );
      toast.push(`Welcome back, ${user.name}`, "success");
      navigate(user.role === "passenger" ? "/" : "/staff");
    } catch (err) {
      const msg = describeError(err, "Authentication failed.");
      setError(msg);
      toast.push(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  async function demoLogin(email: string) {
    setError("");
    setBusy(true);
    try {
      const user = await login(email, "Password123!");
      toast.push(`Signed in as ${user.name}`, "success");
      navigate(user.role === "passenger" ? "/" : "/staff");
    } catch (err) {
      const msg = describeError(err, "Authentication failed.");
      setError(msg);
      toast.push(msg, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="grid gap-10 lg:grid-cols-[1.1fr_1fr] lg:items-center">
      <aside className="hidden lg:block">
        <div className="grid h-12 w-12 place-items-center rounded-3xl bg-gradient-navy text-white shadow-navy">
          <Plane className="h-6 w-6 -rotate-45" />
        </div>
        <p className="mt-6 text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">Airport Operations</p>
        <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight text-ink-900">
          AI-powered <span className="text-navy-700">Lost &amp; Found</span>.
        </h1>
        <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-600">
          Match passenger reports with found items in seconds. Multimodal AI, side-by-side image review, and full audit trail —
          built for terminal, security, and lost-and-found teams.
        </p>
        <ul className="mt-6 grid gap-3 text-sm text-ink-700">
          <li className="flex items-start gap-3">
            <span className="mt-0.5 grid h-7 w-7 place-items-center rounded-xl bg-success-50 text-success-700 ring-1 ring-success-500/15">✓</span>
            <span>Vision + LLM auto-describes every photo</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="mt-0.5 grid h-7 w-7 place-items-center rounded-xl bg-success-50 text-success-700 ring-1 ring-success-500/15">✓</span>
            <span>Manual approval gate before any release</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="mt-0.5 grid h-7 w-7 place-items-center rounded-xl bg-success-50 text-success-700 ring-1 ring-success-500/15">✓</span>
            <span>Bilingual passenger chat in English &amp; Arabic</span>
          </li>
        </ul>
      </aside>

      <Card className="mx-auto w-full max-w-md p-7">
        <header className="mb-5">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">
            {mode === "login" ? "Sign in" : "Create passenger account"}
          </p>
          <h2 className="mt-1 font-display text-2xl font-semibold tracking-tight text-ink-900">
            {mode === "login" ? "Welcome back" : "Tell us a little about you"}
          </h2>
          <p className="mt-1 text-sm text-ink-500">
            {mode === "login"
              ? "Use your account or one of the demo logins below."
              : "Passenger accounts can file lost-item reports and check status updates."}
          </p>
        </header>

        <form onSubmit={submit} className="space-y-3">
          {mode === "register" ? (
            <>
              <Field label="Name">
                <Input name="name" placeholder="Your full name" required autoComplete="name" />
              </Field>
              <Field label="Phone" optional>
                <Input name="phone" placeholder="+20 100 000 0000" autoComplete="tel" />
              </Field>
            </>
          ) : null}
          <Field label="Email">
            <Input name="email" type="email" placeholder="you@example.com" required autoComplete="email" invalid={!!error} />
          </Field>
          <Field label="Password" hint={mode === "register" ? "Minimum 12 chars, mix of cases, digit, symbol." : undefined}>
            <Input
              name="password"
              type="password"
              placeholder="••••••••••••"
              required
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              minLength={mode === "register" ? 12 : undefined}
              invalid={!!error}
            />
          </Field>
          {error ? (
            <p className="rounded-2xl border border-danger-500/20 bg-danger-50 px-3 py-2 text-sm font-medium text-danger-700">
              {error}
            </p>
          ) : null}
          <Button type="submit" loading={busy} fullWidth size="lg">
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
        </form>

        {mode === "login" ? (
          <>
            <div className="my-5 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-wider text-ink-400">
              <span className="h-px flex-1 bg-ink-200" />
              <span>Demo logins</span>
              <span className="h-px flex-1 bg-ink-200" />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <DemoTile icon={<ShieldCheck className="h-4 w-4" />} label="Admin" onClick={() => demoLogin("admin@airport-demo.com")} disabled={busy} />
              <DemoTile icon={<Wrench className="h-4 w-4" />} label="Staff" onClick={() => demoLogin("mona.staff@airport-demo.com")} disabled={busy} />
              <DemoTile icon={<UserCircle className="h-4 w-4" />} label="Passenger" onClick={() => demoLogin("passenger1@airport-demo.com")} disabled={busy} />
            </div>
          </>
        ) : null}

        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
          className="focus-ring mt-5 w-full rounded-2xl py-2 text-center text-sm font-semibold text-navy-700 hover:bg-navy-50"
        >
          {mode === "login" ? "Create a passenger account" : "I already have an account"}
        </button>
      </Card>
    </section>
  );
}

function DemoTile({ icon, label, onClick, disabled }: { icon: React.ReactNode; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="focus-ring group flex flex-col items-center gap-1.5 rounded-2xl border border-ink-200 bg-white px-2 py-3 text-xs font-semibold text-ink-700 transition-all hover:border-navy-300 hover:bg-navy-50 hover:text-navy-800 disabled:opacity-50"
    >
      <span className="grid h-8 w-8 place-items-center rounded-xl bg-ink-100 text-ink-600 group-hover:bg-white group-hover:text-navy-700">
        {icon}
      </span>
      {label}
    </button>
  );
}
