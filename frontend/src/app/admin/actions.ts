"use server";

import { refresh } from "next/cache";

import { assertAdminRequest, adminApi } from "@/lib/admin-api";
import { ApiError } from "@/lib/api";

export interface PauseState {
  error?: string;
  ok?: string;
}

export async function setSourcePaused(_: PauseState, formData: FormData): Promise<PauseState> {
  await assertAdminRequest();
  const sourceId = String(formData.get("sourceId") ?? "");
  const paused = formData.get("paused") === "true";
  const reason = String(formData.get("reason") ?? "").trim();
  if (reason.length < 3) return { error: "Tuliskan alasan (minimal 3 karakter); alasan dicatat di log audit." };

  try {
    await adminApi.setPaused(sourceId, paused, reason);
  } catch (error) {
    if (error instanceof ApiError) return { error: error.message };
    throw error;
  }
  refresh();
  return { ok: paused ? "Sumber dijeda." : "Sumber dilanjutkan." };
}
