import React, { useEffect, useRef, useState } from "react";
import { Bot, GripVertical, Loader2, Send, X } from "lucide-react";
import api from "@/lib/api";

export default function StudentAiChatWidget() {
  const [open, setOpen] = useState(false);
  const [position, setPosition] = useState({ left: 20, bottom: 20 });
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [sending, setSending] = useState(false);
  const dragRef = useRef(null);

  useEffect(() => {
    api.get("/student/ai-chat/messages").then((response) => setMessages(response.data.messages || [])).catch(() => {});
  }, []);

  useEffect(() => {
    const clampPosition = () => setPosition((current) => ({
      ...current,
      left: Math.max(8, Math.min(current.left, window.innerWidth - 368)),
    }));
    window.addEventListener("resize", clampPosition);
    return () => window.removeEventListener("resize", clampPosition);
  }, []);

  const startDrag = (event) => {
    const startX = event.clientX;
    const startY = event.clientY;
    const start = position;
    const move = (moveEvent) => setPosition({ left: Math.max(8, start.left + moveEvent.clientX - startX), bottom: Math.max(8, start.bottom - moveEvent.clientY + startY) });
    const stop = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", stop); };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", stop);
  };

  const sendQuestion = async (event) => {
    event.preventDefault();
    const text = question.trim();
    if (!text || sending) return;
    setQuestion(""); setSending(true);
    const assistantId = `pending-${Date.now()}`;
    setMessages((previous) => [...previous, { id: `user-${Date.now()}`, role: "user", text }, { id: assistantId, role: "assistant", text: "" }]);
    try {
      const token = localStorage.getItem("mdj_token");
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/student/ai-chat/stream`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify({ question: text }) });
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) { const { done, value } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); const events = buffer.split("\n\n"); buffer = events.pop(); events.forEach((raw) => { const line = raw.split("\n").find((item) => item.startsWith("data: ")); if (!line) return; try { const data = JSON.parse(line.slice(6)); if (data.text) setMessages((previous) => previous.map((item) => item.id === assistantId ? { ...item, text: item.text + data.text } : item)); } catch {} }); }
    } finally { setSending(false); }
  };

  return <div ref={dragRef} style={{ left: position.left, bottom: position.bottom }} className="fixed z-40" data-testid="student-ai-chat-widget">
    {open ? <div className="flex h-[460px] w-[min(360px,calc(100vw-32px))] flex-col border border-[#B7E4C7] bg-white shadow-2xl">
      <div onPointerDown={startDrag} className="flex cursor-grab items-center justify-between bg-[#0B6B3A] px-3 py-3 text-white" data-testid="student-ai-chat-drag-handle"><span className="flex items-center gap-2 text-sm font-bold"><GripVertical className="h-4 w-4" />AI Referensi MDJ</span><button type="button" onClick={() => setOpen(false)} data-testid="student-ai-chat-close-button"><X className="h-4 w-4" /></button></div>
      <div className="flex-1 space-y-3 overflow-y-auto p-3" data-testid="student-ai-chat-messages">{messages.map((item) => <div key={item.id} className={item.role === "user" ? "ml-auto max-w-[85%] bg-[#E8F6EE] p-2 text-sm" : "max-w-[85%] border border-gray-200 p-2 text-sm"}>{item.text || <Loader2 className="h-4 w-4 animate-spin" />}</div>)}</div>
      <form onSubmit={sendQuestion} className="flex gap-2 border-t p-3"><input value={question} onChange={(event) => setQuestion(event.target.value)} data-testid="student-ai-chat-input" placeholder="Tanya dokumen referensi..." className="min-w-0 flex-1 border border-gray-200 px-2 py-2 text-sm" /><button disabled={!question.trim() || sending} data-testid="student-ai-chat-send-button" className="bg-[#0B6B3A] px-3 text-white disabled:opacity-50"><Send className="h-4 w-4" /></button></form>
    </div> : <button type="button" onClick={() => setOpen(true)} data-testid="student-ai-chat-open-button" className="flex h-14 w-14 items-center justify-center rounded-full bg-[#0B6B3A] text-white shadow-lg hover:bg-[#07532D]"><Bot className="h-6 w-6" /></button>}
  </div>;
}