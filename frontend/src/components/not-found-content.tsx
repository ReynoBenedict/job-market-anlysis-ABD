import { LinkButton } from "@/components/ui";

/** Body of every 404 page; the surrounding layout supplies the header and footer. */
export function NotFoundContent() {
  return (
    <div className="mx-auto flex max-w-lg flex-1 flex-col items-center justify-center px-4 py-16 text-center">
      <p className="font-mono text-sm text-ink-3">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-ink">Halaman atau lowongan tidak ditemukan</h1>
      <p className="mt-2 text-ink-2">
        Tautannya mungkin salah, atau lowongan ini sudah dihapus dari TalentScope (misalnya karena digabung dengan lowongan
        yang sama dari situs lain).
      </p>
      <div className="mt-6 flex gap-3">
        <LinkButton href="/lowongan">Cari Lowongan</LinkButton>
        <LinkButton href="/" variant="secondary">
          Beranda
        </LinkButton>
      </div>
    </div>
  );
}
