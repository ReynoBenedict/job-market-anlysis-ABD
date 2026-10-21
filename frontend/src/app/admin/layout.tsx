import type { Metadata } from "next";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { Logo } from "@/components/shell/logo";

export const metadata: Metadata = { title: { default: "Admin", template: "%s · Admin TalentScope" }, robots: { index: false } };

const ADMIN_NAV = [
  { href: "/admin", label: "Sumber Data" },
  { href: "/admin/riwayat", label: "Riwayat Eksekusi" },
  { href: "/admin/kualitas", label: "Kualitas Data" },
  { href: "/admin/audit", label: "Audit Perubahan" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-4 py-3 md:px-6">
          <Logo />
          <span className="inline-flex items-center gap-1.5 rounded-full bg-navy px-2.5 py-0.5 text-xs font-semibold text-white">
            <ShieldCheck aria-hidden className="size-3.5" /> Area admin
          </span>
          <nav aria-label="Navigasi admin" className="flex flex-wrap gap-1 text-sm">
            {ADMIN_NAV.map((item) => (
              <Link key={item.href} href={item.href} className="rounded-md px-3 py-1.5 font-medium text-ink-2 hover:bg-sunken hover:text-ink">
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main id="konten" className="mx-auto max-w-6xl px-4 py-8 md:px-6">{children}</main>
    </div>
  );
}
