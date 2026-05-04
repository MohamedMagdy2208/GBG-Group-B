import { useEffect, useState } from "react";
import { Maximize2, X, ImageOff } from "lucide-react";

type Props = {
  lostImageUrl?: string | null;
  foundImageUrl?: string | null;
  lostLabel?: string;
  foundLabel?: string;
};

function resolveUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  if (url.startsWith("/uploads/")) {
    const apiBase = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
    return `${apiBase.replace(/\/$/, "")}${url}`;
  }
  return url;
}

export function ImageComparePanel({ lostImageUrl, foundImageUrl, lostLabel = "Lost report (proof)", foundLabel = "Found item" }: Props) {
  const [zoomed, setZoomed] = useState(false);
  const [splitPercent, setSplitPercent] = useState(50);
  const lost = resolveUrl(lostImageUrl ?? null);
  const found = resolveUrl(foundImageUrl ?? null);

  useEffect(() => {
    if (!zoomed) return;
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") setZoomed(false);
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [zoomed]);

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Visual comparison</h3>
        <button
          type="button"
          onClick={() => setZoomed(true)}
          disabled={!lost && !found}
          className="focus-ring inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2 py-1 text-xs font-medium text-slate-700 disabled:opacity-50"
        >
          <Maximize2 size={12} />
          Compare full-size
        </button>
      </header>
      <div className="grid gap-3 md:grid-cols-2">
        <ImageTile url={lost} label={lostLabel} emptyMessage="Passenger did not provide a photo." />
        <ImageTile url={found} label={foundLabel} emptyMessage="No image stored for this found item." />
      </div>

      {zoomed ? (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Full-size image comparison"
          className="fixed inset-0 z-50 flex flex-col bg-slate-950/90 p-4"
          onClick={(event) => {
            if (event.target === event.currentTarget) setZoomed(false);
          }}
        >
          <header className="flex items-center justify-between text-white">
            <p className="text-sm font-semibold">Compare</p>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs">
                Split
                <input
                  type="range"
                  min={10}
                  max={90}
                  value={splitPercent}
                  onChange={(event) => setSplitPercent(Number(event.target.value))}
                  className="accent-sky-400"
                />
                <span className="font-mono">{splitPercent}%</span>
              </label>
              <button
                type="button"
                onClick={() => setZoomed(false)}
                className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-lg bg-white/10 text-white hover:bg-white/20"
                aria-label="Close comparison"
              >
                <X size={18} />
              </button>
            </div>
          </header>
          <div className="mt-4 grid flex-1 gap-3 md:grid-cols-2">
            <ZoomTile url={lost} label={lostLabel} fillPercent={splitPercent} />
            <ZoomTile url={found} label={foundLabel} fillPercent={100 - splitPercent} />
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ImageTile({ url, label, emptyMessage }: { url: string | null; label: string; emptyMessage: string }) {
  return (
    <figure className="flex flex-col overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
      <figcaption className="border-b border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700">{label}</figcaption>
      <div className="flex min-h-[18rem] w-full items-center justify-center bg-slate-100 p-2">
        {url ? (
          <img
            src={url}
            alt={label}
            className="max-h-[28rem] max-w-full object-contain"
            loading="lazy"
          />
        ) : (
          <div className="flex flex-col items-center gap-1 text-xs text-slate-500">
            <ImageOff size={20} />
            <span>{emptyMessage}</span>
          </div>
        )}
      </div>
    </figure>
  );
}

function ZoomTile({ url, label, fillPercent }: { url: string | null; label: string; fillPercent: number }) {
  return (
    <figure className="flex h-full flex-col overflow-hidden rounded-lg border border-white/20 bg-black">
      <figcaption className="bg-white/10 px-3 py-1.5 text-xs font-semibold text-white">{label}</figcaption>
      <div className="grid flex-1 place-items-center" style={{ minHeight: 0 }}>
        {url ? (
          <img
            src={url}
            alt={label}
            className="object-contain"
            style={{ maxHeight: "100%", maxWidth: "100%", width: `${fillPercent}%` }}
          />
        ) : (
          <div className="flex flex-col items-center gap-1 text-sm text-slate-300">
            <ImageOff size={24} />
            <span>No image</span>
          </div>
        )}
      </div>
    </figure>
  );
}
