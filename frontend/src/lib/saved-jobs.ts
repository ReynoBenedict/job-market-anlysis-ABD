"use client";

import { useSyncExternalStore } from "react";

/**
 * Saved jobs are kept only in this browser (localStorage). TalentScope has no accounts,
 * so no personal data leaves the device. A summary is stored with each ID so the list
 * renders without extra API calls; the detail page always loads fresh data.
 */

export interface SavedJob {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  /** Status label when saved (added later; older entries lack it). */
  status?: string;
  savedAt: string;
}

const STORAGE_KEY = "talentscope:saved-jobs:v1";
const EMPTY: SavedJob[] = [];
const listeners = new Set<() => void>();
let cache: { raw: string | null; jobs: SavedJob[] } = { raw: null, jobs: EMPTY };

function read(): SavedJob[] {
  let raw: string | null = null;
  try {
    raw = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return EMPTY; // storage blocked (private mode, disabled site data)
  }
  if (raw === cache.raw) return cache.jobs;
  let jobs: SavedJob[] = EMPTY;
  try {
    const parsed: unknown = raw ? JSON.parse(raw) : [];
    if (Array.isArray(parsed)) jobs = parsed.filter((item): item is SavedJob => typeof item?.id === "string");
  } catch {
    jobs = EMPTY;
  }
  cache = { raw, jobs };
  return jobs;
}

function write(jobs: SavedJob[]): boolean {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  } catch {
    return false;
  }
  listeners.forEach((listener) => listener());
  return true;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (event: StorageEvent) => {
    if (event.key === STORAGE_KEY) listener();
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

export function useSavedJobs(): SavedJob[] {
  return useSyncExternalStore(subscribe, read, () => EMPTY);
}

function storageAvailable(): boolean {
  try {
    window.localStorage.getItem(STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}

/** False when the browser blocks site storage, so an empty list can be explained honestly. */
export function useSavedJobsAvailable(): boolean {
  return useSyncExternalStore(subscribe, storageAvailable, () => true);
}

/** Remove one job; returns false when the browser refuses to store data. */
export function removeSavedJob(id: string): boolean {
  return write(read().filter((saved) => saved.id !== id));
}

/** Returns false when the browser refuses to store data. */
export function toggleSavedJob(job: Omit<SavedJob, "savedAt">): boolean {
  const jobs = read();
  const next = jobs.some((saved) => saved.id === job.id)
    ? jobs.filter((saved) => saved.id !== job.id)
    : [{ ...job, savedAt: new Date().toISOString() }, ...jobs];
  return write(next);
}

export function clearSavedJobs(): boolean {
  return write([]);
}
