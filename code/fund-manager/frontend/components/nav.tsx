"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/portfolio", label: "Portfolio" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/tradeplans", label: "Plans" },
  { href: "/signals", label: "Signals" },
  { href: "/journal", label: "Journal" },
  { href: "/thesis", label: "Thesis" },
  { href: "/themes", label: "Themes" },
  { href: "/performance", label: "Performance" },
  { href: "/evaluation", label: "Evaluation" },
  { href: "/tape", label: "Tape" },
  { href: "/konglo", label: "Konglo" },
  { href: "/confluence", label: "Confluence" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav className="flex gap-1 flex-wrap border-b border-zinc-800 px-4 py-2 bg-zinc-950 text-sm sticky top-0 z-50">
      {links.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={`px-3 py-1 rounded ${path === l.href ? "bg-zinc-700 text-white" : "text-zinc-400 hover:text-white"}`}
        >
          {l.label}
        </Link>
      ))}
    </nav>
  );
}
