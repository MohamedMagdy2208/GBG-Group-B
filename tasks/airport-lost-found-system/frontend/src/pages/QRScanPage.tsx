import { FormEvent, useEffect, useRef, useState } from "react";
import { Camera, Search } from "lucide-react";
import { api } from "../api/client";
import { Badge } from "../components/Badge";
import { PageHeader } from "../components/PageHeader";
import type { LabelScanResponse } from "../types";

export function QRScanPage() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [code, setCode] = useState("");
  const [result, setResult] = useState<LabelScanResponse | null>(null);
  const [cameraStatus, setCameraStatus] = useState("Camera scanner uses the browser BarcodeDetector when available.");

  useEffect(() => {
    let stopped = false;
    let stream: MediaStream | null = null;

    async function start() {
      const BarcodeDetector = (window as any).BarcodeDetector;
      if (!BarcodeDetector || !navigator.mediaDevices?.getUserMedia) return;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        const detector = new BarcodeDetector({ formats: ["qr_code"] });
        const loop = async () => {
          if (stopped || !videoRef.current) return;
          const detections = await detector.detect(videoRef.current).catch(() => []);
          const rawValue = detections[0]?.rawValue;
          if (rawValue) {
            setCode(rawValue);
            await scan(rawValue);
            return;
          }
          requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
      } catch {
        setCameraStatus("Camera scanner is unavailable. Enter the QR code manually.");
      }
    }

    void start();
    return () => {
      stopped = true;
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  async function scan(value = code) {
    if (!value.trim()) return;
    const response = await api.post<LabelScanResponse>("/labels/scan", {
      label_code: value,
      notes: "Scanned from staff QR page",
    });
    setResult(response.data);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await scan();
  }

  return (
    <section className="space-y-4">
      <PageHeader title="QR Custody Scan" kicker="Found item label lookup" />
      <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="aspect-video overflow-hidden rounded-lg bg-slate-900">
            <video ref={videoRef} className="h-full w-full object-cover" muted playsInline />
          </div>
          <p className="mt-3 text-sm text-slate-500">{cameraStatus}</p>
          <form onSubmit={submit} className="mt-4 flex gap-2">
            <input value={code} onChange={(event) => setCode(event.target.value)} className="focus-ring flex-1 rounded-lg border border-slate-200 px-3 py-2" placeholder="LF-..." />
            <button className="focus-ring inline-flex items-center gap-2 rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white">
              <Search className="h-4 w-4" />
              Scan
            </button>
          </form>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Camera className="h-5 w-5 text-radar" />
            <h2 className="font-semibold text-slate-950">Scan result</h2>
          </div>
          {result ? (
            <div className="mt-4 space-y-3">
              <div className="flex flex-wrap gap-2">
                <Badge value={result.label.status} />
                <Badge value={result.found_item?.status} />
                <Badge value={result.found_item?.risk_level} />
              </div>
              <p className="text-sm"><b>Label:</b> {result.label.label_code}</p>
              <p className="text-sm"><b>Found item:</b> {result.found_item?.item_title ?? "Unknown"}</p>
              <p className="text-sm"><b>Storage:</b> {result.found_item?.storage_location ?? "Not assigned"}</p>
              <p className="text-sm"><b>Scans:</b> {result.label.scan_count}</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-500">Scan a QR label or enter a label code to open the custody context.</p>
          )}
        </div>
      </div>
    </section>
  );
}
