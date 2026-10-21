import Link from "next/link";

import { Logo } from "./logo";

const LINKS = [
  {
    title: "Jelajahi",
    items: [
      ["/lowongan", "Cari Lowongan"],
      ["/gaji", "Gaji"],
      ["/ringkasan", "Pasar Kerja"],
      ["/keterampilan", "Keterampilan"],
      ["/tersimpan", "Lowongan Tersimpan"],
    ],
  },
  {
    title: "Tentang data",
    items: [
      ["/sumber-data", "Sumber data"],
      ["/metodologi", "Cara kami menghitung"],
      ["/metodologi#koreksi", "Minta koreksi atau penghapusan"],
    ],
  },
] as const;

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-card">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 md:grid-cols-[1.6fr_1fr_1fr] md:px-6">
        <div>
          <Logo />
          <p className="mt-3 max-w-sm text-sm text-ink-3">
            Proyek portofolio untuk memahami lowongan kerja di Indonesia, dengan sumber dan batasan data yang terbuka.
            TalentScope tidak berafiliasi dengan situs sumber dan tidak menerima lamaran.
          </p>
        </div>
        {LINKS.map((group) => (
          <nav key={group.title} aria-label={group.title}>
            <p className="text-sm font-semibold text-ink">{group.title}</p>
            <ul className="mt-3 space-y-2 text-sm text-ink-2">
              {group.items.map(([href, label]) => (
                <li key={href}>
                  <Link className="hover:text-teal-text hover:underline" href={href}>
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
    </footer>
  );
}
