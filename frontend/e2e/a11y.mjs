// Ad-hoc accessibility audit with axe-core (already installed as a transitive dependency).
import { chromium } from "@playwright/test";
import { createRequire } from "node:module";
const axePath = createRequire(import.meta.url).resolve("axe-core/axe.min.js");
const base = process.env.BASE ?? "http://localhost:3001";
const pages = ["/", "/lowongan", "/lowongan?province=Aceh&freshness=NOT_SEEN_RECENTLY", "/gaji", "/ringkasan", "/pasar", "/keterampilan", "/sumber-data", "/metodologi", "/tersimpan"];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
for (const path of [...pages, process.env.DETAIL].filter(Boolean)) {
  await page.goto(base + path, { waitUntil: "networkidle" });
  await page.addScriptTag({ path: axePath });
  const result = await page.evaluate(async () => await window.axe.run(document, { resultTypes: ["violations"] }));
  const lines = result.violations.map((v) => `  [${v.impact}] ${v.id}: ${v.help} (${v.nodes.length}) e.g. ${v.nodes[0].target.join(" ")}`);
  console.log(`${path}: ${result.violations.length} violation types`);
  if (lines.length) console.log(lines.join("\n"));
}
await browser.close();
