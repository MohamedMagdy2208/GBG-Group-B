import { useEffect, useState } from "react";
import { Bot, UserCircle2 } from "lucide-react";

type Bubble = {
  id: number;
  role: "passenger" | "assistant";
  text: string;
  delayBefore: number; // ms before this bubble appears
};

const SCRIPT: Bubble[] = [
  { id: 1, role: "assistant", text: "Hi! What did you lose?", delayBefore: 600 },
  { id: 2, role: "passenger", text: "Black iPhone 14 at gate B12.", delayBefore: 1500 },
  { id: 3, role: "assistant", text: "What time were you there?", delayBefore: 1100 },
  { id: 4, role: "passenger", text: "Around 10:30am.", delayBefore: 1300 },
  { id: 5, role: "assistant", text: "Found a match — confidence 92%. Staff will contact you.", delayBefore: 1700 },
];

const TOTAL_TIME = SCRIPT.reduce((sum, bubble) => sum + bubble.delayBefore, 0) + 2500;

/**
 * Auto-playing chat preview for the landing page.
 * Loops the same scripted conversation so visitors see the assistant in action.
 */
export function LiveChatPreview() {
  const [visible, setVisible] = useState<number[]>([]);
  const [typingFor, setTypingFor] = useState<"passenger" | "assistant" | null>("assistant");

  useEffect(() => {
    let cancelled = false;
    const timeouts: ReturnType<typeof setTimeout>[] = [];

    function play() {
      setVisible([]);
      let elapsed = 0;
      SCRIPT.forEach((bubble, index) => {
        elapsed += bubble.delayBefore;
        timeouts.push(
          setTimeout(() => {
            if (cancelled) return;
            setVisible((current) => [...current, bubble.id]);
            const next = SCRIPT[index + 1];
            setTypingFor(next ? next.role : null);
          }, elapsed),
        );
      });
      // restart after a pause
      timeouts.push(
        setTimeout(() => {
          if (!cancelled) play();
        }, TOTAL_TIME),
      );
    }
    play();
    return () => {
      cancelled = true;
      timeouts.forEach(clearTimeout);
    };
  }, []);

  return (
    <div className="rounded-3xl border border-white/15 bg-white/95 p-3 text-ink-900 shadow-2xl">
      <div className="flex items-center justify-between border-b border-ink-100 px-2 pb-2">
        <div className="flex items-center gap-2">
          <span className="grid h-7 w-7 place-items-center rounded-xl bg-gradient-navy text-white">
            <Bot className="h-3.5 w-3.5" />
          </span>
          <div>
            <p className="text-xs font-semibold tracking-tight text-ink-900">Airport Assistant</p>
            <p className="flex items-center gap-1 text-[10px] text-success-600">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-success-500" />
              Online · live demo
            </p>
          </div>
        </div>
        <span className="rounded-full bg-gold-50 px-2 py-0.5 text-[10px] font-semibold text-gold-700">EN</span>
      </div>

      <div className="mt-3 flex h-72 flex-col gap-2 overflow-hidden px-1">
        {SCRIPT.map((bubble) => {
          if (!visible.includes(bubble.id)) return null;
          const isUser = bubble.role === "passenger";
          return (
            <div key={bubble.id} className={`flex animate-message-in items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
              {!isUser ? (
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-navy-100 text-navy-700">
                  <Bot className="h-3 w-3" />
                </span>
              ) : null}
              <div
                className={`max-w-[78%] rounded-2xl px-3 py-2 text-xs leading-snug shadow-card ${
                  isUser
                    ? "bg-gradient-navy text-white"
                    : "bg-ink-50 text-ink-800 ring-1 ring-ink-200/60"
                }`}
              >
                {bubble.text}
              </div>
              {isUser ? (
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-gold-100 text-gold-800">
                  <UserCircle2 className="h-3 w-3" />
                </span>
              ) : null}
            </div>
          );
        })}

        {typingFor && visible.length < SCRIPT.length ? (
          <div className={`flex items-end gap-2 ${typingFor === "passenger" ? "justify-end" : "justify-start"}`}>
            {typingFor === "assistant" ? (
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-navy-100 text-navy-700">
                <Bot className="h-3 w-3" />
              </span>
            ) : null}
            <div
              className={`flex items-center gap-1 rounded-2xl px-3 py-2 ${
                typingFor === "passenger" ? "bg-navy-100" : "bg-ink-50 ring-1 ring-ink-200/60"
              }`}
            >
              <Dot delay="0s" />
              <Dot delay="0.2s" />
              <Dot delay="0.4s" />
            </div>
            {typingFor === "passenger" ? (
              <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-gold-100 text-gold-800">
                <UserCircle2 className="h-3 w-3" />
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-1.5 w-1.5 rounded-full bg-ink-400 animate-typing-bubble"
      style={{ animationDelay: delay }}
    />
  );
}
