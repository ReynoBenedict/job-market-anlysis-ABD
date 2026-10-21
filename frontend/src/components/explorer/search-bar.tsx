"use client";

import { type FormEvent, useState } from "react";
import { Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui";
import { withoutKeyword, withoutPage } from "@/lib/filters";

import { useFilterNavigation } from "./filter-navigation";

const MAX_QUERY_LENGTH = 100;

export function SearchBar() {
  const { query, navigate, isPending } = useFilterNavigation();
  const [text, setText] = useState(query.q ?? "");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = text.trim();
    navigate(q ? { ...withoutPage(query), q } : withoutKeyword(query));
  }

  return (
    <form role="search" onSubmit={submit} className="flex flex-col gap-3 sm:flex-row">
      <label htmlFor="job-search" className="sr-only">
        Cari posisi, perusahaan, lokasi, atau tag
      </label>
      <div className="relative flex-1">
        <Search aria-hidden className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-3" />
        <input
          id="job-search"
          type="search"
          value={text}
          maxLength={MAX_QUERY_LENGTH}
          onChange={(event) => setText(event.target.value)}
          placeholder="Posisi, perusahaan, atau kota"
          className="h-11 w-full rounded-md border border-line bg-card pl-10 pr-3 text-[15px] text-ink focus:border-teal focus:outline-none focus:ring-[3px] focus:ring-teal/15"
        />
      </div>
      <Button type="submit" className="h-11 px-6" disabled={isPending}>
        {isPending ? <Loader2 aria-hidden className="size-4 animate-spin" /> : null}
        Cari Lowongan
      </Button>
    </form>
  );
}
