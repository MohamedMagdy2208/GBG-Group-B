import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { Loader2, Mic, Send, Volume2, VolumeX } from "lucide-react";
import { api } from "../api/client";
import { Button, Card, Section } from "../components/ui";
import { Pill } from "../components/ui/Pill";
import { SegmentedControl } from "../components/ui/SegmentedControl";
import { useToast } from "../components/Toast";
import type { ChatMessage, ChatSession } from "../types";

type Language = "en" | "ar";

function describeError(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (error.message) return error.message;
  }
  return fallback;
}

export function ChatPage() {
  const toast = useToast();
  const [language, setLanguage] = useState<Language>("en");
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageText, setMessageText] = useState("");
  const [voicePreview, setVoicePreview] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speakerEnabled, setSpeakerEnabled] = useState(true);
  const [voiceProvider, setVoiceProvider] = useState("browser");
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  const copy = useMemo(
    () =>
      language === "ar"
        ? {
            title: "Passenger Chat Assistant",
            kicker: "Arabic voice-ready guided intake",
            placeholder: "Type your message",
            submit: "Submit collected report",
            session: "Session",
            mic: "Start voice input",
            speaking: "Spoken replies enabled",
            muted: "Spoken replies disabled",
          }
        : {
            title: "Passenger Chat Assistant",
            kicker: "Guided intake with voice",
            placeholder: "Type your message",
            submit: "Submit collected report",
            session: "Session",
            mic: "Start voice input",
            speaking: "Spoken replies enabled",
            muted: "Spoken replies disabled",
          },
    [language],
  );

  useEffect(() => {
    api.post("/voice/token").then((response) => setVoiceProvider(response.data.provider ?? "browser")).catch(() => setVoiceProvider("browser"));
  }, []);

  useEffect(() => {
    api.post<ChatSession>("/chat/sessions", { language, voice_enabled: true }).then(async (response) => {
      setSession(response.data);
      const messagesResponse = await api.get<ChatMessage[]>(`/chat/sessions/${response.data.id}/messages`);
      setMessages(messagesResponse.data);
    });
  }, [language]);

  async function refreshMessages(targetSession = session) {
    if (!targetSession) return;
    const messagesResponse = await api.get<ChatMessage[]>(`/chat/sessions/${targetSession.id}/messages`);
    setMessages(messagesResponse.data);
  }

  async function sendText(text: string, voice = false) {
    if (!session || !text.trim()) return;
    setSending(true);
    try {
      const endpoint = voice ? `/chat/sessions/${session.id}/voice-message` : `/chat/sessions/${session.id}/messages`;
      const payload = voice ? { transcript: text, language, provider: voiceProvider } : { message_text: text, language };
      const response = await api.post(endpoint, payload);
      setSession(response.data.session);
      await refreshMessages(response.data.session);
      if (speakerEnabled) speak(response.data.assistant_message.message_text);
    } catch (error) {
      toast.push(describeError(error, "Could not send message."), "error");
    } finally {
      setSending(false);
    }
  }

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = messageText;
    setMessageText("");
    setVoicePreview("");
    await sendText(text);
  }

  async function submitReport() {
    if (!session) return;
    setSubmitting(true);
    try {
      const response = await api.post(`/chat/sessions/${session.id}/submit-lost-report`, {});
      const assistantText =
        language === "ar"
          ? `تم إنشاء البلاغ. احتفظ بهذا الرقم: ${response.data.report_code}`
          : `Report created: ${response.data.report_code}`;
      setMessages((current) => [
        ...current,
        {
          id: Date.now(),
          session_id: session.id,
          role: "assistant",
          message_text: assistantText,
          structured_payload_json: {},
          created_at: new Date().toISOString(),
        },
      ]);
      toast.push(`Report ${response.data.report_code} submitted.`, "success");
      if (speakerEnabled) speak(assistantText);
    } catch (error) {
      toast.push(describeError(error, "Could not submit report. Make sure you've described the item, location, and contact info."), "error");
    } finally {
      setSubmitting(false);
    }
  }

  // Auto-scroll to newest message
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  function startVoice() {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoicePreview("Voice input is not available in this browser. Typed chat still works.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = language === "ar" ? "ar-EG" : "en-US";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onstart = () => setIsListening(true);
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results)
        .map((result: any) => result[0]?.transcript ?? "")
        .join(" ")
        .trim();
      setVoicePreview(transcript);
      setMessageText(transcript);
      if (event.results[event.results.length - 1]?.isFinal) {
        setVoicePreview("");
        setMessageText("");
        void sendText(transcript, true);
      }
    };
    recognition.start();
  }

  function speak(text: string) {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language === "ar" ? "ar-EG" : "en-US";
    window.speechSynthesis.speak(utterance);
  }

  return (
    <Section kicker={copy.kicker} title={copy.title}>
      <div className="grid gap-4 lg:grid-cols-[1fr_300px]" dir={language === "ar" ? "rtl" : "ltr"}>
        <Card className="overflow-hidden p-0" padded={false}>
          <div ref={scrollRef} className="h-[520px] space-y-3 overflow-y-auto bg-ink-50/40 p-5">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-ink-400">Starting session…</div>
            ) : null}
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-card ${
                    message.role === "user"
                      ? "bg-gradient-navy text-white"
                      : "bg-white text-ink-800 ring-1 ring-ink-200/60"
                  }`}
                >
                  {message.message_text}
                </div>
              </div>
            ))}
            {sending ? (
              <div className="flex justify-start">
                <div className="inline-flex items-center gap-2 rounded-2xl bg-white px-3 py-2 text-sm text-ink-500 ring-1 ring-ink-200/60">
                  <Loader2 size={14} className="animate-spin" />
                  Assistant is typing…
                </div>
              </div>
            ) : null}
          </div>
          {voicePreview ? (
            <div className="border-t border-ink-200/60 bg-gold-50/60 px-5 py-2 text-xs font-medium text-gold-800">{voicePreview}</div>
          ) : null}
          <form onSubmit={send} className="flex items-center gap-2 border-t border-ink-200/60 bg-white p-3">
            <button
              type="button"
              onClick={startVoice}
              className={`focus-ring grid h-10 w-10 place-items-center rounded-2xl transition ${
                isListening ? "bg-gradient-gold text-navy-950 shadow-gold" : "border border-ink-200 bg-white text-ink-600 hover:bg-ink-50"
              }`}
              title={copy.mic}
              aria-label={copy.mic}
            >
              <Mic className="h-4 w-4" />
            </button>
            <input
              className="focus-ring flex-1 rounded-2xl border border-ink-200 bg-white px-4 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 focus:border-navy-500 focus:outline-none focus:ring-4 focus:ring-navy-500/10"
              value={messageText}
              onChange={(event) => setMessageText(event.target.value)}
              placeholder={copy.placeholder}
              disabled={sending}
              aria-label={copy.placeholder}
            />
            <button
              type="submit"
              disabled={sending || !messageText.trim()}
              className="focus-ring grid h-10 w-10 place-items-center rounded-2xl bg-gradient-navy text-white shadow-navy disabled:opacity-50"
              title="Send"
              aria-label="Send"
            >
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </form>
        </Card>

        <aside className="space-y-3">
          <Card>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-700">{copy.session}</p>
            <p className="mt-1 font-mono text-xs text-ink-500">{session?.session_code ?? "Starting…"}</p>
            <Pill tone="navy" withDot className="mt-3">
              {session?.current_state ?? "loading"}
            </Pill>
            <p className="mt-3 text-xs text-ink-500">Voice provider: <span className="font-medium text-ink-700">{voiceProvider}</span></p>
          </Card>
          <SegmentedControl
            value={language}
            onChange={setLanguage}
            fullWidth
            options={[
              { value: "en", label: "English" },
              { value: "ar", label: "العربية" },
            ]}
          />
          <Button
            variant="outline"
            fullWidth
            onClick={() => setSpeakerEnabled((value) => !value)}
            leftIcon={speakerEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
          >
            {speakerEnabled ? copy.speaking : copy.muted}
          </Button>
          <Button
            variant="gold"
            fullWidth
            loading={submitting}
            disabled={!session}
            onClick={submitReport}
          >
            {copy.submit}
          </Button>
        </aside>
      </div>
    </Section>
  );
}
