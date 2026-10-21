export interface NavItem {
  href: string;
  label: string;
  /** Other routes that belong to this section, so its link stays highlighted there. */
  also?: string[];
}

/** Primary destinations, in order of how often people need them. */
export const MAIN_NAV: NavItem[] = [
  { href: "/lowongan", label: "Cari Lowongan" },
  { href: "/gaji", label: "Gaji" },
  { href: "/ringkasan", label: "Pasar Kerja", also: ["/pasar"] },
  { href: "/keterampilan", label: "Keterampilan" },
  { href: "/sumber-data", label: "Tentang Data", also: ["/metodologi"] },
];

export function isActiveSection(pathname: string | null, item: NavItem): boolean {
  if (!pathname) return false;
  return [item.href, ...(item.also ?? [])].some((href) => pathname === href || pathname.startsWith(`${href}/`));
}
