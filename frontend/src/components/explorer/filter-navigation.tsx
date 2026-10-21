"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, type ReactNode, useCallback, useContext, useMemo, useOptimistic, useTransition } from "react";

import { type FilterQuery, serializeFilters } from "@/lib/filters";

interface FilterNavigation {
  query: FilterQuery;
  navigate: (next: FilterQuery) => void;
  isPending: boolean;
}

const Context = createContext<FilterNavigation | null>(null);

/**
 * Owns URL updates for a page's filters. The server re-renders the results for the new
 * URL; while that transition runs, controls already show the requested state (optimistic
 * query) and `isPending` lets the result region show that work is in progress.
 */
export function FilterNavigationProvider({ query, children }: { query: FilterQuery; children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();
  const [optimisticQuery, setOptimisticQuery] = useOptimistic(query);

  const navigate = useCallback(
    (next: FilterQuery) => {
      const search = serializeFilters(next);
      startTransition(() => {
        setOptimisticQuery(next);
        router.push(search ? `${pathname}?${search}` : pathname, { scroll: false });
      });
    },
    [pathname, router, setOptimisticQuery],
  );

  const value = useMemo(
    () => ({ query: optimisticQuery, navigate, isPending }),
    [optimisticQuery, navigate, isPending],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useFilterNavigation(): FilterNavigation {
  const value = useContext(Context);
  if (!value) throw new Error("useFilterNavigation must be used inside FilterNavigationProvider");
  return value;
}

/** Dims its content and marks it busy while new results load. */
export function PendingRegion({ children, label }: { children: ReactNode; label: string }) {
  const { isPending } = useFilterNavigation();
  return (
    <div aria-busy={isPending} aria-label={label} className={isPending ? "opacity-60 transition-opacity" : undefined}>
      {children}
    </div>
  );
}
