import type { Metadata } from "next";
import "./globals.css";
import { Nav } from "@/components/nav";

export const metadata: Metadata = { title: "Fund Manager", description: "IDX trading dashboard" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-zinc-950 text-zinc-100 min-h-screen font-mono">
        <Nav />
        <main className="p-4 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
