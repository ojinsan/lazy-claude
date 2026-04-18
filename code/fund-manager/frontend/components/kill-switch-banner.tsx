import { api } from "@/lib/api";

export async function KillSwitchBanner() {
  let ks: { active: boolean; reason?: string } = { active: false, reason: "" };
  try {
    ks = await api.getKillSwitch();
  } catch {}
  if (!ks.active) return null;

  return (
    <div className="rounded-2xl border border-danger/35 bg-danger/14 px-4 py-3 text-sm text-danger shadow-[0_10px_30px_rgba(255,99,105,0.08)]">
      <div className="font-semibold tracking-[-0.02em]">Kill switch active</div>
      <div className="mt-1 text-danger/85">{ks.reason || "No new entries."}</div>
    </div>
  );
}
