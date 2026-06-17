"use client";

import { useId, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type {
  ItineraryQualityCheck,
  ItineraryQualitySeverity,
} from "@/lib/validateItinerary";

interface QualityPanelProps {
  checks: ItineraryQualityCheck[];
}

const severityLabel: Record<ItineraryQualitySeverity, string> = {
  low: "提示",
  medium: "注意",
  high: "重点",
};

const severityClass: Record<ItineraryQualitySeverity, string> = {
  low: "bg-sky-50 text-sky-700 ring-sky-100",
  medium: "bg-amber-50 text-amber-700 ring-amber-100",
  high: "bg-red-50 text-red-700 ring-red-100",
};

function QualityItem({ check }: { check: ItineraryQualityCheck }) {
  const isRisk = check.status === "risk";
  const Icon = isRisk ? AlertTriangle : CheckCircle2;
  const iconClass = isRisk ? "text-amber-600" : "text-teal-700";

  return (
    <li className="flex gap-3 rounded-lg bg-zinc-50 px-3 py-3">
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconClass}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-zinc-950">{check.title}</p>
          {isRisk && check.severity ? (
            <span
              className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold ring-1 ${severityClass[check.severity]}`}
            >
              {severityLabel[check.severity]}
            </span>
          ) : null}
        </div>
        <p className="mt-1 text-sm leading-6 text-zinc-600">{check.detail}</p>
      </div>
    </li>
  );
}

export function QualityPanel({ checks }: QualityPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const contentId = useId();
  const riskChecks = checks.filter((check) => check.status === "risk");
  const passChecks = checks.filter((check) => check.status === "pass");
  const badgeLabel =
    riskChecks.length > 0 ? `${riskChecks.length} 个风险` : "全部通过";

  return (
    <Card className="rounded-lg shadow-sm">
      <CardHeader className={cn("p-0", isOpen ? "border-b border-zinc-100" : "")}>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls={contentId}
          className="flex w-full items-start justify-between gap-3 rounded-lg p-6 text-left transition-colors hover:bg-zinc-50"
          onClick={() => setIsOpen((current) => !current)}
        >
          <div className="min-w-0">
            <p className="text-sm text-zinc-500">
              预算、坐标、节奏、交通和天气 · {isOpen ? "点击收起" : "点击展开"}
            </p>
            <CardTitle className="mt-1 flex items-center gap-2 text-xl">
              <ShieldCheck className="h-5 w-5 shrink-0 text-teal-700" aria-hidden="true" />
              <span>质量检查</span>
            </CardTitle>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Badge
              className={
                riskChecks.length > 0
                  ? "rounded-lg bg-amber-600 hover:bg-amber-600"
                  : "rounded-lg bg-teal-700 hover:bg-teal-700"
              }
            >
              {badgeLabel}
            </Badge>
            <ChevronDown
              className={cn(
                "h-4 w-4 text-zinc-500 transition-transform",
                isOpen ? "rotate-180" : "",
              )}
              aria-hidden="true"
            />
          </div>
        </button>
      </CardHeader>
      {isOpen ? (
        <CardContent id={contentId} className="space-y-4 pt-4">
          {riskChecks.length > 0 ? (
            <section>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900">
                <AlertTriangle className="h-4 w-4 text-amber-600" aria-hidden="true" />
                风险项
              </div>
              <ul className="space-y-2">
                {riskChecks.map((check) => (
                  <QualityItem key={check.id} check={check} />
                ))}
              </ul>
            </section>
          ) : null}

          {passChecks.length > 0 ? (
            <section>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-zinc-900">
                <CheckCircle2 className="h-4 w-4 text-teal-700" aria-hidden="true" />
                通过项
              </div>
              <ul className="space-y-2">
                {passChecks.map((check) => (
                  <QualityItem key={check.id} check={check} />
                ))}
              </ul>
            </section>
          ) : null}
        </CardContent>
      ) : null}
    </Card>
  );
}
