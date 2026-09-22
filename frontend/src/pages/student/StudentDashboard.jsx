import React, { useCallback, useEffect, useState, useMemo } from "react";
import { toast } from "sonner";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import DashboardShell, { StatusBadge, STATUS_META } from "@/components/DashboardShell";
import StudentProfile, {
  getMissingProfileFields,
  profileProgress,
} from "@/components/StudentProfile";
import AccountSettings from "@/components/AccountSettings";
import RegistrationSections from "@/components/RegistrationSections";
import StudentDisbursementProofs from "@/components/StudentDisbursementProofs";
import SelectionResultPopup from "@/components/SelectionResultPopup";
import RegistrationClosedDialog from "@/components/RegistrationClosedDialog";
import DocumentRevisionPopup from "@/components/DocumentRevisionPopup";
import SiteAnnouncementPopup from "@/components/SiteAnnouncementPopup";
import StudentLiveChat from "@/components/StudentLiveChat";
import StudentAiChatWidget from "@/components/StudentAiChatWidget";
import { docFileUrl } from "@/components/DocPreview";
import {
  Home, User, FileText, Activity, Megaphone, Settings, Save, Loader2,
  CheckCircle2, FileCheck, MessageCircleMore,
} from "lucide-react";

const MENU = [
  { id: "ringkasan", label: "Ringkasan", icon: Home },
  { id: "profil", label: "Profil Saya", icon: User },
  { id: "daftar", label: "Pendaftaran", icon: FileText },
  { id: "status", label: "Status Seleksi", icon: Activity },
  { id: "pengumuman", label: "Pengumuman", icon: Megaphone },
  { id: "live-chat-admin", label: "Live Chat Admin", icon: MessageCircleMore },
  { id: "pengaturan", label: "Pengaturan", icon: Settings },
];

const DOC_TYPES = [
  "KTP DKI Jakarta", "Kartu Keluarga (KK)", "Pas Foto 3x4", "Kartu Tanda Mahasiswa (KTM)",
  "KRS / KHS / Transkrip Nilai",
  "Surat Keterangan Mahasiswa Aktif", "SKTM / Surat Rekomendasi", "Surat Persetujuan Orang Tua",
  "Surat Keterangan Tidak Menerima Beasiswa Lain",
];
const DEFAULT_REGISTRATION_CATEGORY = "Mahasiswa Sarjana (S1)";

function isRegistrationWindowOpen(settings = {}) {
  if (settings.registration_open !== true) return false;
  const now = Date.now();
  const starts = settings.registration_start_at ? new Date(settings.registration_start_at).getTime() : null;
  const ends = settings.registration_end_at ? new Date(settings.registration_end_at).getTime() : null;
  return (!starts || now >= starts) && (!ends || now < ends);
}

export default function StudentDashboard() {
  const { user, setUser } = useAuth();
  const [active, setActive] = useState("ringkasan");
  const [data, setData] = useState({});
  const [reg, setReg] = useState({});
  const [docs, setDocs] = useState([]);
  const [campuses, setCampuses] = useState([]);
  const [content, setContent] = useState({});
  const [notifications, setNotifications] = useState([]);
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0);
  const [selectionAnnouncement, setSelectionAnnouncement] = useState(null);
  const [documentRevision, setDocumentRevision] = useState(null);
  const [siteAnnouncement, setSiteAnnouncement] = useState(null);
  const [registrationRequestedTab, setRegistrationRequestedTab] = useState("pendidikan");
  const [registrationClosedDialogOpen, setRegistrationClosedDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [submittingRegistration, setSubmittingRegistration] = useState(false);

  const loadNotifications = useCallback(async () => {
    try {
      const response = await api.get("/notifications");
      setNotifications(response.data.notifications || []);
      setUnreadNotificationCount(response.data.unread_count || 0);
    } catch {
      setNotifications([]);
      setUnreadNotificationCount(0);
    }
  }, []);

  const loadSelectionAnnouncement = useCallback(async () => {
    try {
      const response = await api.get("/student/selection-announcements/pending");
      setSelectionAnnouncement(response.data.announcement || null);
    } catch {
      setSelectionAnnouncement(null);
    }
  }, []);

  const loadDocumentRevision = useCallback(async () => {
    try {
      const response = await api.get("/student/document-revisions/pending");
      setDocumentRevision(response.data.revision || null);
    } catch {
      setDocumentRevision(null);
    }
  }, []);

  const loadSiteAnnouncement = useCallback(async () => {
    try {
      const response = await api.get("/student/site-announcements/pending");
      setSiteAnnouncement(response.data.announcement || null);
    } catch {
      setSiteAnnouncement(null);
    }
  }, []);

  useEffect(() => {
    api.get("/profile").then((r) => setData(r.data.data || {}));
    api.get("/registration").then((r) => setReg(r.data || {}));
    api.get("/documents").then((r) => setDocs(r.data));
    api.get("/campuses").then((r) => setCampuses(r.data || []));
    api.get("/site/content").then((r) => setContent(r.data));
    loadNotifications();
    loadSelectionAnnouncement();
    loadDocumentRevision();
    loadSiteAnnouncement();
    const pollNotifications = window.setInterval(() => {
      loadNotifications();
      loadSelectionAnnouncement();
      loadSiteAnnouncement();
    }, 30000);
    return () => window.clearInterval(pollNotifications);
  }, [
    loadDocumentRevision,
    loadNotifications,
    loadSelectionAnnouncement,
    loadSiteAnnouncement,
  ]);

  const progress = useMemo(() => profileProgress(data), [data]);
  const missingProfileFields = useMemo(() => getMissingProfileFields(data), [data]);
  const profileCompletionDetail = missingProfileFields.length
    ? `Belum diisi: ${missingProfileFields.map((field) => field.l).join(", ")}`
    : "Seluruh data wajib telah lengkap.";
  const uploadedDocumentCount = useMemo(
    () => DOC_TYPES.filter((type) => docs.some((document) => document.doc_type === type)).length,
    [docs],
  );
  const documentProgress = useMemo(
    () => Math.round((uploadedDocumentCount / DOC_TYPES.length) * 100),
    [uploadedDocumentCount],
  );
  const profilePhoto = useMemo(
    () => docs.find((document) => document.doc_type === "Pas Foto 3x4"),
    [docs],
  );
  const avatarUrl = profilePhoto ? docFileUrl(profilePhoto) : null;
  const registrationDocumentsLocked = Boolean(
    reg.status && reg.status !== "draft" && !reg.documents_editing_allowed,
  );

  const set = (k, v) => setData((p) => ({ ...p, [k]: v }));

  const saveProfile = async () => {
    setSaving(true);
    try {
      const response = await api.put("/profile", { data });
      const campus = response.data.campus;
      if (response.data.user) {
        setUser(response.data.user);
      }
      if (campus) {
        setCampuses((previous) => [...previous, campus].sort((a, b) => a.name.localeCompare(b.name)));
        toast.success(`Kampus baru ditambahkan dengan kode ${campus.code}.`);
      } else {
        toast.success("Profil berhasil disimpan.");
      }
    }
    catch { toast.error("Gagal menyimpan profil."); }
    finally { setSaving(false); }
  };

  const uploadDoc = async (docType, file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("doc_type", docType);
    fd.append("file", file);
    try {
      await api.post("/documents", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const r = await api.get("/documents");
      setDocs(r.data);
      toast.success(`${docType} berhasil diunggah.`);
    } catch { toast.error("Gagal mengunggah dokumen."); }
  };

  const deleteDoc = async (id) => {
    await api.delete(`/documents/${id}`);
    setDocs((p) => p.filter((d) => d.id !== id));
    toast.success("Dokumen dihapus.");
  };

  const openNotification = async (notification) => {
    if (!notification.is_read) {
      await api.post(`/notifications/${notification.id}/read`);
      setNotifications((previous) => previous.map((item) => (
        item.id === notification.id ? { ...item, is_read: true } : item
      )));
      setUnreadNotificationCount((previous) => Math.max(previous - 1, 0));
    }
    if (notification.type === "announcement") {
      setActive("pengumuman");
      return;
    }
    setActive(notification.type === "disbursement_proof" ? "bukti-transfer" : "status");
  };

  const markAllNotificationsRead = async () => {
    await api.post("/notifications/read-all");
    setNotifications((previous) => previous.map((item) => ({ ...item, is_read: true })));
    setUnreadNotificationCount(0);
  };

  const markSelectionAnnouncementSeen = async (notificationId) => {
    try {
      await api.post(`/student/selection-announcements/${notificationId}/seen`);
      await loadNotifications();
    } catch {
      toast.error("Pengumuman belum dapat ditandai sebagai sudah dibaca.");
    }
  };

  const dismissSelectionAnnouncement = async (notificationId) => {
    await markSelectionAnnouncementSeen(notificationId);
    setSelectionAnnouncement(null);
  };

  const dismissDocumentRevision = async (notificationId) => {
    try {
      await api.post(`/student/document-revisions/${notificationId}/seen`);
      setDocumentRevision(null);
      await loadNotifications();
    } catch {
      toast.error("Notifikasi perbaikan belum dapat ditandai sebagai sudah dibaca.");
    }
  };

  const openDocumentRevisionWorkspace = () => {
    setRegistrationRequestedTab("dokumen");
    setActive("daftar");
  };

  const dismissSiteAnnouncement = async (notificationId) => {
    try {
      await api.post(`/student/site-announcements/${notificationId}/seen`);
      setSiteAnnouncement(null);
      await loadNotifications();
    } catch {
      toast.error("Pengumuman belum dapat ditandai sebagai sudah dibaca.");
    }
  };

  const selectDashboardMenu = async (menuId) => {
    if (!["daftar", "status"].includes(menuId)) {
      setActive(menuId);
      return;
    }
    try {
      const response = await api.get("/site/content");
      const nextContent = response.data || {};
      setContent(nextContent);
      if (!isRegistrationWindowOpen(nextContent.settings) && !reg.revision_requested) {
        setRegistrationClosedDialogOpen(true);
        return;
      }
      setActive(menuId);
    } catch {
      setRegistrationClosedDialogOpen(true);
    }
  };

  const submitRegistration = async (action, paktaIntegritasAgreed = false) => {
    if (action === "submit" && progress < 100) return toast.error("Lengkapi seluruh data wajib pada Profil sebelum mengirim.");
    const category = reg.category || DEFAULT_REGISTRATION_CATEGORY;
    setSubmittingRegistration(true);
    try {
      const { data: r } = await api.post("/registration", {
        category,
        action,
        pakta_integritas_agreed: paktaIntegritasAgreed,
      });
      setReg(r);
      toast.success(action === "submit" ? "Pendaftaran berhasil dikirim!" : "Draft pendaftaran disimpan.");
    } catch (error) {
      const detail = error.response?.data?.detail;
      const message = typeof detail === "string"
        ? detail
        : detail?.message || "Gagal memproses pendaftaran.";
      toast.error(message);
    } finally {
      setSubmittingRegistration(false);
    }
  };

  const timeline = content.timeline || [];
  const statusOrder = ["submitted", "verifikasi", "lolos_administrasi", "wawancara", "verifikasi_faktual", "lolos"];
  const currentIdx = statusOrder.indexOf(reg.status);

  return (
    <DashboardShell menu={MENU} active={active} onSelect={selectDashboardMenu} brandLabel="Portal Pendaftar"
      displayName={data.namaLengkap || user?.name}
      title={MENU.find((m) => m.id === active)?.label} subtitle="Program Masa Depan Jakarta 2026"
      avatarUrl={avatarUrl}
      candidateId={reg.cpm_id}
      notifications={notifications}
      unreadNotificationCount={unreadNotificationCount}
      onNotificationClick={openNotification}
      onReadAllNotifications={markAllNotificationsRead}
      actions={active === "profil" && <button onClick={saveProfile} disabled={saving} data-testid="save-profile-btn" className="px-4 py-2 bg-[#27AE60] hover:bg-[#0B6B3A] text-white text-sm font-bold rounded-xl flex items-center gap-2 transition-colors">{saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Simpan</button>}>

      {active === "ringkasan" && (
        <div className="space-y-6">
          <Card className="bg-gradient-to-r from-[#0B6B3A] to-[#27AE60] text-white">
            <p className="text-white/80 text-sm">Assalamualaikum,</p>
            <h2 className="font-display font-black text-2xl mt-1" data-testid="student-greeting-name">{data.namaLengkap || user?.name}</h2>
            <p className="text-white/80 text-sm mt-2">Lengkapi profil dan berkas Anda untuk melanjutkan pendaftaran MDJ Scholarship.</p>
          </Card>
          <div className="grid sm:grid-cols-3 gap-4">
            <StatTile
              icon={User}
              label="Kelengkapan Profil"
              value={`${progress}%`}
              detail={profileCompletionDetail}
              testId="profile-completion"
            />
            <StatTile
              icon={FileCheck}
              label="Kelengkapan Berkas"
              value={`${documentProgress}%`}
              detail={`${uploadedDocumentCount}/${DOC_TYPES.length} dokumen diunggah`}
              testId="document-completion"
            />
            <StatTile
              icon={Activity}
              label="Status"
              value={STATUS_META[reg.status || "draft"].label}
              testId="registration-status"
            />
          </div>
          <Card>
            <div className="flex items-center justify-between gap-4">
              <h3 className="font-display font-bold text-[#1F2937]">Kelengkapan Pendaftaran</h3>
              <span className="text-xs font-semibold text-[#6B7280]">Perbarui seiring data disimpan</span>
            </div>
            <CompletionBar
              label="Kelengkapan Profil"
              value={progress}
              detail={profileCompletionDetail}
              testId="profile-completion-progress"
            />
            <CompletionBar
              label="Kelengkapan Berkas"
              value={documentProgress}
              detail={`${uploadedDocumentCount} dari ${DOC_TYPES.length} berkas telah diunggah`}
              testId="document-completion-progress"
            />
            <p className="mt-4 text-sm text-[#6B7280]">
              Isi seluruh data wajib pada menu Profil Saya, unggah dokumen, lalu kirim pendaftaran Anda.
            </p>
          </Card>
        </div>
      )}

      {active === "profil" && (
        <StudentProfile
          data={data}
          set={set}
          setData={setData}
          docs={docs}
          documentsLocked={registrationDocumentsLocked}
          uploadDoc={uploadDoc}
          deleteDoc={deleteDoc}
          onDocSaved={(document) => setDocs((previous) => [
            ...previous.filter((item) => item.doc_type !== document.doc_type),
            document,
          ])}
        />
      )}

      {active === "daftar" && (
        <RegistrationSections
          data={data}
          setData={setData}
          docs={docs}
          reg={reg}
          setReg={setReg}
          progress={progress}
          saving={saving}
          onSaveProfile={saveProfile}
          onUploadDoc={uploadDoc}
          onDeleteDoc={deleteDoc}
          onDocumentSaved={(document) => setDocs((previous) => [
            ...previous.filter((item) => item.doc_type !== document.doc_type),
            document,
          ])}
          onSubmitRegistration={submitRegistration}
          submissionLoading={submittingRegistration}
          campuses={campuses}
          initialTab={registrationRequestedTab}
        />
      )}

      {active === "status" && (
        <Card>
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-display font-bold text-lg text-[#1F2937]">Status Seleksi</h3>
            <StatusBadge status={reg.status || "draft"} />
          </div>
          {!reg.status || reg.status === "draft" ? (
            <p className="text-sm text-[#6B7280]">Anda belum mengirim pendaftaran. Lengkapi profil & dokumen, lalu kirim di menu Pendaftaran.</p>
          ) : (
            <div className="relative pl-8 border-l-2 border-gray-100 space-y-6">
              {["Pendaftaran Terkirim", "Verifikasi Administrasi", "Lolos Administrasi", "Wawancara Assessment", "Verifikasi Faktual", "Penerima Manfaat"].map((s, i) => {
                const done = reg.status === "ditolak" ? false : i <= currentIdx;
                const isCurrent = i === currentIdx;
                return (
                  <div key={s} className="relative" data-testid={`selection-step-${i}`}>
                    <div className={`absolute -left-[41px] w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${done ? "bg-[#27AE60] text-white" : isCurrent ? "bg-[#F2C94C] text-[#0B6B3A]" : "bg-gray-100 text-gray-400"}`}>{done ? <CheckCircle2 className="w-4 h-4" /> : i + 1}</div>
                    <p className={`font-semibold ${done || isCurrent ? "text-[#1F2937]" : "text-gray-400"}`}>{s}</p>
                  </div>
                );
              })}
              {reg.status === "ditolak" && <div className="rounded-xl bg-[#FEE2E2] p-4 text-sm text-[#DC2626] ml-[-8px]">Mohon maaf, Anda belum lolos pada tahap ini. Terima kasih atas partisipasinya.</div>}
            </div>
          )}
          {(reg.history || []).length > 0 && (
            <div className="mt-8 pt-6 border-t border-gray-100">
              <p className="font-semibold text-sm text-[#1F2937] mb-3">Riwayat</p>
              <div className="space-y-2">
                {[...reg.history].reverse().map((h, i) => (
                  <div key={i} className="flex items-start gap-3 text-sm"><div className="w-2 h-2 rounded-full bg-[#27AE60] mt-1.5" /><div><span className="font-semibold text-[#1F2937]">{STATUS_META[h.status]?.label || h.status}</span>{h.note && <span className="text-[#6B7280]"> — {h.note}</span>}<span className="block text-xs text-gray-400">{new Date(h.at).toLocaleString("id-ID")}</span></div></div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {active === "bukti-transfer" && <StudentDisbursementProofs />}

      {active === "pengumuman" && (
        <div className="space-y-4">
          {(content.announcements || []).map((a, i) => (
            <Card key={i}>
              <div className="flex items-center justify-between mb-2"><span className="px-2.5 py-1 rounded-full bg-[#E8F6EE] text-[#0B6B3A] text-[11px] font-bold">{a.category}</span><span className="text-xs text-[#6B7280]">{a.date}</span></div>
              <h3 className="font-display font-bold text-[#1F2937]">{a.title}</h3>
              <p className="text-sm text-[#6B7280] mt-1">{a.summary}</p>
            </Card>
          ))}
        </div>
      )}

      {active === "live-chat-admin" && <StudentLiveChat />}
      {active === "pengaturan" && <AccountSettings />}
      <StudentAiChatWidget />
      <DocumentRevisionPopup
        revision={documentRevision}
        onDismiss={dismissDocumentRevision}
        onRepair={openDocumentRevisionWorkspace}
      />
      {!documentRevision && (
        <SelectionResultPopup
          announcement={selectionAnnouncement}
          onMarkSeen={markSelectionAnnouncementSeen}
          onDismiss={dismissSelectionAnnouncement}
        />
      )}
      {!documentRevision && !selectionAnnouncement && (
        <SiteAnnouncementPopup
          announcement={siteAnnouncement}
          onDismiss={dismissSiteAnnouncement}
          onView={() => setActive("pengumuman")}
        />
      )}
      <RegistrationClosedDialog
        open={registrationClosedDialogOpen}
        onClose={() => setRegistrationClosedDialogOpen(false)}
      />
    </DashboardShell>
  );
}

const Card = ({ children, className = "" }) => <div className={`bg-white border border-gray-100 rounded-2xl p-6 shadow-[0_4px_20px_-2px_rgba(39,174,96,0.05)] ${className}`}>{children}</div>;
const StatTile = ({ icon: Icon, label, value, detail, testId }) => (
  <div
    className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    data-testid={testId}
  >
    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[#E8F6EE]">
      <Icon className="h-5 w-5 text-[#27AE60]" />
    </div>
    <p className="text-xs text-[#6B7280]" data-testid={`${testId}-label`}>{label}</p>
    <p className="mt-0.5 font-display text-xl font-extrabold text-[#1F2937]" data-testid={`${testId}-value`}>
      {value}
    </p>
    {detail && <p className="mt-1 text-xs text-[#6B7280]" data-testid={`${testId}-detail`}>{detail}</p>}
  </div>
);

const CompletionBar = ({ label, value, detail, testId }) => (
  <div className="mt-5" data-testid={testId}>
    <div className="mb-2 flex items-center justify-between gap-4">
      <p className="text-sm font-semibold text-[#1F2937]" data-testid={`${testId}-label`}>{label}</p>
      <span className="text-sm font-bold text-[#27AE60]" data-testid={`${testId}-value`}>{value}%</span>
    </div>
    <div className="h-3 overflow-hidden rounded-full bg-gray-100">
      <div
        className="h-full rounded-full bg-[#27AE60] transition-[width] duration-300"
        style={{ width: `${value}%` }}
        data-testid={`${testId}-bar`}
      />
    </div>
    {detail && <p className="mt-2 text-xs text-[#6B7280]" data-testid={`${testId}-detail`}>{detail}</p>}
  </div>
);
