import React, { useCallback, useEffect, useRef, useState } from "react";
import { FileText, Image, Loader2, Paperclip, Send } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const ACCEPTED_FILES = ".jpg,.jpeg,.png,.webp,.pdf";

function attachmentUrl(attachment) {
  const token = localStorage.getItem("mdj_token");
  const baseUrl = process.env.REACT_APP_BACKEND_URL;
  const authQuery = token ? `?auth=${encodeURIComponent(token)}` : "";
  return `${baseUrl}/api/student-live-chat/attachments/${attachment.id}${authQuery}`;
}

function formatMessageTime(value) {
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function ChatAttachment({ attachment }) {
  if (!attachment) {
    return null;
  }

  const url = attachmentUrl(attachment);
  const isImage = attachment.content_type?.startsWith("image/");
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      data-testid={`student-chat-attachment-${attachment.id}`}
      className="mt-3 flex max-w-full items-center gap-2 border border-[#B7E4C7] bg-white px-3 py-2 text-sm font-bold text-[#0B6B3A] transition-colors hover:bg-[#E8F6EE]"
    >
      {isImage ? <Image className="h-4 w-4 shrink-0" /> : <FileText className="h-4 w-4 shrink-0" />}
      <span className="truncate">{attachment.original_filename}</span>
    </a>
  );
}

function ChatMessageList({ emptyMessage, loading, messages }) {
  if (loading) {
    return (
      <div className="flex min-h-[260px] items-center justify-center" data-testid="student-chat-loading">
        <Loader2 className="h-6 w-6 animate-spin text-[#27AE60]" />
      </div>
    );
  }

  if (!messages.length) {
    return (
      <div
        className="flex min-h-[260px] items-center justify-center text-center text-sm text-[#6B7280]"
        data-testid="student-chat-empty-state"
      >
        {emptyMessage}
      </div>
    );
  }

  return messages.map((item) => (
    <article
      key={item.id}
      data-testid={`student-chat-message-${item.id}`}
      className={[
        "max-w-[88%] border px-4 py-3",
        item.sender_role === "student"
          ? "ml-auto border-[#B7E4C7] bg-[#F0FBF5]"
          : "border-gray-200 bg-white",
      ].join(" ")}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="text-sm font-extrabold text-[#1F2937]">{item.sender_name}</p>
        <time className="text-xs text-[#6B7280]">{formatMessageTime(item.created_at)}</time>
      </div>
      {item.message && (
        <p
          className="mt-2 whitespace-pre-wrap break-words text-sm leading-relaxed text-[#374151]"
          data-testid={`student-chat-message-content-${item.id}`}
        >
          {item.message}
        </p>
      )}
      <ChatAttachment attachment={item.attachment} />
    </article>
  ));
}

function ChatComposer({ disabled, onSend, studentId }) {
  const [message, setMessage] = useState("");
  const [attachment, setAttachment] = useState(null);
  const [sending, setSending] = useState(false);
  const fileInputRef = useRef(null);

  const submit = async (event) => {
    event.preventDefault();
    const trimmedMessage = message.trim();
    if ((!trimmedMessage && !attachment) || sending || disabled) {
      return;
    }

    const formData = new FormData();
    formData.append("message", trimmedMessage);
    if (studentId) {
      formData.append("student_id", studentId);
    }
    if (attachment) {
      formData.append("attachment", attachment);
    }

    setSending(true);
    try {
      const response = await api.post("/student-live-chat/messages", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onSend(response.data.message);
      setMessage("");
      setAttachment(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Pesan belum berhasil dikirim.");
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={submit} className="border-t border-gray-200 p-4" data-testid="student-chat-send-form">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label className="sr-only" htmlFor="student-chat-message-input">
            Tulis pesan untuk admin
          </label>
          <textarea
            id="student-chat-message-input"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={3}
            maxLength={2000}
            placeholder="Tulis pesan untuk admin..."
            data-testid="student-chat-message-input"
            className="min-h-[84px] w-full resize-y border border-gray-200 bg-white px-3 py-2.5 text-sm text-[#1F2937] outline-none transition-colors focus:border-[#27AE60] focus:ring-2 focus:ring-[#E8F6EE]"
          />
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <label
              htmlFor="student-chat-attachment-input"
              data-testid="student-chat-attachment-label"
              className="inline-flex cursor-pointer items-center gap-2 text-xs font-bold text-[#0B6B3A]"
            >
              <Paperclip className="h-4 w-4" />
              Lampirkan gambar atau PDF
            </label>
            <input
              ref={fileInputRef}
              id="student-chat-attachment-input"
              type="file"
              accept={ACCEPTED_FILES}
              onChange={(event) => setAttachment(event.target.files?.[0] || null)}
              data-testid="student-chat-attachment-input"
              className="sr-only"
            />
            {attachment && (
              <span className="max-w-full truncate text-xs text-[#4B5563]" data-testid="student-chat-selected-file">
                {attachment.name}
              </span>
            )}
          </div>
        </div>
        <button
          type="submit"
          disabled={disabled || (!message.trim() && !attachment) || sending}
          data-testid="student-chat-send-button"
          className="inline-flex min-h-11 items-center justify-center gap-2 bg-[#0B6B3A] px-5 py-3 text-sm font-bold text-white transition-colors hover:bg-[#07532D] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          Kirim Pesan
        </button>
      </div>
    </form>
  );
}

export default function StudentLiveChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadMessages = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
    }
    try {
      const response = await api.get("/student-live-chat/messages");
      setMessages(response.data.messages || []);
    } catch (error) {
      if (!silent) {
        toast.error(error.response?.data?.detail || "Live Chat Admin belum dapat dimuat.");
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

  return (
    <section className="space-y-6" data-testid="student-live-chat-manager">
      <div className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-5">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">Bantuan Pendaftaran</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">Live Chat Admin</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#4B5563]">
          Kirim pertanyaan atau lampiran kepada Admin Provinsi dan Admin Wilayah Anda.
        </p>
      </div>
      <div className="border border-gray-200 bg-white shadow-sm">
        <div className="max-h-[440px] min-h-[260px] space-y-4 overflow-y-auto p-5 mdj-scrollbar" data-testid="student-chat-message-list">
          <ChatMessageList
            emptyMessage="Belum ada percakapan. Kirim pesan untuk memulai bantuan."
            loading={loading}
            messages={messages}
          />
        </div>
        <ChatComposer onSend={(item) => setMessages((previous) => [...previous, item])} />
      </div>
    </section>
  );
}

export function AdminStudentLiveChat() {
  const [conversations, setConversations] = useState([]);
  const [messages, setMessages] = useState([]);
  const [selectedStudentId, setSelectedStudentId] = useState("");
  const [loading, setLoading] = useState(true);

  const loadConversations = useCallback(async () => {
    try {
      const response = await api.get("/student-live-chat/conversations");
      const nextConversations = response.data.conversations || [];
      setConversations(nextConversations);
      setSelectedStudentId((current) => current || nextConversations[0]?.student_id || "");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Percakapan mahasiswa belum dapat dimuat.");
    }
  }, []);

  const loadMessages = useCallback(async (studentId) => {
    if (!studentId) {
      setMessages([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await api.get("/student-live-chat/messages", { params: { student_id: studentId } });
      setMessages(response.data.messages || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Pesan mahasiswa belum dapat dimuat.");
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    loadMessages(selectedStudentId);
  }, [loadMessages, selectedStudentId]);

  const selectedConversation = conversations.find((item) => item.student_id === selectedStudentId);
  return (
    <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]" data-testid="admin-student-chat-inbox">
      <aside className="border border-gray-200 bg-white" data-testid="admin-student-chat-conversation-list">
        <div className="border-b border-gray-200 px-4 py-3">
          <p className="text-sm font-extrabold text-[#1F2937]">Pesan Mahasiswa</p>
        </div>
        <div className="max-h-[520px] divide-y divide-gray-100 overflow-y-auto mdj-scrollbar">
          {conversations.length === 0 ? (
            <p className="p-4 text-sm text-[#6B7280]" data-testid="admin-student-chat-empty-state">
              Belum ada pesan mahasiswa di wilayah Anda.
            </p>
          ) : conversations.map((conversation) => (
            <button
              key={conversation.student_id}
              type="button"
              onClick={() => setSelectedStudentId(conversation.student_id)}
              data-testid={`admin-student-chat-conversation-${conversation.student_id}`}
              className={[
                "w-full px-4 py-3 text-left transition-colors",
                selectedStudentId === conversation.student_id ? "bg-[#F0FBF5]" : "hover:bg-gray-50",
              ].join(" ")}
            >
              <p className="truncate text-sm font-bold text-[#1F2937]">{conversation.student_name}</p>
              <p className="mt-1 truncate text-xs text-[#6B7280]">{conversation.last_message}</p>
              {conversation.region && <p className="mt-1 text-xs font-bold text-[#0B6B3A]">{conversation.region}</p>}
            </button>
          ))}
        </div>
      </aside>
      <section className="border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-5 py-3">
          <p className="text-sm font-extrabold text-[#1F2937]" data-testid="admin-student-chat-title">
            {selectedConversation ? `Chat dengan ${selectedConversation.student_name}` : "Pilih percakapan mahasiswa"}
          </p>
        </div>
        <div className="max-h-[356px] min-h-[260px] space-y-4 overflow-y-auto p-5 mdj-scrollbar" data-testid="admin-student-chat-message-list">
          <ChatMessageList
            emptyMessage="Pilih percakapan dari daftar di samping."
            loading={loading}
            messages={messages}
          />
        </div>
        <ChatComposer
          disabled={!selectedStudentId}
          onSend={(item) => {
            setMessages((previous) => [...previous, item]);
            loadConversations();
          }}
          studentId={selectedStudentId}
        />
      </section>
    </div>
  );
}