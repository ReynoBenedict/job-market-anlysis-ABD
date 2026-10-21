import { MissingSavedJobNotice } from "@/components/jobs/missing-saved-job";
import { NotFoundContent } from "@/components/not-found-content";

/**
 * Body for an unknown job: the generic 404 text, plus a way out when the job came from
 * this browser's saved list. Used by the proxy's 404 page and by lowongan/[id]/not-found.
 */
export function MissingJob() {
  return (
    <>
      <NotFoundContent />
      <div className="mx-auto -mt-8 mb-12 w-full max-w-lg px-4">
        <MissingSavedJobNotice />
      </div>
    </>
  );
}
