import { expect, test } from "@playwright/test";

/**
 * Tests that need the self-contained stack from playwright.config.ts (E2E_LOCAL_STACK=1):
 * an API with a test-only admin token behind a toggleable proxy, and a web server with
 * test-only admin credentials.
 */
const PROXY = "http://127.0.0.1:8099";
const OUTAGE_TEXT = "Layanan data TalentScope sedang tidak tersedia";

test.describe("API outage and recovery @stack", () => {
  test.afterEach(async ({ request }) => {
    await request.post(`${PROXY}/__e2e/up`);
  });

  test("pages explain an outage, offer a retry, and recover when the API returns", async ({ page, request }) => {
    await request.post(`${PROXY}/__e2e/down`);

    await page.goto("/lowongan?q=admin");
    // (Next.js keeps an empty route-announcer alert on every page, so match by text.)
    const alert = page.getByRole("alert").filter({ hasText: OUTAGE_TEXT });
    await expect(alert).toBeVisible({ timeout: 15_000 });
    await expect(page.locator("[aria-busy=true]")).toHaveCount(0); // not stuck loading
    const retry = alert.getByRole("link", { name: "Coba lagi" });
    await expect(retry).toBeVisible();
    await expect(retry).toHaveAttribute("href", "/lowongan?q=admin"); // retries the same search

    await page.goto("/");
    await expect(page.getByText("Ringkasan data belum dapat dimuat")).toBeVisible();
    await expect(page.getByRole("searchbox", { name: /Cari posisi/ })).toBeVisible(); // search still usable

    await request.post(`${PROXY}/__e2e/up`);
    await page.goto("/lowongan?q=admin");
    await expect(page.getByTestId("result-summary")).toContainText(/lowongan/);
    await expect(page.getByRole("alert").filter({ hasText: OUTAGE_TEXT })).toHaveCount(0);
  });

  test("a job page during an outage shows the error state, not a false 404", async ({ page, request }) => {
    const jobs = await (await request.get(`${PROXY}/api/v1/jobs?page_size=1`)).json();
    const id: string = jobs.items[0].id;
    await request.post(`${PROXY}/__e2e/down`);
    const response = await page.goto(`/lowongan/${id}`);
    expect(response?.status()).toBe(200);
    await expect(page.getByRole("alert").filter({ hasText: OUTAGE_TEXT })).toBeVisible();
    await expect(page.getByRole("heading", { name: /tidak ditemukan/ })).toHaveCount(0);
  });
});

test.describe("admin workspace @stack", () => {
  test.use({
    httpCredentials: { username: process.env.E2E_ADMIN_USER ?? "", password: process.env.E2E_ADMIN_PASSWORD ?? "" },
  });

  test("wrong credentials are rejected", async ({ browser }) => {
    const context = await browser.newContext({ httpCredentials: { username: "e2e-admin", password: "salah" } });
    const response = await (await context.newPage()).goto("/admin");
    expect(response?.status()).toBe(401);
    await context.close();
  });

  test("pause and resume an approved source, with an audit trail", async ({ page }) => {
    // The audit log is append-only, so each run uses a reason it can find unambiguously.
    const runId = Date.now().toString(36);
    await page.goto("/admin");
    const row = page.getByRole("row", { name: /glints-snapshot-2026-06/ });
    await row.getByPlaceholder("Alasan (dicatat di audit)").fill(`uji e2e ${runId}: jeda`);
    await row.getByRole("button", { name: "Jeda" }).click();
    await expect(row.getByText("Sumber dijeda.")).toBeVisible();

    await row.getByPlaceholder("Alasan (dicatat di audit)").fill(`uji e2e ${runId}: lanjut`);
    await row.getByRole("button", { name: "Lanjutkan" }).click();
    await expect(row.getByText("Sumber dilanjutkan.")).toBeVisible();

    await page.getByRole("link", { name: "Audit Perubahan" }).click();
    await expect(page.getByRole("row", { name: new RegExp(`uji e2e ${runId}: lanjut`) })).toBeVisible();
  });

  test("blocked sources cannot be resumed from the UI", async ({ page }) => {
    await page.goto("/admin");
    const row = page.getByRole("row", { name: /^Glints Indonesia glints/ });
    await expect(row).toBeVisible();
    await expect(row.getByRole("button", { name: "Lanjutkan" })).toHaveCount(0);
  });

  test("run history and data quality reflect operational data", async ({ page }) => {
    await page.goto("/admin/riwayat");
    await expect(page.getByText("Berhasil").first()).toBeVisible();
    // A refused run (policy gate) is in the history; page through until it appears.
    let found = false;
    for (let pageNumber = 1; pageNumber <= 10 && !found; pageNumber++) {
      await page.goto(`/admin/riwayat?page=${pageNumber}`);
      found = (await page.getByText(/Diblokir kebijakan sumber/).count()) > 0;
    }
    expect(found).toBe(true);
    await page.goto("/admin/kualitas");
    await expect(page.getByText("TAGS_TRUNCATED")).toBeVisible();
  });
});
