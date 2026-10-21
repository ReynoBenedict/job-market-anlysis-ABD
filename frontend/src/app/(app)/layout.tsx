import { SiteFooter } from "@/components/shell/site-footer";
import { SiteHeader } from "@/components/shell/site-header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main id="konten" tabIndex={-1} className="flex-1 px-4 py-6 md:px-6 lg:py-8">
        <div className="mx-auto max-w-7xl">{children}</div>
      </main>
      <SiteFooter />
    </div>
  );
}
