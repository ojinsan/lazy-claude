import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fund Manager",
  description: "IDX trading dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <body>
        <div className="relative min-h-screen">
          <Nav />
          <main className="mx-auto flex w-full max-w-[1280px] flex-col gap-8 px-4 py-6 md:px-6 md:py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
