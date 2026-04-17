import { api } from "@/lib/api";

export async function KillSwitchBanner() {
  let ks: { active: boolean; reason?: string } = { active: false, reason: "" };
  try { ks = await api.getKillSwitch(); } catch { }
  if (!ks.active) return null;
  return (
    <div className="bg-red-900 border border-red-500 text-red-100 px-4 py-2 text-sm font-semibold">
      ⛔ KILL SWITCH ACTIVE — {ks.reason || "no new entries"}
    </div>
  );
}
