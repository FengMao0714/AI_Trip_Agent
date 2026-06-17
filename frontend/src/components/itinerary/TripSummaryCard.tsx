import {
  CalendarDays,
  CheckCircle2,
  Gauge,
  Info,
  MapPinned,
  ShieldCheck,
  Wallet,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getItineraryInsights } from "@/lib/itineraryInsights";
import type { Itinerary } from "@/types/itinerary";

interface TripSummaryCardProps {
  itinerary: Itinerary;
}

export function TripSummaryCard({ itinerary }: TripSummaryCardProps) {
  const insights = getItineraryInsights(itinerary);
  const dayCount = itinerary.days.length;
  const activityCount = itinerary.days.reduce(
    (total, day) => total + day.activities.length,
    0,
  );
  const remaining =
    itinerary.budget !== undefined ? itinerary.budget - itinerary.total_cost : null;
  const badgeLabel =
    remaining === null ? "行程" : remaining >= 0 ? "预算内" : "超预算";
  const badgeClass =
    remaining === null || remaining >= 0
      ? "rounded-lg bg-teal-400 text-zinc-950 hover:bg-teal-400"
      : "rounded-lg bg-red-500 hover:bg-red-500";
  const budgetUsageLabel =
    insights.budgetUsage === null ? "未设置" : `${insights.budgetUsage}%`;
  const sourceLabel =
    insights.sourceCoverage >= 80
      ? "来源覆盖良好"
      : insights.sourceCoverage > 0
        ? "部分来源待补"
        : "来源待确认";

  return (
    <Card className="overflow-hidden rounded-xl border-white/10 bg-[#081211] text-stone-100 shadow-[0_22px_60px_rgba(0,0,0,0.30),inset_0_1px_0_rgba(255,255,255,0.05)]">
      <div className="border-b border-white/10 bg-[radial-gradient(circle_at_86%_16%,rgba(45,212,191,0.16),transparent_34%),linear-gradient(135deg,rgba(12,22,21,0.98),rgba(3,8,8,0.98))] px-5 py-5 text-stone-100">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-sm text-stone-400">
              {itinerary.destination} · {dayCount} 天游
              {itinerary.budget !== undefined
                ? ` · 预算 ${itinerary.budget} 元`
                : ""}
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-normal text-amber-50">
              行程概览
            </h2>
            {itinerary.summary ? (
              <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-300">
                {itinerary.summary}
              </p>
            ) : null}
          </div>
          <Badge className={`${badgeClass} shrink-0 border-0`}>{badgeLabel}</Badge>
        </div>
      </div>
      <CardHeader className="pb-3">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-teal-300/20 bg-teal-400/10 p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-teal-100">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              可信执行分
            </div>
            <p className="text-2xl font-semibold text-stone-50">
              {insights.confidenceScore}
              <span className="ml-1 text-sm font-medium text-stone-500">/ 100</span>
            </p>
          </div>
          <div className="rounded-lg border border-amber-300/20 bg-amber-400/10 p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-amber-100">
              <Gauge className="h-4 w-4" aria-hidden="true" />
              预算使用率
            </div>
            <p className="text-2xl font-semibold text-stone-50">
              {budgetUsageLabel}
            </p>
          </div>
          <div className="rounded-lg border border-sky-300/20 bg-sky-400/10 p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-sky-100">
              <MapPinned className="h-4 w-4" aria-hidden="true" />
              地图核验
            </div>
            <p className="text-2xl font-semibold text-stone-50">
              {insights.mapVerifiedCount}/{activityCount}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {itinerary.generation_source ? (
          <div className="rounded-lg border border-teal-300/20 bg-teal-400/10 px-3 py-2 text-sm text-teal-100">
            <div className="flex flex-wrap items-center gap-2 font-medium">
              <Info className="h-4 w-4" aria-hidden="true" />
              生成来源：{itinerary.generation_source.label}
              {itinerary.generation_source.is_fallback ? "（兜底）" : ""}
            </div>
            {itinerary.generation_source.detail ? (
              <p className="mt-1 leading-6 text-teal-200/80">
                {itinerary.generation_source.detail}
              </p>
            ) : null}
            {itinerary.generation_source.tools &&
            itinerary.generation_source.tools.length > 0 ? (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {itinerary.generation_source.tools.map((tool) => (
                  <span
                    key={tool}
                    className="rounded-md border border-teal-300/20 bg-teal-300/10 px-2 py-1 text-xs font-medium text-teal-100"
                  >
                    {tool}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
        <div className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-stone-100">
            <CheckCircle2 className="h-4 w-4 text-teal-300" aria-hidden="true" />
            来源与验证
          </div>
          <div className="grid gap-2 text-sm sm:grid-cols-3">
            <span className="rounded-md bg-white/[0.045] px-3 py-2 text-stone-300">
              {sourceLabel} · {insights.sourceCoverage}%
            </span>
            <span className="rounded-md bg-white/[0.045] px-3 py-2 text-stone-300">
              已验证 {insights.verifiedCount} 个地点
            </span>
            <span className="rounded-md bg-white/[0.045] px-3 py-2 text-stone-300">
              待确认 {insights.warningCount + insights.coordinateMissingCount} 项
            </span>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
          <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-stone-400">
              <CalendarDays className="h-4 w-4 text-teal-300" />
              天数
            </div>
            <p className="text-2xl font-semibold">{dayCount} 天</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-stone-400">
              <Wallet className="h-4 w-4 text-amber-300" />
              费用
            </div>
            <p className="text-2xl font-semibold">{itinerary.total_cost} 元</p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-stone-400">
              <MapPinned className="h-4 w-4 text-sky-300" />
              站点
            </div>
            <p className="text-2xl font-semibold">{activityCount} 个</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
