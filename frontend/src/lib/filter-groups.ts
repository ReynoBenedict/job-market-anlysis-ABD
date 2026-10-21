import type { FilterGroup } from "@/components/explorer/filter-panel";

import type { FilterOptions } from "./api";
import type { MultiFilter } from "./filters";

// Filters offered as checkbox groups. "tag" has no group: it is reached from the skills
// page and removed through its chip.
type PanelFilter = Exclude<MultiFilter, "tag">;

const GROUPS: { key: PanelFilter; title: string; initiallyVisible?: number }[] = [
  { key: "freshness", title: "Status lowongan" },
  { key: "province", title: "Provinsi", initiallyVisible: 6 },
  { key: "city", title: "Kota / kabupaten", initiallyVisible: 6 },
  { key: "role_family", title: "Bidang pekerjaan", initiallyVisible: 6 },
  { key: "employment_type", title: "Jenis pekerjaan" },
  { key: "work_arrangement", title: "Pengaturan kerja" },
  { key: "experience", title: "Pengalaman" },
  { key: "education", title: "Pendidikan minimum" },
  { key: "source", title: "Sumber" },
];

export function buildFilterGroups(options: FilterOptions): FilterGroup[] {
  // Options with no listings (e.g. no listing was seen recently) are not offered.
  return GROUPS.map((group) => ({ ...group, options: options[group.key].filter((option) => option.count > 0) })).filter(
    (group) => group.options.length > 0,
  );
}

/** value -> label maps used to name active-filter chips. */
export function filterLabels(options: FilterOptions): Partial<Record<MultiFilter, Record<string, string>>> {
  return Object.fromEntries(
    GROUPS.map(({ key }) => [key, Object.fromEntries(options[key].map((option) => [option.value, option.label]))]),
  );
}
