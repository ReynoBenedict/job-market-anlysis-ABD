import { randomBytes } from "node:crypto";
import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end journeys against a running stack: the API must be reachable at API_BASE_URL.
 * The web app is started automatically unless one is already listening on WEB_URL.
 *
 * With E2E_LOCAL_STACK=1 a second, self-contained stack is started for the @stack tests
 * (admin journeys and API outage/recovery): an API with a test-only admin token, a
 * toggleable proxy in front of it, and a production web server using test-only admin
 * credentials. The credentials are generated per run and exist only in this process tree.
 * Needs `npm run build` and the backend virtualenv; uses DATABASE_URL (default: local db).
 */
const webUrl = process.env.WEB_URL ?? "http://localhost:3001";
const localStack = process.env.E2E_LOCAL_STACK === "1";

// Set once in the main process; workers inherit the environment, so all agree.
process.env.E2E_ADMIN_USER ??= "e2e-admin";
process.env.E2E_ADMIN_PASSWORD ??= randomBytes(18).toString("base64url");
process.env.E2E_ADMIN_TOKEN ??= randomBytes(24).toString("base64url");

const STACK = { api: 8012, proxy: 8099, web: 3004 };
const backendDir = path.resolve(process.cwd(), "..", "backend");
const python = path.join(backendDir, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
const databaseUrl =
  process.env.DATABASE_URL ?? "postgresql+psycopg://talentscope:talentscope@localhost:5433/talentscope";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: { baseURL: webUrl, trace: "retain-on-failure", locale: "id-ID", timezoneId: "Asia/Jakarta" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, grepInvert: /@mobile|@stack/ },
    { name: "mobile", use: { ...devices["Pixel 7"] }, grep: /@mobile/ },
    ...(localStack
      ? [
          {
            name: "local-stack",
            use: { ...devices["Desktop Chrome"], baseURL: `http://localhost:${STACK.web}` },
            grep: /@stack/,
          },
        ]
      : []),
  ],
  webServer: [
    { command: "npm run start", url: webUrl, reuseExistingServer: true, timeout: 120_000 },
    ...(localStack
      ? [
          {
            command: `"${python}" -m uvicorn --factory talentscope.api.app:create_app --port ${STACK.api}`,
            cwd: backendDir,
            url: `http://127.0.0.1:${STACK.api}/api/v1/filters`,
            env: { DATABASE_URL: databaseUrl, ADMIN_API_TOKEN: process.env.E2E_ADMIN_TOKEN },
            reuseExistingServer: false,
            timeout: 60_000,
          },
          {
            command: "node e2e/support/toggle-proxy.mjs",
            port: STACK.proxy,
            env: { PORT: String(STACK.proxy), TARGET: `http://127.0.0.1:${STACK.api}` },
            reuseExistingServer: false,
          },
          {
            command: `npx next start -p ${STACK.web}`,
            url: `http://localhost:${STACK.web}`,
            env: {
              API_BASE_URL: `http://127.0.0.1:${STACK.proxy}`,
              ADMIN_USERNAME: process.env.E2E_ADMIN_USER,
              ADMIN_PASSWORD: process.env.E2E_ADMIN_PASSWORD,
              ADMIN_API_TOKEN: process.env.E2E_ADMIN_TOKEN,
            },
            reuseExistingServer: false,
            timeout: 120_000,
          },
        ]
      : []),
  ],
});
