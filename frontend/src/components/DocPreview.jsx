import React from "react";
import { X, Download } from "lucide-react";

export const docFileUrl = (doc) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("mdj_token") : null;
  return `${process.env.REACT_APP_BACKEND_URL}/api/files/${doc.storage_path}${token ? `?auth=${token}` : ""}`;
};

export function DocPreview({ doc, onClose }) {
  if (!doc) return null;
  const url = docFileUrl(doc);
  const isPdf = (doc.content_type || "").includes("pdf") || /\.pdf$/i.test(doc.original_filename || "");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={onClose} data-testid="doc-preview-modal">
      <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-3 px-5 py-3 border-b border-gray-100">
          <div className="min-w-0">
            <p className="font-display font-bold text-[#1F2937] truncate">{doc.doc_type}</p>
            <p className="text-xs text-[#6B7280] truncate">{doc.original_filename}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <a href={url} target="_blank" rel="noreferrer" data-testid="doc-preview-download"
              className="px-3 py-2 text-xs font-bold rounded-lg border border-gray-300 hover:bg-gray-50 flex items-center gap-1.5 text-[#1F2937]">
              <Download className="w-4 h-4" /> Buka / Unduh
            </a>
            <button onClick={onClose} data-testid="doc-preview-close" aria-label="Tutup" className="p-2 rounded-lg hover:bg-gray-100 text-[#6B7280]"><X className="w-5 h-5" /></button>
          </div>
        </div>
        <div className="flex-1 bg-[#F3F4F6] overflow-auto flex items-center justify-center min-h-[60vh]">
          {isPdf ? (
            <iframe title={doc.original_filename} src={url} className="w-full h-[75vh]" data-testid="doc-preview-pdf" />
          ) : (
            <img src={url} alt={doc.doc_type} className="max-w-full max-h-[75vh] object-contain" data-testid="doc-preview-image" />
          )}
        </div>
      </div>
    </div>
  );
}
