import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { BarList } from "./charts/bar-list";
import { SaveJobButton } from "./jobs/save-job-button";

describe("BarList", () => {
  it("renders values as text and links to drill-downs", () => {
    render(
      <BarList
        caption="Lowongan per provinsi"
        items={[
          { key: "a", label: "DKI Jakarta", count: 521, share: 0.46, href: "/lowongan?province=DKI+Jakarta" },
          { key: "b", label: "Bali", count: 55, share: 0.0485 },
        ]}
      />,
    );
    const list = screen.getByRole("list", { name: "Lowongan per provinsi" });
    expect(list).toHaveTextContent("521");
    expect(list).toHaveTextContent("46%");
    expect(screen.getByRole("link", { name: /DKI Jakarta/ })).toHaveAttribute("href", "/lowongan?province=DKI+Jakarta");
    expect(screen.queryByRole("link", { name: /Bali/ })).toBeNull();
  });
});

describe("SaveJobButton", () => {
  it("toggles a job in browser storage", async () => {
    const user = userEvent.setup();
    render(<SaveJobButton job={{ id: "job-1", title: "Data Engineer", company: "PT Contoh", location: "Bandung" }} />);
    const button = screen.getByRole("button", { name: /Simpan lowongan: Data Engineer/ });
    expect(button).toHaveAttribute("aria-pressed", "false");

    await user.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(JSON.parse(window.localStorage.getItem("talentscope:saved-jobs:v1") ?? "[]")[0].id).toBe("job-1");

    await user.click(button);
    expect(button).toHaveAttribute("aria-pressed", "false");
    expect(JSON.parse(window.localStorage.getItem("talentscope:saved-jobs:v1") ?? "[]")).toEqual([]);
  });
});

describe("MissingSavedJobNotice", () => {
  const KEY = "talentscope:saved-jobs:v1";

  it("offers to remove a saved job whose record no longer exists", async () => {
    const { MissingSavedJobNotice } = await import("./jobs/missing-saved-job");
    const user = userEvent.setup();
    window.history.pushState({}, "", "/lowongan/3f1c2b4a-1111-4222-8333-444455556666");
    window.localStorage.setItem(
      KEY,
      JSON.stringify([
        { id: "3f1c2b4a-1111-4222-8333-444455556666", title: "Analis Data", company: "PT Contoh", location: null, savedAt: "2026-01-01T00:00:00Z" },
        { id: "other", title: "Lain", company: null, location: null, savedAt: "2026-01-01T00:00:00Z" },
      ]),
    );
    render(<MissingSavedJobNotice />);
    expect(screen.getByText("Lowongan ini ada di daftar tersimpanmu")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Hapus dari tersimpan" }));
    expect(screen.getByRole("status")).toHaveTextContent("“Analis Data” sudah dihapus dari daftar tersimpan.");
    expect(JSON.parse(window.localStorage.getItem(KEY) ?? "[]").map((job: { id: string }) => job.id)).toEqual(["other"]);
  });

  it("renders nothing for a job that was never saved", async () => {
    const { MissingSavedJobNotice } = await import("./jobs/missing-saved-job");
    window.history.pushState({}, "", "/lowongan/never-saved");
    window.localStorage.setItem(KEY, "[]");
    const { container } = render(<MissingSavedJobNotice />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("SavedJobsList", () => {
  it("explains blocked browser storage instead of claiming the list is empty", async () => {
    const { SavedJobsList } = await import("@/app/(app)/tersimpan/saved-jobs-list");
    const getItem = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    try {
      render(<SavedJobsList />);
      expect(screen.getByText("Browser ini tidak mengizinkan penyimpanan")).toBeInTheDocument();
      expect(screen.queryByText("Belum ada lowongan tersimpan")).toBeNull();
    } finally {
      getItem.mockRestore();
    }
  });
});
