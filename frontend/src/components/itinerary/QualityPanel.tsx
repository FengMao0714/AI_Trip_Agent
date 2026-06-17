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
  low: "bg-sky-400/10 text-sky-200 ring-sky-300/20",
  medium: "bg-amber-400/10 text-amber-200 ring-amber-300/20",
  high: "bg-red-500/10 text-red-200 ring-red-400/20",
};

function QualityItem({ check }: { check: ItineraryQualityCheck }) {
  const isRisk = check.status === "risk";
  const Icon = isRisk ? AlertTriangle : CheckCircle2;
  const iconClass = isRisk ? "text-amber-300" : "text-teal-300";

  return (
    <li className="flex gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-3">
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${iconClass}`} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-sm font-semibold text-stone-100">{check.title}</p>
          {isRisk && check.severity ? (
            <span
              className={`inline-flex rounded-md px-2 py-0.5 text-[11px] font-semibold ring-1 ${severityClass[check.severity]}`}
            >
              {severityLabel[check.severity]}
            </span>
          ) : null}
        </div>
        <p className="mt-1 text-sm leading-6 text-stone-400">{check.detail}</p>
      </div>
    </li>
  );
}

export function QualityPanel({ checks }: QualityPanelProps) {
  const [isOpen, setIsOpen] = useState(true);
  const contentId = useId();
  const riskChecks = checks.filter((check) => check.status === "risk");
  const passChecks = checks.filter((check) => check.status === "pass");
  const badgeLabel =
    riskChecks.length > 0 ? `${riskChecks.length} 个风险` : "全部通过";

  return (
    <Card className="rounded-xl border-white/10 bg-[#081211] text-stone-100 shadow-[0_18px_52px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.05)]">
      <CardHeader className={cn("p-0", isOpen ? "border-b border-white/10" : "")}>
        <button
          type="button"
          aria-expanded={isOpen}
          aria-controls={contentId}
          className="flex w-full items-start justify-between gap-3 rounded-lg p-5 text-left transition-colors hover:bg-white/[0.04]"
          onClick={() => setIsOpen((current) => !current)}
        >
          <div className="min-w-0">
            <p className="text-sm text-stone-500">
              预算、坐标、节奏、交通和天气 · {isOpen ? "点击收起" : "点击展开"}
            </p>
            <CardTitle className="mt-1 flex items-center gap-2 text-xl text-amber-50">
              <ShieldCheck className="h-5 w-5 shrink-0 text-teal-300" aria-hidden="true" />
              <span>行程质量检查</span>
            </CardTitle>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Badge
              className={
                riskChecks.length > 0
                  ? "rounded-lg bg-amber-600 hover:bg-amber-600"
                  : "rounded-lg bg-teal-400 text-zinc-950 hover:bg-teal-400"
              }
            >
              {badgeLabel}
            </Badge>
            <ChevronDown
              className={cn(
                "h-4 w-4 text-stone-500 transition-transform",
                isOpen ? "rotate-180" : "",
              )}
              aria-hidden="true"
            />
          </div>
        </button>
      </CardHeader>
      {isOpen ? (
        <CardContent id={contentId} className="space-y-4 pt-4">
          <div className="grid gap-2 sm:grid-cols-3">
            <div className="rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2">
              <p className="text-xs text-stone-500">检查项</p>
              <p className="mt-1 text-sm font-semibold text-stone-100">
                {checks.length} 项
              </p>
            </div>
            <div className="rounded-lg border border-amber-300/20 bg-amber-400/10 px-3 py-2">
              <p className="text-xs text-amber-100">风险项</p>
              <p className="mt-1 text-sm font-semibold text-stone-100">
                {riskChecks.length} 项
              </p>
            </div>
            <div className="rounded-lg border border-teal-300/20 bg-teal-400/10 px-3 py-2">
              <p className="text-xs text-teal-100">通过项</p>
              <p className="mt-1 text-sm font-semibold text-stone-100">
                {passChecks.length} 项
              </p>
            </div>
          </div>
          {riskChecks.length > 0 ? (
            <section>
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-stone-100">
                <AlertTriangle className="h-4 w-4 text-amber-300" aria-hidden="true" />
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
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-stone-100">
                <CheckCircle2 className="h-4 w-4 text-teal-300" aria-hidden="true" />
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
