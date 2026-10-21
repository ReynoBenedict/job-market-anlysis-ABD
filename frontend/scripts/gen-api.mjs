// Regenerates src/lib/api-schema.ts from the running API's OpenAPI document.
// Plain Node so it behaves the same in PowerShell, cmd, and POSIX shells (npm scripts
// cannot expand ${VAR:-default} on Windows).
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const base = (process.env.API_BASE_URL ?? "http://localhost:8010").replace(/\/$/, "");
// The package's "exports" hide its CLI from require.resolve, so use the installed path.
const cli = fileURLToPath(new URL("../node_modules/openapi-typescript/bin/cli.js", import.meta.url));
const result = spawnSync(process.execPath, [cli, `${base}/api/openapi.json`, "-o", "src/lib/api-schema.ts"], {
  stdio: "inherit",
});
process.exit(result.status ?? 1);
