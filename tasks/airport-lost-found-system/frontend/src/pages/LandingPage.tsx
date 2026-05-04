import { ArrowRight, Bot, Camera, ClipboardCheck, Eye, Plane, Search, ShieldCheck, Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { CountUp } from "../components/landing/CountUp";
import { FlyingPlane } from "../components/landing/FlyingPlane";
import { LiveChatPreview } from "../components/landing/LiveChatPreview";

export function LandingPage() {
  const heroRef = useRef<HTMLDivElement | null>(null);
  const [parallax, setParallax] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const el = heroRef.current;
    if (!el) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) return;
    const target = el;
    function handle(event: MouseEvent) {
      const rect = target.getBoundingClientRect();
      const cx = (event.clientX - rect.left) / rect.width - 0.5;
      const cy = (event.clientY - rect.top) / rect.height - 0.5;
      setParallax({ x: cx, y: cy });
    }
    target.addEventListener("mousemove", handle);
    return () => target.removeEventListener("mousemove", handle);
  }, []);

  return (
    <div className="space-y-12">
      {/* HERO */}
      <section
        ref={heroRef}
        className="relative overflow-hidden rounded-[2rem] border border-ink-200/60 bg-white p-8 shadow-card lg:p-12"
      >
        {/* Animated background blurs that follow the cursor very gently */}
        <div
          className="absolute -right-32 -top-32 h-[28rem] w-[28rem] rounded-full bg-gold-100/60 blur-3xl transition-transform duration-700 ease-out"
          style={{ transform: `translate(${parallax.x * 30}px, ${parallax.y * 30}px)` }}
          aria-hidden
        />
        <div
          className="absolute -bottom-40 -left-32 h-[28rem] w-[28rem] rounded-full bg-navy-100/60 blur-3xl transition-transform duration-700 ease-out"
          style={{ transform: `translate(${-parallax.x * 30}px, ${-parallax.y * 30}px)` }}
          aria-hidden
        />

        {/* The plane + clouds animation across the hero */}
        <FlyingPlane />

        <div className="relative grid gap-10 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-gold-200 bg-gold-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700 animate-fade-in">
              <Sparkles className="h-3.5 w-3.5 animate-float-soft" />
              AI-assisted intake &amp; matching
            </div>
            <h1 className="mt-4 font-display text-4xl font-semibold leading-[1.1] tracking-tight text-ink-900 lg:text-6xl">
              Reunite passengers with their belongings —{" "}
              <span className="bg-gradient-to-r from-navy-700 via-navy-600 to-gold-600 bg-clip-text text-transparent" style={{ backgroundSize: "200% 100%", animation: "gradient-shift 6s ease infinite" }}>
                in minutes.
              </span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-ink-600">
              Vision, embeddings, and hybrid search work together so airport staff spend their time on judgment calls — not data entry.
            </p>

            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link
                to="/chat"
                className="focus-ring group inline-flex items-center gap-2 rounded-full bg-gradient-navy px-5 py-3 text-sm font-semibold text-white shadow-navy transition-all hover:brightness-110 active:scale-[0.98]"
              >
                <Bot className="h-4 w-4" /> Talk to the assistant
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                to="/lost-report"
                className="focus-ring inline-flex items-center gap-2 rounded-full border border-ink-200 bg-white px-5 py-3 text-sm font-semibold text-ink-800 transition-all hover:border-ink-300 hover:bg-ink-50"
              >
                <ClipboardCheck className="h-4 w-4" /> File a report
              </Link>
              <Link
                to="/lost-report/photo"
                className="focus-ring inline-flex items-center gap-2 rounded-full bg-gradient-gold px-5 py-3 text-sm font-semibold text-navy-950 shadow-gold transition-all hover:brightness-105 active:scale-[0.98]"
              >
                <Camera className="h-4 w-4" /> Search by photo
              </Link>
            </div>

            {/* Counters */}
            <div className="mt-9 grid max-w-md grid-cols-3 gap-4">
              <Counter value={48} label="Reports today" />
              <Counter value={92} suffix="%" label="Match accuracy" />
              <Counter value={2.3} decimals={1} suffix="m" label="Avg resolution" />
            </div>
          </div>

          {/* Right side: tilting hero panel with live chat */}
          <div className="tilt-card relative">
            <div className="absolute inset-0 -m-4 rounded-[2.5rem] bg-gradient-navy opacity-95" aria-hidden />
            <div className="absolute -inset-1 -m-4 animate-float-slow rounded-[2.5rem] bg-gradient-to-br from-gold-400/30 via-transparent to-navy-400/30 opacity-50 blur-xl" aria-hidden />

            <div className="relative grid gap-3 rounded-3xl border border-white/10 p-5 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="grid h-9 w-9 place-items-center rounded-2xl bg-white/15 backdrop-blur">
                    <Plane className="h-4 w-4 -rotate-45 text-gold-300" />
                  </span>
                  <p className="font-display text-sm font-semibold">Live operations</p>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-success-500/20 px-2 py-0.5 text-[11px] font-semibold text-success-50">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-success-500 opacity-75" />
                    <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-success-500" />
                  </span>
                  Online
                </span>
              </div>

              <LiveChatPreview />
            </div>
          </div>
        </div>
      </section>

      {/* PILLARS with 3D tilt */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Pillar
          icon={<Bot className="h-5 w-5" />}
          title="Bilingual chat intake"
          description="English and Arabic guided assistant captures missing details and suggests follow-up questions."
        />
        <Pillar
          icon={<Camera className="h-5 w-5" />}
          title="Photo-only matching"
          description="Vision describes the item and pHash + multimodal embeddings find visual look-alikes."
        />
        <Pillar
          icon={<Eye className="h-5 w-5" />}
          title="Side-by-side review"
          description="Staff see both photos with highlighted evidence spans before approving any release."
        />
        <Pillar
          icon={<ShieldCheck className="h-5 w-5" />}
          title="Audit-grade release"
          description="Identity check, fraud signals, custody chain — every state change is logged."
        />
      </section>

      {/* HOW IT WORKS — animated timeline */}
      <section className="rounded-[2rem] border border-ink-200/60 bg-white p-8 shadow-card lg:p-12">
        <div className="mb-8 text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">How it works</p>
          <h2 className="mt-1 font-display text-3xl font-semibold tracking-tight text-ink-900">
            From lost to <span className="text-navy-700">found</span> in 3 steps.
          </h2>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          <Step number={1} title="Passenger reports" description="Type, talk, or upload a photo. AI cleans the description and extracts attributes." icon={<Bot className="h-5 w-5" />} />
          <Step number={2} title="Hybrid match" description="Azure Search + LLM rerank + image similarity rank candidates from the staff catalogue." icon={<Search className="h-5 w-5" />} />
          <Step number={3} title="Manual release" description="Staff verify identity, confirm checklist, and release with a complete audit trail." icon={<ShieldCheck className="h-5 w-5" />} />
        </div>
      </section>
    </div>
  );
}

function Counter({ value, label, suffix, decimals }: { value: number; label: string; suffix?: string; decimals?: number }) {
  return (
    <div className="rounded-2xl bg-ink-50/80 px-4 py-3 ring-1 ring-ink-200/40">
      <p className="font-display text-2xl font-semibold tracking-tight text-navy-800">
        <CountUp to={value} suffix={suffix} decimals={decimals ?? 0} />
      </p>
      <p className="mt-0.5 text-[11px] font-semibold uppercase tracking-wider text-ink-500">{label}</p>
    </div>
  );
}

function Pillar({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="tilt-card glow-hover rounded-3xl border border-ink-200/60 bg-white p-5 shadow-card transition-all duration-300 ease-apple hover:shadow-card-hover">
      <span className="grid h-10 w-10 place-items-center rounded-2xl bg-navy-50 text-navy-700 ring-1 ring-navy-100 transition-transform group-hover:scale-110">
        {icon}
      </span>
      <p className="mt-3 font-display text-base font-semibold tracking-tight text-ink-900">{title}</p>
      <p className="mt-1 text-sm text-ink-600">{description}</p>
    </div>
  );
}

function Step({ number, title, description, icon }: { number: number; title: string; description: string; icon: React.ReactNode }) {
  return (
    <div className="tilt-card group relative rounded-3xl border border-ink-200/60 bg-gradient-to-br from-white to-ink-50/40 p-6 transition-all hover:shadow-card-hover">
      <div className="absolute -right-2 -top-2 grid h-12 w-12 place-items-center rounded-2xl bg-gradient-gold font-display text-lg font-bold text-navy-950 shadow-gold transition-transform group-hover:rotate-6 group-hover:scale-110">
        {number}
      </div>
      <span className="grid h-10 w-10 place-items-center rounded-2xl bg-navy-50 text-navy-700 ring-1 ring-navy-100">
        {icon}
      </span>
      <p className="mt-3 font-display text-lg font-semibold tracking-tight text-ink-900">{title}</p>
      <p className="mt-1 text-sm leading-relaxed text-ink-600">{description}</p>
    </div>
  );
}
