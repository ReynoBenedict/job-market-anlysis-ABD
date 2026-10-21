import { NotFoundContent } from "@/components/not-found-content";
import { SiteFooter } from "@/components/shell/site-footer";
import { SiteHeader } from "@/components/shell/site-header";

/** Unknown URLs: rendered inside the root layout only, so it brings its own header. */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader />
      <main id="konten" tabIndex={-1} className="flex flex-1">
        <NotFoundContent />
      </main>
      <SiteFooter />
    </div>
  );
}
