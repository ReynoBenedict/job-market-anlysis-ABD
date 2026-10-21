import { type NextRequest, NextResponse } from "next/server";

import { checkAdminAuthorization } from "@/lib/admin-auth";

const JOB_DETAIL = /^\/lowongan\/([^/]+)\/?$/;
const MISSING_JOB_PATH = "/lowongan/tidak-ditemukan";

async function jobExists(id: string): Promise<boolean | null> {
  const base = process.env.API_BASE_URL?.replace(/\/$/, "");
  if (!base) return null;
  try {
    const response = await fetch(`${base}/api/v1/jobs/${encodeURIComponent(id)}`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(3_000),
    });
    if (response.status === 404 || response.status === 422) return false;
    return response.ok ? true : null;
  } catch {
    return null; // API unreachable: let the page render its own error state
  }
}

/**
 * A job page streams its content, so by the time the API says "no such job" a 200 status
 * has already been sent (and Next.js ignores a status on rewrites). For full page loads
 * of an unknown job, answer here with the prerendered not-found page and a real 404.
 * Client-side navigations (RSC requests) are left to the page's notFound().
 */
async function missingJobResponse(request: NextRequest, id: string): Promise<NextResponse | null> {
  const isDocument = !request.headers.get("rsc") && (request.headers.get("accept") ?? "").includes("text/html");
  if (!isDocument || id === MISSING_JOB_PATH.split("/").pop() || (await jobExists(id)) !== false) return null;
  const page = await fetch(new URL(MISSING_JOB_PATH, request.url), { headers: { Accept: "text/html" } });
  return new NextResponse(await page.text(), {
    status: 404,
    headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
  });
}

function adminGate(request: NextRequest): NextResponse {
  const result = checkAdminAuthorization(request.headers.get("authorization"));
  if (result === "ok") return NextResponse.next();
  if (result === "disabled") {
    return new NextResponse("Area admin dinonaktifkan pada deployment ini.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
  return new NextResponse("Autentikasi diperlukan.", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="TalentScope Admin", charset="UTF-8"',
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
}

export async function proxy(request: NextRequest) {
  const job = JOB_DETAIL.exec(request.nextUrl.pathname);
  if (job) return (await missingJobResponse(request, job[1])) ?? NextResponse.next();
  return adminGate(request);
}

export const config = {
  matcher: ["/admin", "/admin/:path*", "/lowongan/:id"],
};
