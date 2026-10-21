/**
 * HTTP Basic credentials for the /admin pages, checked in proxy.ts and again inside
 * admin server actions. The API token used for admin API calls never reaches the browser.
 */

export type AdminAuthResult = "ok" | "disabled" | "unauthorized";

/** Constant-time string comparison that does not leak where the strings differ. */
function safeEqual(a: string, b: string): boolean {
  const left = new TextEncoder().encode(a);
  const right = new TextEncoder().encode(b);
  let diff = left.length ^ right.length;
  for (let i = 0; i < Math.max(left.length, right.length); i++) diff |= (left[i] ?? 0) ^ (right[i] ?? 0);
  return diff === 0;
}

export function checkAdminAuthorization(header: string | null, env: NodeJS.ProcessEnv = process.env): AdminAuthResult {
  const username = env.ADMIN_USERNAME;
  const password = env.ADMIN_PASSWORD;
  if (!username || !password || !env.ADMIN_API_TOKEN) return "disabled";
  if (!header?.startsWith("Basic ")) return "unauthorized";
  let decoded: string;
  try {
    decoded = atob(header.slice("Basic ".length));
  } catch {
    return "unauthorized";
  }
  const separator = decoded.indexOf(":");
  if (separator < 0) return "unauthorized";
  const userOk = safeEqual(decoded.slice(0, separator), username);
  const passOk = safeEqual(decoded.slice(separator + 1), password);
  return userOk && passOk ? "ok" : "unauthorized";
}
