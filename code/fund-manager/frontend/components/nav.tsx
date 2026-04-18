"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/portfolio", label: "Portfolio" },
  { href: "/watchlist", label: "Watchlist" },
  { href: "/thesis", label: "Thesis" },
  { href: "/screener", label: "Screener" },
];

export function Nav() {
  const path = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/85 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-[1280px] flex-col gap-4 px-4 py-4 md:px-6">
        <div className="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
          <div>
            <Link href="/portfolio" className="inline-flex items-center gap-2 text-sm font-semibold tracking-[-0.02em] text-foreground">
              <span className="inline-flex size-2 rounded-full bg-primary shadow-[0_0_14px_rgba(94,106,210,0.45)] dark:shadow-[0_0_18px_rgba(113,112,255,0.8)]" />
              Fund Manager
            </Link>
            <p className="text-xs text-muted-foreground">Portfolio, watchlist, research, and broker flow in fewer workspaces.</p>
          </div>
          <div className="hidden text-[11px] uppercase tracking-[0.18em] text-muted-foreground md:block">
            Light default · Workflow first
          </div>
        </div>

        <nav className="flex flex-wrap gap-2">
          {links.map((link) => {
            const active = path === link.href;

            return (
              <Link
                key={link.href}
                href={link.href}
                className={[
                  "inline-flex items-center rounded-full border px-3 py-1.5 text-[13px] font-medium transition-all focus-visible:ring-2 focus-visible:ring-ring",
                  active
                    ? "border-primary/30 bg-primary/14 text-foreground shadow-[0_0_0_1px_rgba(113,112,255,0.08)]"
                    : "border-border/70 bg-secondary/45 text-muted-foreground hover:border-border hover:bg-secondary hover:text-foreground",
                ].join(" ")}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
