import { describe, expect, it } from "vitest";

import { niceTicks } from "@/components/charts/histogram";
import { pageWindow } from "@/components/explorer/pagination";

import { checkAdminAuthorization } from "./admin-auth";
import { ApiError, retryHref, toSearchParams } from "./api";
import { jobsHref, resultsHref } from "./drilldown";
import {
  clearFilters,
  countActiveFilters,
  millionsToRupiah,
  readFilters,
  rupiahToMillions,
  serializeFilters,
  toggleValue,
  withoutKeyword,
} from "./filters";
import { formatNumber, formatPercent, formatRupiah, formatRupiahRange, formatRupiahShort } from "./format";

describe("Indonesian formatting", () => {
  it("uses Indonesian separators", () => {
    expect(formatNumber(1133)).toBe("1.133");
    expect(formatPercent(0.7572)).toBe("75,7%");
  });

  it("formats rupiah amounts", () => {
    expect(formatRupiah(5_500_000)).toBe("Rp 5.500.000");
    expect(formatRupiahShort(5_500_000)).toBe("Rp 5,5 jt");
    expect(formatRupiahShort(750_000)).toBe("Rp 750 rb");
    expect(formatRupiahRange(2_500_000, 2_500_000)).toBe("Rp 2.500.000");
    expect(formatRupiahRange(null, 1)).toBeNull();
  });
});

describe("URL filter state", () => {
  it("keeps known filters only and normalizes single/multi values", () => {
    const query = readFilters(
      { q: "data", province: ["DKI Jakarta", "Bali"], role_family: "DATA_ANALYTICS", evil: "x", page: "3" },
      ["page"],
    );
    expect(query).toEqual({ q: "data", province: ["DKI Jakarta", "Bali"], role_family: ["DATA_ANALYTICS"], page: "3" });
    expect(countActiveFilters(query)).toBe(4);
  });

  it("toggling a value resets pagination", () => {
    const next = toggleValue({ province: ["Bali"], page: "4" }, "province", "Bali");
    expect(next).toEqual({ province: undefined });
    expect(toggleValue({}, "city", "Bandung")).toEqual({ city: ["Bandung"] });
  });

  it("serializes repeated parameters", () => {
    expect(serializeFilters({ province: ["Bali", "Banten"], q: "qa engineer" })).toBe(
      "province=Bali&province=Banten&q=qa+engineer",
    );
  });

  it("converts salary bounds typed in millions", () => {
    expect(millionsToRupiah("7,5")).toBe("7500000");
    expect(millionsToRupiah("abc")).toBeUndefined();
    expect(millionsToRupiah("-1")).toBeUndefined();
    expect(rupiahToMillions("7500000")).toBe("7,5");
  });

  it("rejects salary input the API would refuse or that is ambiguous", () => {
    expect(millionsToRupiah(" 7.5 ")).toBe("7500000");
    expect(millionsToRupiah("0")).toBe("0");
    expect(millionsToRupiah("10000")).toBe("10000000000"); // the API's upper bound
    expect(millionsToRupiah("10001")).toBeUndefined();
    expect(millionsToRupiah("1e3")).toBeUndefined();
    expect(millionsToRupiah("7,5,3")).toBeUndefined();
    expect(millionsToRupiah("")).toBeUndefined();
  });

  it("removing the keyword also drops the keyword-only sort order", () => {
    expect(withoutKeyword({ q: "data", sort: "relevance", page: "3", province: ["Bali"] })).toEqual({
      q: undefined,
      sort: undefined,
      province: ["Bali"],
    });
    expect(withoutKeyword({ q: "data", sort: "salary_desc" }).sort).toBe("salary_desc");
  });

  it("clearing filters keeps the keyword, sort order, and comparison tab", () => {
    expect(
      clearFilters({ q: "data", sort: "title", by: "province", page: "2", province: ["Bali"], salary_min: "5000000" }),
    ).toEqual({ q: "data", sort: "title", by: "province" });
    expect(clearFilters({ city: ["Bandung"] })).toEqual({});
  });

  it("links back to the results with every search parameter and never off-site", () => {
    expect(resultsHref("q=admin&province=DKI+Jakarta&sort=salary_desc&page=2")).toBe(
      "/lowongan?province=DKI+Jakarta&q=admin&sort=salary_desc&page=2",
    );
    expect(resultsHref("?province=Bali&province=Banten")).toBe("/lowongan?province=Bali&province=Banten");
    for (const hostile of ["//evil.com", "https://evil.com", "\\evil.com", "javascript:alert(1)", "/../x", "\r\nLocation: x"]) {
      expect(resultsHref(hostile)).toBe("/lowongan");
    }
    expect(resultsHref(["q=a", "q=b"])).toBe("/lowongan");
    expect(resultsHref(undefined)).toBe("/lowongan");
  });

  it("retries the same view unless the parameters themselves were invalid", () => {
    expect(retryHref(new ApiError(503, "api_unreachable", ""), "/lowongan", "q=admin")).toBe("/lowongan?q=admin");
    expect(retryHref(new ApiError(422, "invalid_request", ""), "/lowongan", "sort=x")).toBe("/lowongan");
    expect(retryHref(new ApiError(500, "http_error", ""), "/gaji")).toBe("/gaji");
  });

  it("builds drill-down links that keep filters and drop pagination", () => {
    expect(jobsHref({ q: "data", page: "2" }, "province", "Bali")).toBe("/lowongan?q=data&province=Bali");
    expect(jobsHref({})).toBe("/lowongan");
    // The salary page's comparison tab is not a job-search parameter.
    expect(jobsHref({ by: "province", salary_disclosed: "true" }, "province", "Bali")).toBe(
      "/lowongan?salary_disclosed=true&province=Bali",
    );
  });

  it("drops empty values when building API query strings", () => {
    expect(toSearchParams({ q: "", page: 2, province: ["A", "B"], salary_min: undefined }).toString()).toBe(
      "page=2&province=A&province=B",
    );
  });
});

describe("pagination window", () => {
  it("shows first, last, and neighbours with gaps", () => {
    expect(pageWindow(1, 1)).toEqual([1]);
    expect(pageWindow(5, 57)).toEqual([1, "gap", 4, 5, 6, "gap", 57]);
    expect(pageWindow(2, 3)).toEqual([1, 2, 3]);
  });
});

describe("axis ticks", () => {
  it("uses whole-number 1-2-5 steps", () => {
    expect(niceTicks(216)).toEqual([0, 100, 200, 300]);
    expect(niceTicks(3)).toEqual([0, 1, 2, 3]);
    expect(niceTicks(1)).toEqual([0, 1]);
  });
});

describe("admin Basic authentication", () => {
  const env = { ADMIN_USERNAME: "ops", ADMIN_PASSWORD: "s3cret", ADMIN_API_TOKEN: "t" } as unknown as NodeJS.ProcessEnv;
  const basic = (value: string) => `Basic ${btoa(value)}`;

  it("is disabled without configuration", () => {
    expect(checkAdminAuthorization(basic("ops:s3cret"), {} as NodeJS.ProcessEnv)).toBe("disabled");
  });

  it("accepts only the configured credentials", () => {
    expect(checkAdminAuthorization(basic("ops:s3cret"), env)).toBe("ok");
    expect(checkAdminAuthorization(basic("ops:wrong"), env)).toBe("unauthorized");
    expect(checkAdminAuthorization(basic("ops"), env)).toBe("unauthorized");
    expect(checkAdminAuthorization("Bearer x", env)).toBe("unauthorized");
    expect(checkAdminAuthorization("Basic %%%", env)).toBe("unauthorized");
    expect(checkAdminAuthorization(null, env)).toBe("unauthorized");
  });
});

describe("listing links and status helpers", () => {
  it("only accepts http(s) URLs as external links", async () => {
    const { safeExternalUrl, sourceHost } = await import("./status");
    expect(sourceHost("https://www.lokeraceh.id/loker/1")).toBe("lokeraceh.id");
    expect(safeExternalUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalUrl("not a url")).toBeNull();
    expect(safeExternalUrl(null)).toBeNull();
    expect(safeExternalUrl("http://contoh.id/a")).toBe("http://contoh.id/a");
  });

  it("highlights a nav section on its sub-pages too", async () => {
    const { isActiveSection, MAIN_NAV } = await import("@/components/shell/nav");
    const market = MAIN_NAV.find((item) => item.href === "/ringkasan")!;
    expect(isActiveSection("/pasar", market)).toBe(true);
    expect(isActiveSection("/lowongan/abc", MAIN_NAV[0])).toBe(true);
    expect(isActiveSection("/gaji", market)).toBe(false);
  });
});

describe("job card text", () => {
  const base = {
    published_at: null,
    posted_age_days: null,
    last_seen_at: "2026-06-13T00:00:00+07:00",
  };

  it("prefers the stated posting date and marks derived dates as approximate", async () => {
    const { postedText } = await import("@/components/jobs/job-card");
    expect(postedText({ ...base, published_at: "2026-09-11T00:00:00Z" })).toBe("Tayang 11 Sep 2026");
    expect(postedText({ ...base, posted_age_days: 3 })).toBe("Tayang ± 10 Jun 2026");
    expect(postedText(base)).toBeNull();
  });

  it("never shows a missing salary as an amount", async () => {
    const { salaryLine } = await import("@/components/jobs/job-card");
    const salary = {
      status: { code: "NOT_DISCLOSED", label: "Tidak dicantumkan" },
      text: null,
      min: null,
      max: null,
      currency: null,
      period: { code: "UNKNOWN", label: "periode tidak diketahui" },
      period_assumed: false,
      monthly_min: null,
      monthly_max: null,
      comparable: false,
    };
    expect(salaryLine(salary)).toEqual({ text: "Gaji tidak dicantumkan", disclosed: false });
    expect(salaryLine({ ...salary, status: { code: "UNPARSEABLE", label: "" } }).text).toBe("Gaji tidak tersedia");
    expect(
      salaryLine({
        ...salary,
        status: { code: "DISCLOSED", label: "" },
        min: 4_000_000,
        max: 5_000_000,
        currency: "IDR",
        period: { code: "MONTH", label: "per bulan" },
        period_assumed: true,
        comparable: true,
      }).text,
    ).toBe("Rp 4.000.000 – Rp 5.000.000/bulan*");
    // A disclosed monthly rupiah salary the API rejects (e.g. "Rp 2 – Rp 897") is not shown as a salary.
    expect(
      salaryLine({
        ...salary,
        status: { code: "DISCLOSED", label: "" },
        min: 2,
        max: 897,
        currency: "IDR",
        period: { code: "MONTH", label: "per bulan" },
        comparable: false,
      }),
    ).toEqual({ text: "Angka gaji di sumber tidak wajar", disclosed: false });
  });
});
