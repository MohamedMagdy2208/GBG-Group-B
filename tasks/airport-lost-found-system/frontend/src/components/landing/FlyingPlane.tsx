/**
 * Decorative flying-plane animation for the landing hero.
 * SVG plane with a contrail trail and a few drifting clouds — pure CSS, no deps.
 */
export function FlyingPlane() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      {/* Drifting clouds in the background */}
      <Cloud className="absolute top-[18%] left-0 w-24 opacity-60 animate-cloud-drift" style={{ animationDelay: "0s" }} />
      <Cloud className="absolute top-[30%] left-0 w-16 opacity-40 animate-cloud-drift" style={{ animationDelay: "-20s", animationDuration: "75s" }} />
      <Cloud className="absolute top-[55%] left-0 w-32 opacity-50 animate-cloud-drift" style={{ animationDelay: "-45s", animationDuration: "90s" }} />

      {/* The plane + contrail */}
      <div className="absolute top-[40%] left-0 w-full">
        <div className="relative w-fit animate-fly-across">
          <span className="absolute right-full top-1/2 h-0.5 w-40 -translate-y-1/2 rounded-full bg-gradient-to-l from-gold-400/70 via-gold-300/30 to-transparent" />
          <PlaneIcon className="relative h-10 w-10 text-navy-800 drop-shadow-[0_4px_12px_rgba(30,50,96,0.35)]" />
        </div>
      </div>
    </div>
  );
}

function PlaneIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1L15 22v-1.5L13 19v-5.5l8 2.5z" />
    </svg>
  );
}

function Cloud({ className = "", style }: { className?: string; style?: React.CSSProperties }) {
  return (
    <svg viewBox="0 0 64 32" className={className} style={style} fill="white" xmlns="http://www.w3.org/2000/svg">
      <path d="M15 24c-5 0-9-4-9-9 0-4 3-7 7-8 1-4 5-7 9-7 5 0 9 4 9 9h2c4 0 7 3 7 7s-3 7-7 7c-2 0-4-1-5-2H15z" />
    </svg>
  );
}
