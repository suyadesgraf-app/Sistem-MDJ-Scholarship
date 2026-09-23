import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Loader2, Search, ShieldCheck, Trash2, X } from "lucide-react";
import api from "@/lib/api";

const DEMO_STUDENT_EMAIL = process.env.REACT_APP_DEMO_STUDENT_EMAIL;

export default function ParticipantDeletionDialog({ participant, onClose, onDeleted }) {
  const [scope, setScope] = useState(participant ? "single" : "campus");
  const [campus, setCampus] = useState("");
  const [campuses, setCampuses] = useState([]);
  const [participantQuery, setParticipantQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedParticipant, setSelectedParticipant] = useState(participant || null);
  const [searchingParticipants, setSearchingParticipants] = useState(false);
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const selectedUserId = participant?.user_id || selectedParticipant?.user_id;

  useEffect(() => {
    if (!participant) {
      api.get("/campuses")
        .then((response) => setCampuses(response.data || []))
        .catch(() => setCampuses([]));
    }
  }, [participant]);

  useEffect(() => {
    if (participant || scope !== "single" || participantQuery.trim().length < 2) {
      setSearchResults([]);
      return undefined;
    }
    const timeoutId = window.setTimeout(() => {
      setSearchingParticipants(true);
      api.get("/admin/participants", { params: { search: participantQuery.trim() } })
        .then((response) => setSearchResults(response.data || []))
        .catch(() => {
          setSearchResults([]);
          toast.error("Pencarian pendaftar tidak dapat dimuat.");
        })
        .finally(() => setSearchingParticipants(false));
    }, 300);
    return () => window.clearTimeout(timeoutId);
  }, [participant, participantQuery, scope]);

  useEffect(() => {
    const payload = {
      scope,
      user_id: selectedUserId,
      campus,
    };
    if (scope === "campus" && !campus) {
      setPreview(null);
      return;
    }
    if (scope === "single" && !selectedUserId) {
      setPreview(null);
      return;
    }
    setLoadingPreview(true);
    api.post("/admin/participants/delete-preview", payload)
      .then((response) => setPreview(response.data))
      .catch((error) => {
        setPreview(null);
        toast.error(error.response?.data?.detail || "Pratinjau data tidak dapat dimuat.");
      })
      .finally(() => setLoadingPreview(false));
  }, [scope, campus, selectedUserId]);

  const deleteParticipants = async () => {
    if (!preview?.count) return;
    setDeleting(true);
    try {
      const response = await api.delete("/admin/participants", {
        data: {
          scope,
          user_id: selectedUserId,
          campus,
          confirmed: true,
        },
      });
      toast.success(`${response.data.deleted_count} pendaftar dihapus permanen.`);
      onDeleted();
      onClose();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Penghapusan data pendaftar gagal.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F2937]/50 p-4"
      data-testid="participant-deletion-dialog"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-xl bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b px-6 py-5">
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-[#DC2626]">
              Tindakan Permanen
            </p>
            <h2 className="mt-1 font-display text-xl font-extrabold text-[#1F2937]">
              Hapus Data Pendaftar
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            data-testid="close-participant-deletion-dialog"
            className="rounded-lg p-2 text-[#6B7280] transition-colors hover:bg-gray-100"
            aria-label="Tutup hapus pendaftar"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-5 p-6">
          {!participant && (
            <div className="space-y-3" data-testid="participant-deletion-scope">
              <label
                className={[
                  "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm",
                  "font-semibold",
                ].join(" ")}
              >
                <input
                  type="radio"
                  value="single"
                  checked={scope === "single"}
                  onChange={(event) => setScope(event.target.value)}
                  data-testid="participant-delete-scope-single"
                  className="accent-[#DC2626]"
                />
                Hapus satu pendaftar berdasarkan pencarian
              </label>
              <label
                className={[
                  "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm",
                  "font-semibold",
                ].join(" ")}
              >
                <input
                  type="radio"
                  value="campus"
                  checked={scope === "campus"}
                  onChange={(event) => setScope(event.target.value)}
                  data-testid="participant-delete-scope-campus"
                  className="accent-[#DC2626]"
                />
                Hapus semua pendaftar dari satu kampus
              </label>
              <label
                className={[
                  "flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm",
                  "font-semibold",
                ].join(" ")}
              >
                <input
                  type="radio"
                  value="all"
                  checked={scope === "all"}
                  onChange={(event) => setScope(event.target.value)}
                  data-testid="participant-delete-scope-all"
                  className="accent-[#DC2626]"
                />
                Hapus semua pendaftar dari seluruh kampus
              </label>
              {scope === "campus" && (
                <select
                  value={campus}
                  onChange={(event) => setCampus(event.target.value)}
                  data-testid="participant-delete-campus-select"
                  className={[
                    "w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm",
                    "outline-none focus:border-[#DC2626]",
                  ].join(" ")}
                >
                  <option value="">Pilih kampus...</option>
                  {campuses.map((item) => (
                    <option key={item.id} value={item.name}>{item.name}</option>
                  ))}
                </select>
              )}
              {scope === "single" && (
                <div className="space-y-3" data-testid="participant-delete-search-panel">
                  <label className="block text-xs font-bold uppercase tracking-wide text-[#6B7280]">
                    Cari nama, email, atau kampus
                    <div className="relative mt-1.5">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9CA3AF]" />
                      <input
                        value={participantQuery}
                        onChange={(event) => setParticipantQuery(event.target.value)}
                        data-testid="participant-delete-search-input"
                        placeholder="Ketik minimal 2 karakter..."
                        className="w-full rounded-lg border border-gray-300 py-2.5 pl-10 pr-3 text-sm outline-none focus:border-[#DC2626]"
                      />
                    </div>
                  </label>
                  {selectedParticipant && (
                    <div
                      data-testid="selected-participant-delete-target"
                      className="flex items-start justify-between gap-3 border border-[#FECACA] bg-[#FEF2F2] p-3"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-[#991B1B]">{selectedParticipant.name}</p>
                        <p className="truncate text-xs text-[#991B1B]">
                          {selectedParticipant.email} · {selectedParticipant.institusi || "-"}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedParticipant(null)}
                        data-testid="clear-delete-participant-selection"
                        aria-label="Ganti peserta yang dipilih"
                        className="shrink-0 rounded-lg p-1.5 text-[#991B1B] transition-colors hover:bg-[#FECACA]"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  )}
                  {searchingParticipants && (
                    <p className="flex items-center gap-2 text-xs text-[#6B7280]" data-testid="participant-delete-search-loading">
                      <Loader2 className="h-4 w-4 animate-spin" /> Mencari pendaftar...
                    </p>
                  )}
                  {!searchingParticipants && participantQuery.trim().length >= 2 && (
                    <div className="max-h-44 space-y-1 overflow-y-auto rounded-lg border border-gray-200 p-1" data-testid="participant-delete-search-results">
                      {searchResults.length ? searchResults.map((item) => {
                        const isDemoAccount = (
                          item.email?.toLowerCase() === DEMO_STUDENT_EMAIL?.toLowerCase()
                        );
                        return (
                          <button
                            key={item.user_id}
                            type="button"
                            disabled={isDemoAccount}
                            onClick={() => setSelectedParticipant(item)}
                            data-testid={`participant-delete-search-result-${item.user_id}`}
                            className={[
                              "flex w-full items-center justify-between gap-3 p-3 text-left",
                              "transition-colors hover:bg-[#F9FAFB] disabled:cursor-not-allowed",
                              "disabled:bg-[#F9FAFB] disabled:opacity-60",
                            ].join(" ")}
                          >
                            <span className="min-w-0">
                              <span className="block truncate text-sm font-bold text-[#1F2937]">{item.name}</span>
                              <span className="block truncate text-xs text-[#6B7280]">
                                {item.email} · {item.institusi || "-"}
                              </span>
                            </span>
                            {isDemoAccount ? (
                              <span className="inline-flex items-center gap-1 text-xs font-bold text-[#92400E]" data-testid={`protected-demo-search-result-${item.user_id}`}>
                                <ShieldCheck className="h-3.5 w-3.5" /> Akun Demo
                              </span>
                            ) : (
                              <span className="text-xs font-bold text-[#0B6B3A]">Pilih</span>
                            )}
                          </button>
                        );
                      }) : (
                        <p className="p-3 text-center text-xs text-[#6B7280]" data-testid="participant-delete-search-empty">
                          Tidak ada pendaftar yang cocok.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {participant && (
            <p
              className="rounded-lg border border-gray-100 bg-[#F9FAFB] p-4 text-sm text-[#374151]"
            >
              Pendaftar yang dihapus: <strong>{participant.name}</strong>
            </p>
          )}

          <div className="border-l-4 border-[#DC2626] bg-[#FEF2F2] p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-[#DC2626]" />
              <div>
                <p className="text-sm font-bold text-[#991B1B]">
                  {loadingPreview
                    ? "Menghitung data terkait..."
                    : preview?.label || "Pilih cakupan penghapusan."}
                </p>
                <p className="mt-1 text-xs leading-relaxed text-[#991B1B]">
                  Akun, profil, pendaftaran, dokumen, notifikasi, riwayat chat, dan riwayat terkait
                  akan dihapus permanen dan tidak dapat dipulihkan.
                </p>
              </div>
            </div>
          </div>

          {preview?.participants?.length > 0 && (
            <ul className="max-h-32 space-y-1 overflow-y-auto text-xs text-[#4B5563]">
              {preview.participants.map((item) => (
                <li key={item.user_id}>• {item.name} — {item.email}</li>
              ))}
              {preview.count > preview.participants.length && (
                <li>• dan {preview.count - preview.participants.length} pendaftar lainnya</li>
              )}
            </ul>
          )}
        </div>

        <div className="flex justify-end border-t bg-[#F9FAFB] px-6 py-4">
          <button
            type="button"
            onClick={deleteParticipants}
            disabled={deleting || !preview?.count}
            data-testid="confirm-permanent-participant-deletion"
            className={[
              "inline-flex items-center gap-2 rounded-lg bg-[#DC2626] px-5 py-3 text-sm",
              "font-bold text-white transition-colors hover:bg-[#B91C1C]",
              "disabled:cursor-not-allowed disabled:opacity-60",
            ].join(" ")}
          >
            {deleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="h-4 w-4" />
            )}
            Hapus Permanen
          </button>
        </div>
      </div>
    </div>
  );
}