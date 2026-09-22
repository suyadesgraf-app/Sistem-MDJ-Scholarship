import React, { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Loader2, MessageCircleMore, Mic, Paperclip, RefreshCw, Send, Square } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";
import { AdminStudentLiveChat } from "@/components/StudentLiveChat";

const ADMIN_TEAM_SESSION_ID = "admin-team";

function formatMessageTime(value) {
  if (!value) {
    return "Baru saja";
  }

  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function LiveChat() {
  const [channel, setChannel] = useState("team");
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [attachment, setAttachment] = useState(null);
  const [recording, setRecording] = useState(false);
  const [recordingLocked, setRecordingLocked] = useState(false);
  const messageListRef = useRef(null);
  const fileInputRef = useRef(null);
  const recorderRef = useRef(null);
  const audioPartsRef = useRef([]);
  const recordStartYRef = useRef(0);

  const loadMessages = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
    }

    try {
      const response = await api.get("/admin/live-chat/messages", {
        params: { session_id: ADMIN_TEAM_SESSION_ID },
      });
      setMessages(response.data.messages || []);
    } catch (error) {
      if (!silent) {
        toast.error(error.response?.data?.detail || "Pesan Live Chat belum dapat dimuat.");
      }
    } finally {
      if (!silent) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    loadMessages();
    const intervalId = window.setInterval(() => loadMessages({ silent: true }), 15000);
    return () => window.clearInterval(intervalId);
  }, [loadMessages]);

  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (event) => {
    event.preventDefault();
    const trimmedMessage = message.trim();
    if ((!trimmedMessage && !attachment) || sending) {
      return;
    }

    setSending(true);
    try {
      const response = attachment
        ? await api.post("/admin/live-chat/messages/attachment", (() => {
          const formData = new FormData();
          formData.append("message", trimmedMessage);
          formData.append("attachment", attachment);
          return formData;
        })(), { headers: { "Content-Type": "multipart/form-data" } })
        : await api.post("/admin/live-chat/messages", { session_id: ADMIN_TEAM_SESSION_ID, message: trimmedMessage });
      setMessages((previous) => [...previous, response.data.message]);
      setMessage("");
      setAttachment(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (error) {
      toast.error(error.response?.data?.detail || "Pesan belum berhasil dikirim.");
    } finally {
      setSending(false);
    }
  };

  const sendVoiceNote = async (file) => {
    setSending(true);
    try {
      const formData = new FormData();
      formData.append("message", "");
      formData.append("attachment", file);
      const response = await api.post("/admin/live-chat/messages/attachment", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setMessages((previous) => [...previous, response.data.message]);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Voice note belum berhasil dikirim.");
    } finally {
      setSending(false);
    }
  };

  const startPressRecording = async (event) => {
    if (sending || recording) return;
    try {
      recordStartYRef.current = event.clientY;
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioPartsRef.current = [];
      recorder.ondataavailable = (item) => audioPartsRef.current.push(item.data);
      recorder.onstop = () => {
        const blob = new Blob(audioPartsRef.current, { type: recorder.mimeType || "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        setRecording(false);
        setRecordingLocked(false);
        if (blob.size) sendVoiceNote(new File([blob], `voice-note-${Date.now()}.webm`, { type: blob.type }));
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
    } catch {
      toast.error("Izin mikrofon diperlukan untuk merekam voice note.");
    }
  };

  const movePressRecording = (event) => {
    if (recording && !recordingLocked && recordStartYRef.current - event.clientY > 48) {
      setRecordingLocked(true);
    }
  };

  const endPressRecording = () => {
    if (recording && !recordingLocked) recorderRef.current?.stop();
  };

  const stopLockedRecording = () => {
    if (recording && recordingLocked) recorderRef.current?.stop();
  };

  return (
    <section className="space-y-6" data-testid="live-chat-manager">
      <div className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">
              Koordinasi Internal
            </p>
            <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">
              {channel === "team" ? "Live Chat Tim Admin" : "Live Chat Mahasiswa"}
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#4B5563]">
              {channel === "team"
                ? "Ruang percakapan bersama untuk koordinasi operasional MDJ Scholarship."
                : "Baca dan balas pesan mahasiswa sesuai cakupan akses Anda."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadMessages()}
            disabled={loading}
            data-testid="live-chat-refresh-button"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#B7E4C7] bg-white px-4 py-2.5 text-sm font-bold text-[#0B6B3A] transition-colors hover:bg-[#E8F6EE] disabled:cursor-not-allowed disabled:opacity-60"
          >
            <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            Muat Ulang
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" data-testid="live-chat-channel-tabs">
        <button
          type="button"
          onClick={() => setChannel("team")}
          data-testid="live-chat-team-tab"
          className={channel === "team" ? "bg-[#0B6B3A] px-4 py-2 text-sm font-bold text-white" : "border border-gray-200 bg-white px-4 py-2 text-sm font-bold text-[#4B5563]"}
        >
          Tim Admin
        </button>
        <button
          type="button"
          onClick={() => setChannel("students")}
          data-testid="live-chat-students-tab"
          className={channel === "students" ? "bg-[#0B6B3A] px-4 py-2 text-sm font-bold text-white" : "border border-gray-200 bg-white px-4 py-2 text-sm font-bold text-[#4B5563]"}
        >
          Pesan Mahasiswa
        </button>
      </div>

      {channel === "students" ? <AdminStudentLiveChat /> : <div className="border border-gray-200 bg-white shadow-sm">
        <div
          ref={messageListRef}
          data-testid="live-chat-message-list"
          className="max-h-[440px] min-h-[260px] space-y-4 overflow-y-auto p-5 mdj-scrollbar"
        >
          {loading ? (
            <div className="flex min-h-[220px] items-center justify-center" data-testid="live-chat-loading">
              <Loader2 className="h-6 w-6 animate-spin text-[#27AE60]" />
            </div>
          ) : messages.length === 0 ? (
            <div
              className="flex min-h-[220px] flex-col items-center justify-center text-center"
              data-testid="live-chat-empty-state"
            >
              <MessageCircleMore className="h-9 w-9 text-[#9CA3AF]" />
              <p className="mt-3 text-sm font-bold text-[#4B5563]">Belum ada pesan</p>
              <p className="mt-1 text-sm text-[#6B7280]">Mulai koordinasi dengan tim admin.</p>
            </div>
          ) : (
            messages.map((item) => (
              <article
                key={item.id}
                data-testid={`live-chat-message-${item.id}`}
                className="border-l-2 border-[#B7E4C7] bg-[#F9FAFB] px-4 py-3"
              >
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <p className="text-sm font-extrabold text-[#1F2937]">{item.sender_name}</p>
                  <time
                    className="text-xs font-medium text-[#6B7280]"
                    data-testid={`live-chat-message-time-${item.id}`}
                  >
                    {formatMessageTime(item.created_at)}
                  </time>
                </div>
                <p
                  className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-[#374151]"
                  data-testid={`live-chat-message-content-${item.id}`}
                >
                  {item.message}
                </p>
                {item.attachment && (
                  item.attachment.content_type?.startsWith("audio/") ? (
                    <audio controls className="mt-3 w-full" data-testid={`live-chat-audio-${item.attachment.id}`}>
                      <source src={`${process.env.REACT_APP_BACKEND_URL}/api/admin/live-chat/attachments/${item.attachment.id}?auth=${encodeURIComponent(localStorage.getItem("mdj_token") || "")}`} type={item.attachment.content_type} />
                    </audio>
                  ) : (
                    <a href={`${process.env.REACT_APP_BACKEND_URL}/api/admin/live-chat/attachments/${item.attachment.id}?auth=${encodeURIComponent(localStorage.getItem("mdj_token") || "")}`} target="_blank" rel="noreferrer" data-testid={`live-chat-attachment-${item.attachment.id}`} className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-[#0B6B3A]"><FileText className="h-4 w-4" />{item.attachment.original_filename}</a>
                  )
                )}
              </article>
            ))
          )}
        </div>

        <form
          onSubmit={sendMessage}
          className="border-t border-gray-200 p-4"
          data-testid="live-chat-send-form"
        >
          <label className="sr-only" htmlFor="live-chat-message-input">
            Tulis pesan untuk tim admin
          </label>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <textarea
              id="live-chat-message-input"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              maxLength={2000}
              rows={3}
              placeholder="Tulis pesan untuk tim admin..."
              data-testid="live-chat-message-input"
              className="min-h-[84px] flex-1 resize-y rounded-lg border border-gray-200 bg-white px-3 py-2.5 text-sm text-[#1F2937] outline-none transition-colors placeholder:text-[#9CA3AF] focus:border-[#27AE60] focus:ring-2 focus:ring-[#E8F6EE]"
            />
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <label title="Lampirkan dokumen" aria-label="Lampirkan dokumen" className="inline-flex h-11 w-11 cursor-pointer items-center justify-center rounded-full border border-[#B7E4C7] text-[#0B6B3A] transition-colors hover:bg-[#E8F6EE]" data-testid="live-chat-attachment-label"><Paperclip className="h-5 w-5" /><input ref={fileInputRef} type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp,.mp3,.wav,.ogg,.webm,.m4a" className="sr-only" data-testid="live-chat-attachment-input" onChange={(event) => setAttachment(event.target.files?.[0] || null)} /></label>
              <button type="button" onPointerDown={startPressRecording} onPointerMove={movePressRecording} onPointerUp={endPressRecording} onPointerCancel={endPressRecording} onClick={stopLockedRecording} data-testid="live-chat-record-button" className={`inline-flex h-11 w-11 items-center justify-center rounded-full text-white ${recording ? "bg-[#DC2626]" : "bg-[#0B6B3A]"}`} aria-label={recordingLocked ? "Kirim voice note" : "Tahan untuk rekam voice note"}>{recordingLocked ? <Square className="h-4 w-4" /> : <Mic className="h-5 w-5" />}</button>
              {recording && <span className="text-xs font-bold text-[#DC2626]" data-testid="live-chat-recording-status">{recordingLocked ? "Rekaman dikunci — tekan tombol untuk kirim" : "Merekam — lepas untuk kirim atau geser ke atas untuk kunci"}</span>}
              {attachment && <span className="max-w-full truncate text-xs text-[#4B5563]" data-testid="live-chat-selected-file">{attachment.name}</span>}
            </div>
            <button
              type="submit"
              disabled={(!message.trim() && !attachment) || sending}
              data-testid="live-chat-send-button"
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#0B6B3A] px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-[#07532D] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Kirim Pesan
            </button>
          </div>
        </form>
      </div>}
    </section>
  );
}