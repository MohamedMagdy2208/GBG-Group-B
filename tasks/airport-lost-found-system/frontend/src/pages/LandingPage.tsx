import { ArrowRight, Bot, ClipboardCheck, Plane, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";

export function LandingPage() {
  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="p-6 lg:p-10">
            <PageHeader title="Airport Lost & Found Operations" kicker="AI-assisted intake and matching" />
            <p className="max-w-2xl text-sm leading-6 text-slate-600">
              Passengers report items, staff register found property, and AI-powered matching helps operations teams review candidates with clear evidence and manual approvals.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white" to="/chat">
                <Bot className="h-4 w-4" /> Chat assistant <ArrowRight className="h-4 w-4" />
              </Link>
              <Link className="focus-ring inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700" to="/lost-report">
                <ClipboardCheck className="h-4 w-4" /> Report item
              </Link>
            </div>
          </div>
          <div className="min-h-[280px] bg-slate-900 p-6 text-white">
            <div className="grid h-full content-between rounded-lg border border-white/10 p-5">
              <div className="flex items-center justify-between">
                <Plane className="h-8 w-8 text-sky-300" />
                <span className="rounded-md bg-emerald-400/15 px-2 py-1 text-xs font-semibold text-emerald-200">Live Ops</span>
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {["Image OCR", "Hybrid Search", "Manual Release"].map((item) => (
                  <div key={item} className="rounded-lg border border-white/10 bg-white/5 p-3">
                    <ShieldCheck className="mb-3 h-4 w-4 text-emerald-300" />
                    <p className="text-sm font-semibold">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
