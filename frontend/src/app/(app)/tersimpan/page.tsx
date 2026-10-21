import type { Metadata } from "next";

import { PageHeader } from "@/components/ui";

import { SavedJobsList } from "./saved-jobs-list";

export const metadata: Metadata = { title: "Lowongan Tersimpan" };

export default function SavedJobsPage() {
  return (
    <>
      <PageHeader
        title="Lowongan Tersimpan"
        description="Daftar ini hanya tersimpan di browser ini, tidak ikut ke perangkat atau browser lain, dan hilang bila data situs di browser dihapus. TalentScope tidak punya akun dan tidak mengirim daftar ini ke server."
      />
      <SavedJobsList />
    </>
  );
}
