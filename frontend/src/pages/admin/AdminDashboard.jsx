import React, { useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import AdminRecipientDashboard from "@/components/AdminRecipientDashboard";
import AdminRegistrationSummary from "@/components/AdminRegistrationSummary";
import ParticipantsPanel from "@/components/ParticipantsPanel";
import CampusManager from "@/components/CampusManager";
import { Building2, Home, Users } from "lucide-react";

const MENU = [
  { id: "dashboard", label: "Dashboard", icon: Home },
  { id: "ringkasan", label: "Ringkasan", icon: Home },
  { id: "peserta", label: "Data Peserta", icon: Users },
  { id: "kampus", label: "Kampus", icon: Building2 },
];

export default function AdminDashboard() {
  const [active, setActive] = useState("ringkasan");
  return (
    <DashboardShell menu={MENU} active={active} onSelect={setActive} brandLabel="Admin Pendaftaran"
      title={MENU.find((m) => m.id === active)?.label} subtitle="Kelola data peserta MDJ Scholarship">
      {active === "dashboard" && <AdminRecipientDashboard />}
      {active === "ringkasan" && <AdminRegistrationSummary />}
      {active === "peserta" && <ParticipantsPanel />}
      {active === "kampus" && <CampusManager />}
    </DashboardShell>
  );
}
