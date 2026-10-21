"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Bookmark, Menu, X } from "lucide-react";

import { cx } from "@/components/ui";
import { useSavedJobs } from "@/lib/saved-jobs";

import { Logo } from "./logo";
import { isActiveSection, MAIN_NAV } from "./nav";

function SavedLink({
  pathname,
  onNavigate,
  inMenu = false,
}: {
  pathname: string | null;
  onNavigate?: () => void;
  /** In the mobile menu the link matches the other menu rows instead of the compact header button. */
  inMenu?: boolean;
}) {
  const count = useSavedJobs().length;
  const active = pathname === "/tersimpan";
  return (
    <Link
      href="/tersimpan"
      onClick={onNavigate}
      aria-current={active ? "page" : undefined}
      className={cx(
        "items-center gap-2 rounded-md px-3 font-medium transition-colors",
        inMenu ? "flex h-12 text-base" : "inline-flex h-10 text-sm",
        active ? "bg-teal-wash text-teal-text" : inMenu ? "text-ink hover:bg-sunken" : "text-ink-2 hover:bg-sunken hover:text-ink",
      )}
    >
      <Bookmark aria-hidden className="size-4" />
      Tersimpan
      {count ? (
        <span className="tabular rounded-full bg-teal px-1.5 text-xs font-semibold leading-5 text-white">{count}</span>
      ) : null}
    </Link>
  );
}

/** One header for every page: inline links on wide screens, a disclosure menu on small ones. */
export function SiteHeader() {
  // The path is request data; isolating it lets every route prerender the header shell,
  // with the active link highlighted once the path is known.
  return (
    <Suspense fallback={<HeaderContent pathname={null} />}>
      <HeaderWithPath />
    </Suspense>
  );
}

function HeaderWithPath() {
  return <HeaderContent pathname={usePathname()} />;
}

function HeaderContent({ pathname }: { pathname: string | null }) {
  // The menu remembers the page it was opened on, so it closes by itself after navigation.
  const [openOn, setOpenOn] = useState<string | null | undefined>(undefined);
  const open = openOn !== undefined && openOn === pathname;
  const setOpen = (next: boolean | ((current: boolean) => boolean)) =>
    setOpenOn((typeof next === "function" ? next(open) : next) ? pathname : undefined);

  const headerRef = useRef<HTMLElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpenOn(undefined);
      // Return focus to the toggle when it was inside the menu, so keyboard users are not dropped at <body>.
      if (headerRef.current?.contains(document.activeElement)) toggleRef.current?.focus();
    };
    // The open menu covers the top of the page; close it once keyboard focus moves past it.
    const onFocusIn = (event: FocusEvent) => {
      if (!headerRef.current?.contains(event.target as Node)) setOpenOn(undefined);
    };
    window.addEventListener("keydown", onKey);
    document.addEventListener("focusin", onFocusIn);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("focusin", onFocusIn);
    };
  }, [open]);

  return (
    <header ref={headerRef} className="sticky top-0 z-40 border-b border-line bg-card/95 backdrop-blur">
      <a
        href="#konten"
        className="sr-only focus:not-sr-only focus:absolute focus:inset-x-0 focus:top-0 focus:z-50 focus:flex focus:h-16 focus:items-center focus:justify-center focus:bg-card focus:font-semibold focus:text-teal-text focus:underline focus:outline-offset-[-4px]"
      >
        Lewati ke konten
      </a>
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 md:px-6">
        <Logo />
        <nav aria-label="Navigasi utama" className="hidden lg:block">
          <ul className="flex items-center gap-1">
            {MAIN_NAV.map((item) => {
              const active = isActiveSection(pathname, item);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cx(
                      "relative inline-flex h-10 items-center rounded-md px-3 text-sm font-medium transition-colors",
                      active ? "text-teal-text" : "text-ink-2 hover:bg-sunken hover:text-ink",
                    )}
                  >
                    {item.label}
                    {active ? <span aria-hidden className="absolute inset-x-3 -bottom-[13px] h-0.5 rounded-full bg-teal" /> : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
        <div className="flex items-center gap-1">
          <div className="hidden sm:block">
            <SavedLink pathname={pathname} />
          </div>
          <button
            ref={toggleRef}
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls="menu-seluler"
            className="inline-flex size-10 items-center justify-center rounded-md text-ink-2 hover:bg-sunken lg:hidden"
          >
            {open ? <X aria-hidden className="size-5" /> : <Menu aria-hidden className="size-5" />}
            <span className="sr-only">{open ? "Tutup menu" : "Buka menu"}</span>
          </button>
        </div>
      </div>

      {open ? (
        <nav id="menu-seluler" aria-label="Menu" className="border-t border-line bg-card px-4 pb-4 pt-2 shadow-[var(--shadow-float)] lg:hidden">
          <ul className="space-y-1">
            {MAIN_NAV.map((item) => {
              const active = isActiveSection(pathname, item);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={cx(
                      "flex h-12 items-center rounded-md px-3 text-base font-medium",
                      active ? "bg-teal-wash text-teal-text" : "text-ink hover:bg-sunken",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
            <li className="sm:hidden">
              <SavedLink pathname={pathname} onNavigate={() => setOpen(false)} inMenu />
            </li>
          </ul>
        </nav>
      ) : null}
    </header>
  );
}
