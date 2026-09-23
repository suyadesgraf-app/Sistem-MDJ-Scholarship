import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { AlertTriangle, Loader2, Trash2, X } from "lucide-react";
import api from "@/lib/api";

export default function ParticipantDeletionDialog({ participant, onClose, onDeleted }) {
  const [scope, setScope] = useState(participant ? "single" : "campus");
  const [campus, setCampus] = useState("");
  const [campuses, setCampuses] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!participant) {
      api.get("/campuses")
        .then((response) => setCampuses(response.data || []))
        .catch(() => setCampuses([]));
    }
  }, [participant]);

  useEffect(() => {
    const payload = {
      scope,
      user_id: participant?.user_id,
      campus,
    };
    if (scope === "campus" && !campus) {
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
  }, [scope, campus, participant]);

  const deleteParticipants = async () => {
    if (!preview?.count) return;
    setDeleting(true);
    try {
      const response = await api.delete("/admin/participants", {
        data: {
          scope,
          user_id: participant?.user_id,
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
        className="w-full max-w-xl rounded-xl bg-white shadow-2xl"
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