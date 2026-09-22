import React, { useEffect, useState } from "react";
import { FileText, Loader2, Trash2, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const ACCEPTED_REFERENCES = ".pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.mp3,.wav,.ogg,.aac,.flac";

export default function AiReferenceManager() {
  const [references, setReferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const loadReferences = async () => {
    setLoading(true);
    try {
      const response = await api.get("/super-admin/ai-references");
      setReferences(response.data.references || []);
    } catch (error) {
      toast.error(error.response?.data?.detail || "Referensi AI belum dapat dimuat.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadReferences(); }, []);

  const uploadReference = async (file) => {
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    setUploading(true);
    try {
      const response = await api.post("/super-admin/ai-references", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setReferences((previous) => [response.data.reference, ...previous]);
      toast.success("Referensi AI berhasil diindeks.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Referensi AI gagal diproses.");
    } finally {
      setUploading(false);
    }
  };

  const removeReference = async (referenceId) => {
    if (!window.confirm("Hapus referensi ini dari jawaban AI?")) return;
    try {
      await api.delete(`/super-admin/ai-references/${referenceId}`);
      setReferences((previous) => previous.filter((item) => item.id !== referenceId));
      toast.success("Referensi AI dihapus.");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Referensi AI gagal dihapus.");
    }
  };

  return (
    <section className="space-y-6" data-testid="ai-reference-manager">
      <div className="border-l-4 border-[#0B6B3A] bg-[#F0FBF5] px-5 py-5">
        <p className="text-xs font-bold uppercase tracking-wide text-[#0B6B3A]">RAG Gemini</p>
        <h2 className="mt-1 font-display text-2xl font-extrabold text-[#1F2937]">Referensi AI Mahasiswa</h2>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-[#4B5563]">
          Mahasiswa hanya menerima jawaban yang didasarkan pada referensi di bawah ini.
        </p>
      </div>
      <div className="border border-dashed border-[#8ED4A8] bg-white p-5">
        <label className="inline-flex cursor-pointer items-center gap-2 bg-[#0B6B3A] px-4 py-3 text-sm font-bold text-white hover:bg-[#07532D]" data-testid="ai-reference-upload-label">
          {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
          Unggah Referensi
          <input type="file" accept={ACCEPTED_REFERENCES} className="sr-only" data-testid="ai-reference-upload-input" onChange={(event) => uploadReference(event.target.files?.[0])} />
        </label>
        <p className="mt-3 text-xs text-[#6B7280]">PDF, DOC, DOCX, XLS, XLSX, JPG, PNG, dan audio hingga 20MB.</p>
      </div>
      <div className="divide-y divide-gray-100 border border-gray-200 bg-white" data-testid="ai-reference-list">
        {loading ? <div className="p-8 text-center"><Loader2 className="inline h-5 w-5 animate-spin text-[#27AE60]" /></div> : references.length === 0 ? (
          <p className="p-6 text-sm text-[#6B7280]" data-testid="ai-reference-empty-state">Belum ada dokumen referensi AI.</p>
        ) : references.map((item) => (
          <div key={item.id} className="flex items-center justify-between gap-4 p-4" data-testid={`ai-reference-${item.id}`}>
            <div className="min-w-0"><p className="truncate text-sm font-bold text-[#1F2937]"><FileText className="mr-2 inline h-4 w-4 text-[#0B6B3A]" />{item.name}</p><p className="mt-1 text-xs text-[#6B7280]">{item.chunk_count} potongan referensi</p></div>
            <button type="button" onClick={() => removeReference(item.id)} data-testid={`delete-ai-reference-${item.id}`} className="p-2 text-[#B91C1C] hover:bg-[#FEE2E2]"><Trash2 className="h-4 w-4" /></button>
          </div>
        ))}
      </div>
    </section>
  );
}