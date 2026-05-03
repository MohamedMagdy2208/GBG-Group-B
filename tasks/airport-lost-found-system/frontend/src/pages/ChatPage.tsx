import { FormEvent, useEffect, useMemo, useState } from "react";
import { Mic, Send, Volume2, VolumeX } from "lucide-react";
import { api } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import type { ChatMessage, ChatSession } from "../types";

type Language = "en" | "ar";

export function ChatPage() {
  const [language, setLanguage] = useState<Language>("en");
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageText, setMessageText] = useState("");
  const [voicePreview, setVoicePreview] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speakerEnabled, setSpeakerEnabled] = useState(true);
  const [voiceProvider, setVoiceProvider] = useState("browser");

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
    const endpoint = voice ? `/chat/sessions/${session.id}/voice-message` : `/chat/sessions/${session.id}/messages`;
    const payload = voice ? { transcript: text, language, provider: voiceProvider } : { message_text: text, language };
    const response = await api.post(endpoint, payload);
    setSession(response.data.session);
    await refreshMessages(response.data.session);
    if (speakerEnabled) speak(response.data.assistant_message.message_text);
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
    const response = await api.post(`/chat/sessions/${session.id}/submit-lost-report`, {});
    const assistantText =
      language === "ar" ? `Report created. Keep this code: ${response.data.report_code}` : `Report created: ${response.data.report_code}`;
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
    if (speakerEnabled) speak(assistantText);
  }

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
    <section className="max-w-4xl" dir={language === "ar" ? "rtl" : "ltr"}>
      <PageHeader title={copy.title} kicker={copy.kicker} />
      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div className="h-[520px] space-y-3 overflow-y-auto p-4">
            {messages.map((message) => (
              <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[78%] rounded-lg px-3 py-2 text-sm ${message.role === "user" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-800"}`}>
                  {message.message_text}
                </div>
              </div>
            ))}
          </div>
          {voicePreview ? <div className="border-t border-slate-100 px-4 py-2 text-xs font-medium text-radar">{voicePreview}</div> : null}
          <form onSubmit={send} className="flex gap-2 border-t border-slate-200 p-3">
            <button
              type="button"
              onClick={startVoice}
              className={`focus-ring grid h-10 w-10 place-items-center rounded-lg border ${isListening ? "border-radar bg-radar text-white" : "border-slate-200 text-slate-600"}`}
              title={copy.mic}
            >
              <Mic className="h-4 w-4" />
            </button>
            <input className="focus-ring flex-1 rounded-lg border border-slate-200 px-3 py-2" value={messageText} onChange={(event) => setMessageText(event.target.value)} placeholder={copy.placeholder} />
            <button className="focus-ring grid h-10 w-10 place-items-center rounded-lg bg-slate-900 text-white" title="Send">
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
        <aside className="space-y-3">
          <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-sm font-semibold text-slate-950">{copy.session}</p>
            <p className="mt-1 text-xs text-slate-500">{session?.session_code ?? "Starting..."}</p>
            <p className="mt-3 text-xs font-semibold uppercase tracking-normal text-radar">{session?.current_state ?? "loading"}</p>
            <p className="mt-2 text-xs text-slate-500">Voice provider: {voiceProvider}</p>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => setLanguage("en")} className={`rounded-lg border px-3 py-2 text-sm font-semibold ${language === "en" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"}`}>English</button>
            <button onClick={() => setLanguage("ar")} className={`rounded-lg border px-3 py-2 text-sm font-semibold ${language === "ar" ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"}`}>Arabic</button>
          </div>
          <button onClick={() => setSpeakerEnabled((value) => !value)} className="focus-ring flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-700">
            {speakerEnabled ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
            {speakerEnabled ? copy.speaking : copy.muted}
          </button>
          <button onClick={submitReport} className="focus-ring w-full rounded-lg bg-radar px-4 py-2 text-sm font-semibold text-white">
            {copy.submit}
          </button>
        </aside>
      </div>
    </section>
  );
}
