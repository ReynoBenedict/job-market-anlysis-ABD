import type { Metadata } from "next";

import { MissingJob } from "../missing-job";

export const metadata: Metadata = { title: "Lowongan tidak ditemukan" };

/** Target of the proxy's rewrite for unknown job IDs (served with HTTP 404). */
export default function MissingJobPage() {
  return <MissingJob />;
}
