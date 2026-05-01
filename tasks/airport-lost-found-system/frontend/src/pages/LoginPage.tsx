import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const data = new FormData(event.currentTarget);
    try {
      let user;
      if (mode === "login") {
        user = await login(String(data.get("email")), String(data.get("password")));
      } else {
        user = await register(String(data.get("name")), String(data.get("email")), String(data.get("password")), String(data.get("phone") || ""));
      }
      navigate(user.role === "passenger" ? "/" : "/staff");
    } catch {
      setError("Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  async function demoLogin(email: string) {
    setError("");
    setBusy(true);
    try {
      const user = await login(email, "Password123!");
      navigate(user.role === "passenger" ? "/" : "/staff");
    } catch {
      setError("Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mx-auto max-w-md">
      <PageHeader title={mode === "login" ? "Sign In" : "Passenger Registration"} kicker="Access" />
      <form onSubmit={submit} className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        {mode === "register" && (
          <>
            <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="name" placeholder="Name" required />
            <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="phone" placeholder="Phone" />
          </>
        )}
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="email" type="email" placeholder="Email" required />
        <input className="focus-ring w-full rounded-lg border border-slate-200 px-3 py-2" name="password" type="password" placeholder="Password" required />
        {error && <p className="text-sm font-medium text-rose-700">{error}</p>}
        <button disabled={busy} className="focus-ring w-full rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50">
          {busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
        </button>
        {mode === "login" ? (
          <div className="grid gap-2 border-t border-slate-100 pt-3 sm:grid-cols-3">
            <DemoButton label="Admin" onClick={() => demoLogin("admin@airport-demo.com")} />
            <DemoButton label="Staff" onClick={() => demoLogin("mona.staff@airport-demo.com")} />
            <DemoButton label="Passenger" onClick={() => demoLogin("passenger1@airport-demo.com")} />
          </div>
        ) : null}
        <button type="button" className="text-sm font-semibold text-sky" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "Create passenger account" : "Use existing account"}
        </button>
      </form>
    </section>
  );
}

function DemoButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="focus-ring rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50">
      {label}
    </button>
  );
}
