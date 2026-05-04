import { useEffect, useRef, useState } from "react";

type Props = {
  to: number;
  duration?: number; // ms
  decimals?: number;
  suffix?: string;
  className?: string;
};

/**
 * Smooth count-up that respects prefers-reduced-motion.
 * Uses requestAnimationFrame so it stays buttery on long values.
 */
export function CountUp({ to, duration = 1400, decimals = 0, suffix = "", className = "" }: Props) {
  const [value, setValue] = useState(0);
  const ref = useRef<HTMLSpanElement | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setValue(to);
      started.current = true;
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && !started.current) {
            started.current = true;
            const start = performance.now();
            const tick = (now: number) => {
              const elapsed = now - start;
              const progress = Math.min(1, elapsed / duration);
              // ease-out cubic
              const eased = 1 - Math.pow(1 - progress, 3);
              setValue(eased * to);
              if (progress < 1) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
            observer.disconnect();
          }
        }
      },
      { threshold: 0.4 },
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [to, duration]);

  return (
    <span ref={ref} className={`tabular-nums ${className}`}>
      {value.toFixed(decimals)}
      {suffix}
    </span>
  );
}
