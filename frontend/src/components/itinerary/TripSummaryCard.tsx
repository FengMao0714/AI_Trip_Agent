import { CalendarDays, Info, MapPinned, Wallet } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Itinerary } from "@/types/itinerary";

interface TripSummaryCardProps {
  itinerary: Itinerary;
}

export function TripSummaryCard({ itinerary }: TripSummaryCardProps) {
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
      ? "rounded-lg bg-teal-700 hover:bg-teal-700"
      : "rounded-lg bg-red-600 hover:bg-red-600";

  return (
    <Card className="rounded-lg shadow-sm">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sm text-zinc-500">
              {itinerary.destination} · {dayCount} 天游
              {itinerary.budget !== undefined
                ? ` · 预算 ${itinerary.budget} 元`
                : ""}
            </p>
            <CardTitle className="mt-1 text-xl">行程概览</CardTitle>
          </div>
          <Badge className={badgeClass}>{badgeLabel}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {itinerary.summary ? (
          <p className="text-sm leading-6 text-zinc-600">{itinerary.summary}</p>
        ) : null}
        {itinerary.generation_source ? (
          <div className="rounded-lg border border-teal-100 bg-teal-50 px-3 py-2 text-sm text-teal-900">
            <div className="flex items-center gap-2 font-medium">
              <Info className="h-4 w-4" aria-hidden="true" />
              生成来源：{itinerary.generation_source.label}
              {itinerary.generation_source.is_fallback ? "（兜底）" : ""}
            </div>
            {itinerary.generation_source.detail ? (
              <p className="mt-1 leading-6 text-teal-800">
                {itinerary.generation_source.detail}
              </p>
            ) : null}
            {itinerary.generation_source.tools &&
            itinerary.generation_source.tools.length > 0 ? (
              <p className="mt-1 text-xs text-teal-700">
                依据/工具：{itinerary.generation_source.tools.join("、")}
              </p>
            ) : null}
          </div>
        ) : null}
        <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
          <div className="rounded-lg bg-zinc-50 p-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-zinc-600">
              <CalendarDays className="h-4 w-4 text-teal-700" />
              天数
            </div>
            <p className="text-2xl font-semibold">{dayCount} 天</p>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-zinc-600">
              <Wallet className="h-4 w-4 text-amber-600" />
              费用
            </div>
            <p className="text-2xl font-semibold">{itinerary.total_cost} 元</p>
          </div>
          <div className="rounded-lg bg-zinc-50 p-3">
            <div className="mb-2 flex items-center gap-2 text-sm text-zinc-600">
              <MapPinned className="h-4 w-4 text-sky-700" />
              站点
            </div>
            <p className="text-2xl font-semibold">{activityCount} 个</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
