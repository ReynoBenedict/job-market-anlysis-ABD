import { expect, type APIRequestContext, type Page, test } from "@playwright/test";

/**
 * User journeys against a running stack. Expected numbers are read from the API at test
 * time, never hard-coded, so the suite stays valid when the dataset legitimately changes.
 */
const API = `${(process.env.API_BASE_URL ?? "http://localhost:8010").replace(/\/$/, "")}/api/v1`;

/** Parses "1.133" style Indonesian integers from visible text. */
function parseCount(text: string | null): number {
  return Number((text ?? "").replace(/\./g, ""));
}

async function resultTotal(page: Page): Promise<number> {
  const summary = page.getByTestId("result-summary");
  await expect(summary).toBeVisible();
  const match = (await summary.textContent())?.match(/^\s*([\d.]+)\s+lowongan/);
  return match ? parseCount(match[1]) : 0;
}

async function apiJson<T>(request: APIRequestContext, path: string): Promise<T> {
  const response = await request.get(`${API}${path}`);
  expect(response.ok(), `${path} -> HTTP ${response.status()}`).toBeTruthy();
  return (await response.json()) as T;
}

/** Waits until the URL matches and the page has finished re-rendering for it. */
async function settled(page: Page, url: RegExp) {
  await expect(page).toHaveURL(url);
  await expect(page.locator("[aria-busy=true]")).toHaveCount(0);
}

const filterGroup = (page: Page, title: string) =>
  page.getByRole("group", { name: title, exact: true });

test("journey 1: homepage statistics come from the API and search leads to results", async ({ page, request }) => {
  const overview = await apiJson<{ total_jobs: number }>(request, "/market/overview");
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Cari lowongan");
  await expect(page.getByText(`${overview.total_jobs.toLocaleString("id-ID")} lowongan tercatat`)).toBeVisible();

  await page.getByRole("searchbox", { name: /Cari posisi/ }).fill("  Admin  ");
  await page.getByRole("button", { name: "Cari Lowongan" }).click();
  await settled(page, /\/lowongan\?q=/);
  const jobs = await apiJson<{ total: number }>(request, "/jobs?q=admin&page_size=1");
  expect(await resultTotal(page)).toBe(jobs.total);
  await expect(page.locator("article").first()).toContainText(/admin/i);
});

test("journey 2: search, filters, sorting, and pagination stay consistent with the URL", async ({ page, request }) => {
  await page.goto("/lowongan?q=staff");
  const all = await resultTotal(page);

  const province = filterGroup(page, "Provinsi").getByRole("checkbox").first();
  const provinceName = (await province.locator("xpath=..").innerText()).split("\n")[0].trim();
  await province.check();
  await settled(page, /province=/);
  const byProvince = await resultTotal(page);
  expect(byProvince).toBeLessThanOrEqual(all);

  await filterGroup(page, "Status lowongan").getByRole("checkbox").first().check();
  await settled(page, /freshness=/);
  const url = new URL(page.url());
  expect(url.searchParams.get("q")).toBe("staff");
  const both = await resultTotal(page);
  expect(both).toBeLessThanOrEqual(byProvince);
  const api = await apiJson<{ total: number }>(request, `/jobs?${url.searchParams.toString()}&page_size=1`);
  expect(both).toBe(api.total);

  await page.getByRole("button", { name: `Hapus filter ${provinceName}` }).click();
  await settled(page, /^(?!.*province=).*freshness=/);

  await page.getByRole("button", { name: "Hapus semua filter" }).first().click();
  await settled(page, /\/lowongan\?q=staff$/);
  expect(await resultTotal(page)).toBe(all);

  await page.getByRole("combobox").first().selectOption("salary_desc");
  await settled(page, /sort=salary_desc/);
  await expect(page.locator("article").first()).toContainText(/Rp/);
  await page.getByRole("link", { name: /Berikutnya/ }).click();
  await settled(page, /page=2/);
  await expect(page.getByTestId("result-summary")).toContainText("menampilkan 21–40");
});

test("journey 3: a job detail matches the API, states its status, and returns to the results", async ({ page, request }) => {
  await page.goto("/lowongan?province=DKI+Jakarta");
  const firstLink = page.locator("article").first().getByRole("heading").getByRole("link");
  const href = (await firstLink.getAttribute("href")) ?? "";
  await firstLink.click();
  await expect(page).toHaveURL(/\/lowongan\/[0-9a-f-]{36}/);

  const id = href.match(/[0-9a-f-]{36}/)?.[0];
  const job = await apiJson<{ title: string; company_name: string | null; source_url: string | null; freshness: { code: string } }>(
    request,
    `/jobs/${id}`,
  );
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(job.title);
  if (job.company_name) await expect(page.getByText(job.company_name).first()).toBeVisible();
  await expect(page.getByText(job.freshness.code === "EXPIRED_BY_SOURCE" ? /Batas lamaran sudah lewat/ : "Belum tentu masih dibuka")).toBeVisible();
  await expect(page.getByText("Belum pernah")).toBeVisible(); // never re-checked live

  const original = page.getByRole("link", { name: /Buka halaman asli/ });
  if (job.source_url) {
    await expect(original).toHaveAttribute("href", job.source_url);
    await expect(original).toHaveAttribute("target", "_blank");
    await expect(original).toHaveAttribute("rel", /noopener/);
  } else {
    await expect(original).toHaveCount(0);
  }

  await page.getByRole("link", { name: "Kembali ke hasil pencarian" }).click();
  await settled(page, /\/lowongan\?province=DKI\+Jakarta/);
});

test("journey 4: saving and removing a job, persisted in this browser", async ({ page }) => {
  await page.goto("/lowongan");
  const firstCard = page.locator("article").first();
  const title = (await firstCard.getByRole("heading").textContent())?.trim() ?? "";
  await firstCard.getByRole("button", { name: /Simpan lowongan/ }).click();
  await expect(firstCard.getByRole("button", { name: /Hapus dari tersimpan/ })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("link", { name: /Tersimpan\s*1/ }).first()).toBeVisible();

  await page.getByRole("link", { name: /Tersimpan/ }).first().click();
  await expect(page.getByRole("link", { name: title })).toBeVisible();
  await expect(page.getByText(/Status saat disimpan/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole("link", { name: title })).toBeVisible();

  await page.getByRole("button", { name: `Hapus ${title} dari tersimpan` }).click();
  await expect(page.getByText("Belum ada lowongan tersimpan")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Belum ada lowongan tersimpan")).toBeVisible();
});

test("journey 5: salary figures follow the filters and sparse groups get no numbers", async ({ page, request }) => {
  await page.goto("/gaji");
  await expect(page.getByText("Gaji tengah yang dicantumkan")).toBeVisible();
  await expect(page.getByText(/\/bulan/).first()).toBeVisible();

  await filterGroup(page, "Provinsi").getByRole("checkbox").first().check();
  await settled(page, /province=/);
  await expect(page.getByText("Gaji tengah yang dicantumkan (sesuai filter)")).toBeVisible();
  const params = new URL(page.url()).searchParams;
  const salary = await apiJson<{ eligible: number }>(request, `/salaries/overview?${params.toString()}`);
  await expect(page.getByText(`Dihitung dari ${salary.eligible.toLocaleString("id-ID")} lowongan`)).toBeVisible();

  await page.getByRole("link", { name: "Pendidikan", exact: true }).click();
  await settled(page, /by=education/);
  const compare = await apiJson<{ groups: { median: number | null }[] }>(request, `/salaries/compare?${params.toString()}&by=education`);
  if (compare.groups.some((group) => group.median === null)) {
    await expect(page.getByText(/Statistik tidak ditampilkan: kurang dari/).first()).toBeVisible();
  }
  await page.getByRole("button", { name: "Tampilkan sebagai tabel" }).click();
  await expect(page.getByRole("columnheader", { name: "Rentang titik tengah" })).toBeVisible();
});

test("journey 6: market comparison numbers follow filters and bars open the matching jobs", async ({ page, request }) => {
  await page.goto("/pasar");
  await filterGroup(page, "Bidang pekerjaan").getByRole("checkbox").nth(1).check();
  await settled(page, /role_family=/);
  const params = new URL(page.url()).searchParams;
  const overview = await apiJson<{ total_jobs: number }>(request, `/market/overview?${params.toString()}`);
  const tile = page.locator(".card", { has: page.getByText("Lowongan", { exact: true }) }).first();
  await expect(tile).toContainText(overview.total_jobs.toLocaleString("id-ID"));

  await page.getByRole("list", { name: /per provinsi/ }).getByRole("link").first().click();
  await settled(page, /\/lowongan\?.*role_family=.*province=/);
  expect(await resultTotal(page)).toBeGreaterThan(0);
});

test("journey 7: sources and methodology are reachable and distinguish active from unused sources", async ({ page }) => {
  await page.goto("/sumber-data");
  await expect(page.getByRole("heading", { name: /Kumpulan data yang dipakai/ })).toBeVisible();
  await expect(page.getByText("Arsip web", { exact: true }).first()).toBeVisible();
  await page.locator("summary", { hasText: "Diblokir" }).click();
  await expect(page.locator("details[open]").getByText(/^Glints Indonesia/).first()).toBeVisible();

  await page.getByRole("link", { name: /Cara kami menghitung/ }).first().click();
  await settled(page, /\/metodologi/);
  await expect(page.getByRole("heading", { name: "Apakah lowongan masih dibuka?" })).toBeVisible();
  // Technical detail is available but collapsed by default.
  await expect(page.getByText(/Silhouette Score 0,0351/)).toBeHidden();
  await page.locator("#teknis").getByText("Rincian").click();
  await expect(page.getByText(/Silhouette Score 0,0351/)).toBeVisible();
});

test("journey 8: empty, invalid, and missing-record states explain what to do", async ({ page }) => {
  await page.goto("/lowongan?q=zzzqqqxxx");
  await expect(page.getByText("Tidak ada lowongan yang cocok").first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Mulai pencarian baru" })).toBeVisible();

  await page.goto("/lowongan?role_family=BUKAN_BIDANG");
  await expect(page.getByRole("alert").filter({ hasText: "Parameter pencarian tidak valid" })).toBeVisible();

  // A full page load of an unknown job answers with a real 404 (checked in proxy.ts).
  const missing = await page.goto("/lowongan/00000000-0000-0000-0000-000000000000");
  expect(missing?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: /tidak ditemukan/ })).toBeVisible();
});

test("journey 10: counts agree across the overview, filters, search, and sources", async ({ request }) => {
  const [overview, filters, jobs, sources] = await Promise.all([
    apiJson<{ total_jobs: number }>(request, "/market/overview"),
    apiJson<{ total: number; freshness: { count: number }[]; source: { count: number }[] }>(request, "/filters"),
    apiJson<{ total: number }>(request, "/jobs?page_size=1"),
    apiJson<{ job_count: number }[]>(request, "/sources/coverage"),
  ]);
  const sum = (items: { count?: number; job_count?: number }[]) =>
    items.reduce((total, item) => total + (item.count ?? item.job_count ?? 0), 0);
  expect(jobs.total).toBe(overview.total_jobs);
  expect(filters.total).toBe(overview.total_jobs);
  expect(sum(filters.freshness)).toBe(overview.total_jobs);
  expect(sum(filters.source)).toBe(overview.total_jobs);
  expect(sum(sources)).toBe(overview.total_jobs);
});

test("admin area requires authentication", async ({ request }) => {
  const response = await request.get("/admin");
  expect([401, 404]).toContain(response.status());
});

test("journey 9: navigation and filters work on a phone @mobile", async ({ page }) => {
  await page.goto("/ringkasan");
  await page.getByRole("button", { name: "Buka menu" }).click();
  await page.getByRole("navigation", { name: "Menu" }).getByRole("link", { name: "Gaji", exact: true }).click();
  await settled(page, /\/gaji/);
  await expect(page.getByRole("button", { name: "Buka menu" })).toBeVisible(); // menu closed itself

  await page.goto("/lowongan");
  await page.getByRole("button", { name: /^Filter/ }).click();
  await filterGroup(page, "Provinsi").getByRole("checkbox").first().check();
  await settled(page, /province=/);
  await page.getByRole("button", { name: /^Lihat [\d.]+ hasil$/ }).click();
  await expect(filterGroup(page, "Provinsi")).toBeHidden();
  await expect(page.locator("article").first()).toBeVisible();
});

test.describe("layout at every supported screen size @layout", () => {
  const SIZES = [
    [1440, 900],
    [1280, 720],
    [1024, 768],
    [768, 1024],
    [390, 844],
    [360, 800],
  ] as const;
  const PAGES = ["/", "/lowongan", "/gaji", "/ringkasan", "/pasar", "/keterampilan", "/sumber-data", "/metodologi", "/tersimpan"];

  for (const [width, height] of SIZES) {
    test(`no horizontal overflow at ${width}×${height}`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      for (const path of PAGES) {
        await page.goto(path);
        await expect(page.locator("[aria-busy=true]")).toHaveCount(0);
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
        expect(overflow, `${path} overflows by ${overflow}px`).toBeLessThanOrEqual(0);
        // Primary navigation is reachable: inline links on wide screens, a menu button otherwise.
        const menuButton = page.getByRole("button", { name: "Buka menu" });
        if (width < 1024) await expect(menuButton).toBeVisible();
        else await expect(page.getByRole("navigation", { name: "Navigasi utama" })).toBeVisible();
      }
    });
  }
});

// ---------------------------------------------------------------------------------------
// Interaction and URL-state journeys (docs/QA/INTERACTION_MATRIX.md lists what each covers).
// ---------------------------------------------------------------------------------------

const idPercent = new Intl.NumberFormat("id-ID", { style: "percent", maximumFractionDigits: 1 });
const idNumber = (value: number) => value.toLocaleString("id-ID");

interface JobPage {
  total: number;
  items: { id: string; title: string; company_name: string | null; source_url: string | null }[];
}

async function apiTotal(request: APIRequestContext, search: string): Promise<number> {
  return (await apiJson<JobPage>(request, `/jobs?${search}${search ? "&" : ""}page_size=1`)).total;
}

/** The URL's own query string, so the API is asked exactly what the page asked. */
function searchOf(page: Page): string {
  return new URL(page.url()).searchParams.toString();
}

const searchBox = (page: Page) => page.getByRole("searchbox", { name: /Cari posisi/ });
const invalidAlert = (page: Page) => page.getByRole("alert").filter({ hasText: "Parameter pencarian tidak valid" });

test("journey A: search by part of an employer name, any case and spacing, matches the API", async ({ page, request }) => {
  const sample = await apiJson<JobPage>(request, "/jobs?page_size=50");
  const company = sample.items.map((job) => job.company_name ?? "").find((name) => /[A-Za-z]{6,}/.test(name));
  test.skip(!company, "no listing with a company name");
  const word = company!.match(/[A-Za-z]{6,}/)![0];
  const partial = word.slice(1, 6);

  await page.goto("/lowongan");
  await searchBox(page).fill(`   ${partial.toUpperCase()}   `);
  await searchBox(page).press("Enter");
  await settled(page, new RegExp(`q=${partial.toUpperCase()}(&|$)`)); // trimmed before it reaches the URL
  const expected = await apiTotal(request, `q=${encodeURIComponent(partial.toLowerCase())}`);
  expect(expected).toBeGreaterThan(0);
  expect(await resultTotal(page)).toBe(expected);
  await expect(page.getByRole("button", { name: `Hapus filter “${partial.toUpperCase()}”` })).toBeVisible();

  // Multi-word: every word must match somewhere.
  await page.goto(`/lowongan?q=${encodeURIComponent("staff admin")}`);
  expect(await resultTotal(page)).toBe(await apiTotal(request, "q=staff+admin"));
});

test("journey A2: special characters, unicode, and length limits in search", async ({ page, request }) => {
  for (const q of ["%", "_", "\\", "'", '"', "é", "😀", "<script>"]) {
    await page.goto(`/lowongan?q=${encodeURIComponent(q)}`);
    const expected = await apiTotal(request, `q=${encodeURIComponent(q)}`);
    await expect(page.getByTestId("result-summary"), `q=${q}`).toBeVisible();
    expect(await resultTotal(page), `q=${q}`).toBe(expected);
    await expect(searchBox(page)).toHaveValue(q); // shown back verbatim, not interpreted
  }

  await page.goto("/lowongan");
  await expect(searchBox(page)).toHaveAttribute("maxlength", "100"); // the API's limit
  await searchBox(page).fill("a".repeat(150));
  await expect(searchBox(page)).toHaveValue("a".repeat(100));

  // A longer keyword from an edited link is explained, not a crash or a silent cut.
  await page.goto(`/lowongan?q=${"a".repeat(101)}`);
  await expect(invalidAlert(page)).toBeVisible();
  await expect(page.locator("[aria-busy=true]")).toHaveCount(0);
});

test("journey B: several filters combine (OR within a group, AND across) and chips remove one at a time", async ({ page, request }) => {
  await page.goto("/lowongan");
  const provinces = filterGroup(page, "Provinsi").getByRole("checkbox");
  await provinces.nth(0).check();
  await settled(page, /province=/);
  await provinces.nth(1).check();
  await settled(page, /province=.*province=/);
  const twoProvinces = await resultTotal(page);
  expect(twoProvinces).toBe(await apiTotal(request, searchOf(page)));

  await filterGroup(page, "Jenis pekerjaan").getByRole("checkbox").first().check();
  await settled(page, /employment_type=/);
  await filterGroup(page, "Pendidikan minimum").getByRole("checkbox").first().check();
  await settled(page, /education=/);
  const combined = await resultTotal(page);
  expect(combined).toBe(await apiTotal(request, searchOf(page)));
  expect(combined).toBeLessThanOrEqual(twoProvinces);

  // Removing one chip (the last one: education) keeps every other filter.
  const before = new URL(page.url()).searchParams;
  await page.locator("button[aria-label^='Hapus filter']").last().click();
  await settled(page, /^(?!.*education=)/);
  const after = new URL(page.url()).searchParams;
  expect(after.getAll("province")).toEqual(before.getAll("province"));
  expect(after.get("employment_type")).toBe(before.get("employment_type"));
  expect(after.get("education")).toBeNull();
  expect(await resultTotal(page)).toBe(await apiTotal(request, searchOf(page)));

  // Clear all keeps the chosen sort order (a view setting, not a filter).
  await page.getByRole("combobox").first().selectOption("title");
  await settled(page, /sort=title/);
  await page.getByRole("button", { name: "Hapus semua filter" }).click();
  await settled(page, /\/lowongan\?sort=title$/);
  expect(await resultTotal(page)).toBe(await apiTotal(request, ""));
});

test("journey B2: salary bounds — min only, max only, invalid input, min above max, and chip removal", async ({ page, request }) => {
  await page.goto("/lowongan");
  const min = page.getByLabel("Gaji minimum (juta rupiah)");
  const max = page.getByLabel("Gaji maksimum (juta rupiah)");
  const apply = page.getByRole("button", { name: "Terapkan" });

  await min.fill("7,5");
  await apply.click();
  await settled(page, /\?salary_min=7500000$/);
  expect(await resultTotal(page)).toBe(await apiTotal(request, "salary_min=7500000"));
  const chip = page.getByRole("button", { name: "Hapus filter Gaji ≥ Rp 7,5 jt" });
  await expect(chip).toBeVisible();

  // Removing the chip also empties the box (it used to keep showing the old bound).
  await chip.click();
  await settled(page, /\/lowongan$/);
  await expect(min).toHaveValue("");
  // Back restores the bound in the URL and in the box.
  await page.goBack();
  await settled(page, /\?salary_min=7500000$/);
  await expect(min).toHaveValue("7,5");
  await page.goto("/lowongan");

  await max.fill("4");
  await apply.click();
  await settled(page, /\?salary_max=4000000$/);
  expect(await resultTotal(page)).toBe(await apiTotal(request, "salary_max=4000000"));

  await min.fill("abc");
  await apply.click();
  await expect(page.getByRole("alert").filter({ hasText: "Masukkan angka 0 sampai 10.000" })).toBeVisible();
  await min.fill("8");
  await apply.click();
  await expect(page.getByRole("alert").filter({ hasText: "Batas bawah tidak boleh melebihi batas atas" })).toBeVisible();
  await min.fill("99999");
  await apply.click();
  await expect(page.getByRole("alert").filter({ hasText: "Masukkan angka 0 sampai 10.000" })).toBeVisible();
  await expect(page).toHaveURL(/\?salary_max=4000000$/); // nothing was applied

  // The same mistake in an edited link is explained by the page; retry resets the search.
  await page.goto("/lowongan?salary_min=9000000&salary_max=1000000");
  await expect(invalidAlert(page)).toBeVisible();
  await expect(invalidAlert(page).getByRole("link", { name: "Coba lagi" })).toHaveAttribute("href", "/lowongan");
});

test("journey C: Back/Forward, reload, and history entries follow the URL", async ({ page, request }) => {
  await page.goto("/lowongan");
  const all = await resultTotal(page);
  const startLength = await page.evaluate(() => history.length);
  const province = filterGroup(page, "Provinsi").getByRole("checkbox").first();
  await province.check();
  await settled(page, /province=/);
  const status = filterGroup(page, "Status lowongan").getByRole("checkbox").first();
  await status.check();
  await settled(page, /province=.*freshness=/);
  const both = await resultTotal(page);
  expect(await page.evaluate(() => history.length)).toBe(startLength + 2); // one entry per change

  await page.goBack();
  await settled(page, /province=(?!.*freshness=)/);
  await expect(status).not.toBeChecked();
  await expect(province).toBeChecked();
  expect(await resultTotal(page)).toBe(await apiTotal(request, searchOf(page)));
  await page.goBack();
  await settled(page, /\/lowongan$/);
  await expect(province).not.toBeChecked();
  expect(await resultTotal(page)).toBe(all);
  await page.goForward();
  await settled(page, /province=(?!.*freshness=)/);
  await page.goForward();
  await settled(page, /province=.*freshness=/);
  expect(await resultTotal(page)).toBe(both);

  // Reload shows the same state.
  await page.reload();
  await expect(province).toBeChecked();
  await expect(status).toBeChecked();
  expect(await resultTotal(page)).toBe(both);

  // Search submission is its own entry; Back restores the previous keyword in the box.
  await page.goto("/lowongan?q=admin");
  await searchBox(page).fill("staff");
  await searchBox(page).press("Enter");
  await settled(page, /q=staff/);
  await page.goBack();
  await settled(page, /q=admin$/);
  await expect(searchBox(page)).toHaveValue("admin");
  expect(await resultTotal(page)).toBe(await apiTotal(request, "q=admin"));
});

test("journey C2: a detail page links back to the exact results page, never off-site", async ({ page }) => {
  await page.goto("/lowongan?q=staff&sort=title&page=2");
  await expect(page.getByTestId("result-summary")).toContainText("menampilkan 21–");
  const firstLink = page.locator("article").first().getByRole("heading").getByRole("link");
  const id = (await firstLink.getAttribute("href"))!.match(/[0-9a-f-]{36}/)![0];
  await firstLink.click();
  await expect(page).toHaveURL(/\/lowongan\/[0-9a-f-]{36}\?kembali=/);
  const back = page.getByRole("link", { name: "Kembali ke hasil pencarian" });
  await expect(back).toHaveAttribute("href", "/lowongan?q=staff&sort=title&page=2");
  await back.click();
  await settled(page, /\/lowongan\?q=staff&sort=title&page=2$/);
  await expect(page.getByTestId("result-summary")).toContainText("menampilkan 21–");

  for (const hostile of ["//evil.example", "https://evil.example", "javascript:alert(1)", "%2F%2Fevil.example"]) {
    await page.goto(`/lowongan/${id}?kembali=${hostile}`);
    await expect(page.getByRole("link", { name: "Kembali ke hasil pencarian" })).toHaveAttribute("href", "/lowongan");
  }
});

test("journey D: detail page states dates honestly and handles a missing source link", async ({ page, request }) => {
  interface Detail {
    id: string;
    source_url: string | null;
    expires_at: string | null;
    quality_flags: string[];
  }
  // A listing without a stored original link (snapshot sources do not keep one).
  let detail: Detail | null = null;
  const sources = await apiJson<{ source: { value: string }[] }>(request, "/filters");
  for (const source of sources.source) {
    const jobs = await apiJson<JobPage>(request, `/jobs?source=${encodeURIComponent(source.value)}&page_size=50`);
    const job = jobs.items.find((item) => !item.source_url);
    if (job) {
      detail = await apiJson<Detail>(request, `/jobs/${job.id}`);
      break;
    }
  }
  test.skip(!detail, "every listing has a source link");
  await page.goto(`/lowongan/${detail!.id}`);
  await expect(page.getByRole("link", { name: /Buka halaman asli/ })).toHaveCount(0);
  await expect(page.getByText("Tautan asli tidak tersimpan untuk sumber ini.")).toBeVisible();
  await expect(page.getByText("Belum pernah")).toBeVisible();
  const deadline = page.locator("dt", { hasText: "Batas lamaran" }).locator("xpath=following-sibling::dd[1]");
  if (detail!.expires_at) {
    const date = new Date(detail!.expires_at).toLocaleDateString("id-ID", { dateStyle: "long", timeZone: "Asia/Jakarta" });
    await expect(deadline).toHaveText(date);
  } else {
    await expect(deadline).toHaveText("Tidak diketahui"); // never a made-up date
  }
  if (detail!.quality_flags.length) await expect(page.getByRole("heading", { name: "Catatan kualitas data" })).toBeVisible();

  // Malformed IDs are a real 404, not an error page.
  for (const bad of ["not-a-uuid", "12345", "%27%20OR%201%3D1"]) {
    const response = await page.goto(`/lowongan/${bad}`);
    expect(response?.status(), bad).toBe(404);
    await expect(page.getByRole("heading", { name: /tidak ditemukan/ })).toBeVisible();
  }
});

test("journey E: a saved job whose record is gone can be removed from the not-found page", async ({ page }) => {
  const id = crypto.randomUUID();
  await page.goto("/tersimpan");
  await page.evaluate((jobId) => {
    localStorage.setItem(
      "talentscope:saved-jobs:v1",
      JSON.stringify([{ id: jobId, title: "Lowongan Lama Uji", company: "PT Uji", location: null, savedAt: new Date().toISOString() }]),
    );
  }, id);
  await page.reload();
  await expect(page.getByRole("link", { name: /Tersimpan\s*1/ }).first()).toBeVisible();

  // Client-side navigation from the saved list.
  await page.getByRole("link", { name: "Lowongan Lama Uji" }).click();
  await expect(page.getByRole("heading", { name: /tidak ditemukan/ })).toBeVisible();
  await expect(page.getByText("Lowongan ini ada di daftar tersimpanmu")).toBeVisible();

  // A full page load (proxy 404) shows the same way out.
  const response = await page.goto(`/lowongan/${id}`);
  expect(response?.status()).toBe(404);
  await expect(page.getByText("Lowongan ini ada di daftar tersimpanmu")).toBeVisible();
  await page.getByRole("button", { name: "Hapus dari tersimpan" }).click();
  await expect(page.getByRole("status").filter({ hasText: "sudah dihapus dari daftar tersimpan" })).toBeVisible();
  await page.getByRole("link", { name: "Lihat lowongan tersimpan" }).click();
  await expect(page.getByText("Belum ada lowongan tersimpan")).toBeVisible();
});

test("journey E2: blocked browser storage is explained, not shown as an empty list", async ({ page }) => {
  await page.addInitScript(() => {
    const blocked = () => {
      throw new DOMException("The operation is insecure.", "SecurityError");
    };
    Storage.prototype.getItem = blocked;
    Storage.prototype.setItem = blocked;
  });
  await page.goto("/tersimpan");
  await expect(page.getByText("Browser ini tidak mengizinkan penyimpanan")).toBeVisible();
  await page.goto("/lowongan");
  await page.locator("article").first().getByRole("button", { name: /Simpan lowongan/ }).click();
  await expect(page.getByText("Browser menolak menyimpan data.").first()).toBeVisible();
});

test("journey F: salary chart, table, and comparison follow the API for each grouping and filter", async ({ page, request }) => {
  interface Compare {
    groups: { key: string | null; label: string; n: number; median: number | null }[];
  }
  interface Overview {
    eligible: number;
    histogram: { lower: number; upper: number | null; count: number }[];
  }
  const quartileRows = page.locator("section", { has: page.getByRole("heading", { name: /^Bandingkan per/ }) }).locator("ul > li");

  for (const [tab, by] of [
    ["Jenis pekerjaan", "employment_type"],
    ["Bidang", "role_family"],
  ] as const) {
    await page.goto("/gaji?by=education");
    await page.getByRole("link", { name: tab, exact: true }).click();
    await settled(page, new RegExp(`by=${by}`));
    const compare = await apiJson<Compare>(request, `/salaries/compare?by=${by}&limit=20`);
    await expect(quartileRows).toHaveCount(compare.groups.length);
    for (const [index, group] of compare.groups.entries()) {
      await expect(quartileRows.nth(index)).toContainText(group.label);
      await expect(quartileRows.nth(index)).toContainText(`n = ${idNumber(group.n)}`);
    }
  }

  // Recalculated for a province; the tab survives the filter change.
  await filterGroup(page, "Provinsi").getByRole("checkbox").first().check();
  await settled(page, /province=/);
  expect(new URL(page.url()).searchParams.get("by")).toBe("role_family");
  const params = new URLSearchParams(searchOf(page));
  params.delete("by");
  const compare = await apiJson<Compare>(request, `/salaries/compare?${params}&by=role_family&limit=20`);
  await expect(quartileRows).toHaveCount(compare.groups.length);
  await expect(quartileRows.first()).toContainText(`n = ${idNumber(compare.groups[0].n)}`);
  const overview = await apiJson<Overview>(request, `/salaries/overview?${params}`);
  await expect(page.getByText(`Dihitung dari ${idNumber(overview.eligible)} lowongan`)).toBeVisible();

  // Histogram bars and the table view show the same counts as the API.
  if (overview.histogram.length) {
    await page.getByRole("button", { name: "Tampilkan sebagai tabel" }).click();
    const rows = page.locator("table", { has: page.getByRole("columnheader", { name: "Rentang titik tengah" }) }).locator("tbody tr");
    await expect(rows).toHaveCount(overview.histogram.length);
    const bars = page.locator("svg rect[role=img]");
    await expect(bars).toHaveCount(overview.histogram.length);
    for (const [index, bin] of overview.histogram.entries()) {
      await expect(rows.nth(index).locator("td").last()).toHaveText(idNumber(bin.count));
      expect(await bars.nth(index).getAttribute("aria-label")).toMatch(new RegExp(`: ${idNumber(bin.count).replace(/\./g, "\\.")} lowongan$`));
    }
  }

  // A group drills down to matching jobs; the comparison tab does not leak into the search.
  const linked = compare.groups.find((group) => group.key);
  if (linked) {
    await quartileRows.getByRole("link", { name: linked.label, exact: true }).click();
    await settled(page, /\/lowongan\?/);
    const url = new URL(page.url());
    expect(url.searchParams.get("by")).toBeNull();
    expect(url.searchParams.get("salary_disclosed")).toBe("true");
    expect(url.searchParams.getAll("role_family")).toEqual([linked.key]);
    const total = await resultTotal(page);
    expect(total).toBe(await apiTotal(request, url.searchParams.toString()));
    expect(total).toBeGreaterThanOrEqual(linked.n); // n counts only usable monthly rupiah salaries
  }

  // Clearing filters keeps the comparison tab.
  await page.goto(`/gaji?by=education&${params}`);
  await page.getByRole("button", { name: "Hapus semua filter" }).click();
  await settled(page, /\/gaji\?by=education$/);
});

test("journey G: market counts and percentages match the API, and bars open matching searches", async ({ page, request }) => {
  interface Breakdown {
    rows: { key: string | null; label: string; count: number; share: number }[];
  }
  const overview = await apiJson<{ total_jobs: number; salary_disclosed: number; salary_disclosed_share: number }>(
    request,
    "/market/overview",
  );
  await page.goto("/ringkasan");
  const tile = (label: string) => page.locator(".card", { has: page.getByText(label, { exact: true }) }).first();
  await expect(tile("Lowongan tercatat")).toContainText(idNumber(overview.total_jobs));
  await expect(tile("Mencantumkan gaji")).toContainText(idPercent.format(overview.salary_disclosed_share));
  await expect(tile("Mencantumkan gaji")).toContainText(`${idNumber(overview.salary_disclosed)} lowongan`);

  const roles = await apiJson<Breakdown>(request, "/market/breakdown/role_family?limit=10");
  const list = page.getByRole("list", { name: "Jumlah lowongan per bidang pekerjaan" });
  await expect(list.getByRole("listitem")).toHaveCount(roles.rows.length);
  for (const [index, row] of roles.rows.entries()) {
    const item = list.getByRole("listitem").nth(index);
    await expect(item).toContainText(row.label);
    await expect(item).toContainText(idNumber(row.count));
    await expect(item).toContainText(idPercent.format(row.share));
  }

  // City bar on the comparison page → the search shows exactly that many jobs.
  await page.goto("/pasar");
  const cities = await apiJson<Breakdown>(request, "/market/breakdown/city?limit=8");
  const city = cities.rows.find((row) => row.key)!;
  await page.getByRole("list", { name: /per kota/ }).getByRole("link", { name: new RegExp(`^${city.label}`) }).first().click();
  await settled(page, /\/lowongan\?city=/);
  expect(await resultTotal(page)).toBe(city.count);
});

test("journey H: skills category switching and tag links lead to the matching search", async ({ page, request }) => {
  interface Tags {
    total_jobs: number;
    role_families: { value: string; label: string }[];
    top_tags: { value: string; label: string; count: number }[];
  }
  const all = await apiJson<Tags>(request, "/skills/source-tags?limit=15");
  test.skip(!all.role_families.length, "no tagged listings");
  await page.goto("/keterampilan");
  await expect(page.getByText(`n = ${idNumber(all.total_jobs)} lowongan`)).toBeVisible();

  const role = all.role_families[0];
  const nav = page.getByRole("navigation", { name: "Pilih bidang" });
  await nav.getByRole("link", { name: role.label, exact: true }).click();
  await settled(page, new RegExp(`role_family=${role.value}`));
  const filtered = await apiJson<Tags>(request, `/skills/source-tags?role_family=${role.value}&limit=15`);
  await expect(page.getByText(`n = ${idNumber(filtered.total_jobs)} lowongan`)).toBeVisible();
  await expect(nav.getByRole("link", { name: role.label, exact: true })).toHaveAttribute("aria-current", "page");

  const tag = filtered.top_tags[0];
  test.skip(!tag, "no visible tags for this role family");
  await page.getByRole("list", { name: /Frekuensi tag/ }).getByRole("link").first().click();
  // The link filters on the exact tag within the selected field, so it opens exactly the
  // listings the page counted for that tag.
  await settled(page, /\/lowongan\?tag=/);
  const params = new URL(page.url()).searchParams;
  expect(params.get("tag")).toBe(tag.value);
  expect(params.get("role_family")).toBe(role.value);
  expect(await resultTotal(page)).toBe(tag.count);
});

// Fixed: tag links use the exact `tag` filter (formerly a free-text `q` search across sources).
test("journey H2: a tag link opens exactly the listings counted for that tag", async ({ page, request }) => {
  const tags = await apiJson<{ top_tags: { value: string; count: number }[] }>(request, "/skills/source-tags?limit=15");
  for (const [index, tag] of tags.top_tags.entries()) {
    await page.goto("/keterampilan");
    await page.getByRole("list", { name: /Frekuensi tag/ }).getByRole("link").nth(index).click();
    await settled(page, /\/lowongan\?/);
    expect(await resultTotal(page), tag.value).toBe(tag.count);
  }
});

test("journey I: invalid parameters fall back or explain themselves", async ({ page, request }) => {
  await page.goto("/lowongan?sort=bogus");
  expect(await resultTotal(page)).toBe(await apiTotal(request, ""));
  await expect(page.getByRole("combobox").first()).toHaveValue("newest");

  await page.goto("/lowongan?sort=relevance"); // relevance needs a keyword
  await expect(page.getByRole("combobox").first()).toHaveValue("newest");

  await page.goto("/lowongan?page=99999");
  await expect(page.getByText("Halaman ini tidak ada")).toBeVisible();

  await page.goto("/lowongan?q=admin&sort=relevance&province=DKI+Jakarta");
  await page.getByRole("button", { name: "Hapus filter “admin”" }).click();
  await settled(page, /\/lowongan\?province=DKI\+Jakarta$/); // keyword-only sort removed with it
  await expect(searchBox(page)).toHaveValue("");

  await page.goto("/pasar?role_family=NOPE");
  await expect(invalidAlert(page)).toBeVisible();
  await page.goto("/gaji?province=Provinsi+Fiktif");
  await expect(page.getByText(/Belum cukup data/)).toBeVisible();
});

test("journey J: every route renders without console errors, page errors, or failed requests", async ({ page }) => {
  const problems: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") problems.push(`${page.url()} console: ${message.text()}`);
  });
  page.on("pageerror", (error) => problems.push(`${page.url()} pageerror: ${error.message}`));
  page.on("requestfailed", (request) => {
    // Prefetches cancelled by the next navigation are not failures.
    if (request.failure()?.errorText !== "net::ERR_ABORTED") problems.push(`${request.url()} failed: ${request.failure()?.errorText}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) problems.push(`${response.url()} HTTP ${response.status()}`);
  });
  const routes = [
    "/",
    "/lowongan",
    "/lowongan?q=admin&province=DKI+Jakarta&sort=salary_desc&page=2",
    "/gaji",
    "/gaji?by=province&employment_type=FULL_TIME",
    "/ringkasan",
    "/pasar",
    "/pasar?role_family=SOFTWARE_ENGINEERING",
    "/keterampilan",
    "/sumber-data",
    "/metodologi",
    "/tersimpan",
  ];
  for (const route of routes) {
    await page.goto(route);
    await expect(page.locator("[aria-busy=true]")).toHaveCount(0); // no indefinite loading
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  }
  await page.goto("/lowongan");
  await page.locator("article").first().getByRole("heading").getByRole("link").click();
  await expect(page).toHaveURL(/\/lowongan\/[0-9a-f-]{36}/);
  await expect(page.getByRole("link", { name: "Kembali ke hasil pencarian" })).toBeVisible();

  // Footer links all resolve.
  for (const href of await page.locator("footer a").evaluateAll((links) => links.map((link) => link.getAttribute("href") ?? ""))) {
    const response = await page.request.get(href.split("#")[0] || "/");
    expect(response.status(), href).toBe(200);
  }
  expect(problems).toEqual([]);
});

test("journey K: search, detail, back, and save on a phone @mobile", async ({ page }) => {
  await page.goto("/lowongan?q=admin");
  const first = page.locator("article").first();
  const title = (await first.getByRole("heading").textContent())?.trim() ?? "";
  await first.getByRole("heading").getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
  await page.getByRole("button", { name: "Simpan", exact: true }).click();
  await expect(page.getByRole("button", { name: "Tersimpan", exact: true })).toHaveAttribute("aria-pressed", "true");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
  await page.getByRole("link", { name: "Kembali ke hasil pencarian" }).click();
  await settled(page, /\/lowongan\?q=admin$/);
  await expect(searchBox(page)).toHaveValue("admin");
});

test("journey D2: an implausible disclosed salary is not presented as a salary", async ({ page, request }) => {
  interface Salary { status: { code: string }; currency: string | null; period: { code: string }; min: number | null; max: number | null; comparable: boolean }
  let id: string | null = null;
  for (let pageNumber = 1; pageNumber <= 60 && !id; pageNumber++) {
    const jobs = await apiJson<{ total_pages: number; items: { id: string; salary: Salary }[] }>(
      request,
      `/jobs?salary_disclosed=true&page_size=50&page=${pageNumber}`,
    );
    id = jobs.items.find(({ salary }) => !salary.comparable && salary.currency === "IDR" && salary.period.code === "MONTH" && salary.min !== null)?.id ?? null;
    if (pageNumber >= jobs.total_pages) break;
  }
  test.skip(!id, "no implausible monthly rupiah salary in the data");
  await page.goto(`/lowongan/${id}`);
  await expect(page.getByText("Gaji tidak tersedia.")).toBeVisible();
  await expect(page.getByText(/tidak wajar untuk gaji bulanan/)).toBeVisible();
  await expect(page.getByText("Gaji yang dicantumkan")).toHaveCount(0);
});
