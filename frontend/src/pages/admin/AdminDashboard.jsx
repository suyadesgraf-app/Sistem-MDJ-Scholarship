import React, { useMemo, useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import AdminRecipientDashboard from "@/components/AdminRecipientDashboard";
import AdminRegistrationSummary from "@/components/AdminRegistrationSummary";
import ParticipantsPanel from "@/components/ParticipantsPanel";
import CampusManager from "@/components/CampusManager";
import DisbursementManager from "@/components/DisbursementManager";
import ActiveLetterApprovalManager from "@/components/ActiveLetterApprovalManager";
import SelectionImportManager from "@/components/SelectionImportManager";
import AiAdministrativeVerification from "@/components/AiAdministrativeVerification";
import AdminUsers from "@/components/AdminUsers";
import LiveChat from "@/components/LiveChat";
import SelectionAnnouncementManager from "@/components/SelectionAnnouncementManager";
import { useAuth } from "@/context/AuthContext";
import {
  BarChart3,
  BellRing,
  Building2,
  FileCheck2,
  HandCoins,
  FileSpreadsheet,
  LayoutDashboard,
  MessageCircleMore,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";

const BASE_MENU = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "ringkasan", label: "Ringkasan", icon: BarChart3 },
  { id: "peserta", label: "Data Peserta", icon: Users },
  { id: "import-seleksi", label: "Import Seleksi", icon: FileSpreadsheet },
  { id: "verifikasi-ai", label: "Verifikasi AI", icon: Sparkles },
];

export default function AdminDashboard() {
  const { user } = useAuth();
  const [active, setActive] = useState("dashboard");
  const isRegionalAdmin = user?.role === "admin_wilayah";
  const menu = useMemo(() => {
    if (isRegionalAdmin) {
      return [
        ...BASE_MENU.filter((item) => !["import-seleksi", "verifikasi-ai"].includes(item.id)),
        { id: "pencairan-dana", label: "Pencairan Dana", icon: HandCoins },
        { id: "live-chat", label: "Live Chat", icon: MessageCircleMore },
      ];
    }

    return [
      ...BASE_MENU,
      { id: "surat-aktif", label: "Surat Aktif AI", icon: FileCheck2 },
      { id: "pencairan-dana", label: "Pencairan Dana", icon: HandCoins },
      { id: "kampus", label: "Kampus", icon: Building2 },
      { id: "admin-wilayah", label: "Admin Wilayah", icon: ShieldCheck },
      { id: "live-chat", label: "Live Chat", icon: MessageCircleMore },
      { id: "pengumuman-seleksi", label: "Pengumuman Hasil Seleksi", icon: BellRing },
    ];
  }, [isRegionalAdmin]);
  const activeMenu = menu.find((item) => item.id === active);
  const subtitle = isRegionalAdmin
    ? `Kelola data peserta ${user?.region || "wilayah kerja"}`
    : "Kelola data peserta MDJ Scholarship";

  return (
    <DashboardShell
      menu={menu}
      active={active}
      onSelect={setActive}
      brandLabel={isRegionalAdmin ? "Admin Wilayah" : "Admin Provinsi"}
      title={activeMenu?.label}
      subtitle={subtitle}
    >
      {active === "dashboard" && <AdminRecipientDashboard />}
      {active === "ringkasan" && <AdminRegistrationSummary />}
      {active === "peserta" && <ParticipantsPanel />}
      {active === "pencairan-dana" && <DisbursementManager />}
      {active === "verifikasi-ai" && <AiAdministrativeVerification />}
      {active === "import-seleksi" && <SelectionImportManager />}
      {active === "kampus" && <CampusManager />}
      {active === "surat-aktif" && <ActiveLetterApprovalManager />}
      {active === "admin-wilayah" && <AdminUsers canManageProvincial={false} />}
      {active === "live-chat" && <LiveChat />}
      {active === "pengumuman-seleksi" && <SelectionAnnouncementManager />}
    </DashboardShell>
  );
}
