import { MissingJob } from "../missing-job";

/** notFound() from the job page during client-side navigation (full loads get the proxy's 404). */
export default function JobNotFound() {
  return <MissingJob />;
}
