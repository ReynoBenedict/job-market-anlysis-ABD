import { CircleSlash, Eye, History } from "lucide-react";

import { Badge } from "@/components/ui";
import type { JobSummary } from "@/lib/api";
import { STATUS_EXPLANATION, type StatusCode } from "@/lib/status";

const STYLE: Record<StatusCode, { tone: "teal" | "neutral" | "warn"; icon: typeof Eye }> = {
  POTENTIALLY_ACTIVE: { tone: "teal", icon: Eye },
  NOT_SEEN_RECENTLY: { tone: "neutral", icon: History },
  EXPIRED_BY_SOURCE: { tone: "warn", icon: CircleSlash },
};

/** Status as icon + text (never color alone), with the explanation as a tooltip. */
export function StatusBadge({ freshness }: { freshness: JobSummary["freshness"] }) {
  const code = freshness.code as StatusCode;
  const { tone, icon: Icon } = STYLE[code] ?? STYLE.NOT_SEEN_RECENTLY;
  return (
    <Badge tone={tone} pill title={STATUS_EXPLANATION[code]}>
      <Icon aria-hidden className="size-3.5" />
      {freshness.label}
    </Badge>
  );
}
