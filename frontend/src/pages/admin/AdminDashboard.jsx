import React, { useState } from "react";
import DashboardShell from "@/components/DashboardShell";
import StatsOverview from "@/components/StatsOverview";
import ParticipantsPanel from "@/components/ParticipantsPanel";
import { Home, Users } from "lucide-react";

const MENU = [
  { id: "ringkasan", label: "Ringkasan", icon: Home },
  { id: "peserta", label: "Data Peserta", icon: Users },
];

export default function AdminDashboard() {
  const [active, setActive] = useState("ringkasan");
  return (
    <DashboardShell menu={MENU} active={active} onSelect={setActive} brandLabel="Admin Pendaftaran"
      title={MENU.find((m) => m.id === active)?.label} subtitle="Kelola data peserta MDJ Scholarship">
      {active === "ringkasan" && <StatsOverview />}
      {active === "peserta" && <ParticipantsPanel />}
    </DashboardShell>
  );
}
