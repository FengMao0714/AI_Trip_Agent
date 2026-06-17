import { AlertTriangle, CalendarDays, MapPinned, WalletCards } from "lucide-react";

import { ActivityItem } from "@/components/itinerary/ActivityItem";
import { TransportSegment } from "@/components/itinerary/TransportSegment";
import { WeatherBadge } from "@/components/itinerary/WeatherBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDayCalendarLabel, getDayTitle } from "@/lib/dateDisplay";
import { hasValidActivityCoordinates } from "@/lib/itineraryInsights";
import type { DayPlan } from "@/types/itinerary";

interface DayPlanCardProps {
  day: DayPlan;
  tripStartDate?: string;
  isQuickAdjustDisabled?: boolean;
  onQuickAdjust?: (instruction: string) => void;
}

export function DayPlanCard({
  day,
  tripStartDate,
  isQuickAdjustDisabled = false,
  onQuickAdjust,
}: DayPlanCardProps) {
  const calendarLabel = getDayCalendarLabel(day, tripStartDate);
  const dayCost = day.activities.reduce((total, activity) => total + activity.cost, 0);
  const mappedCount = day.activities.filter(hasValidActivityCoordinates).length;
  const risks = [
    ...(day.risk_summary ?? []),
    ...(day.weather?.advice ? [day.weather.advice] : []),
  ];

  return (
    <Card className="overflow-hidden rounded-xl border-white/10 bg-[#081211] text-stone-100 shadow-[0_20px_56px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.05)]">
      <CardHeader className="space-y-4 border-b border-white/10 bg-[linear-gradient(145deg,rgba(255,255,255,0.045),rgba(255,255,255,0.015))] pb-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium text-teal-200">Day {day.day}</p>
            <CardTitle className="mt-1 text-xl text-amber-50">{getDayTitle(day)}</CardTitle>
            <p className="mt-2 flex items-center gap-1.5 text-sm text-stone-400">
              <CalendarDays className="h-4 w-4 text-teal-300" aria-hidden="true" />
              {calendarLabel ?? "日期待确认"}
            </p>
          </div>
          <WeatherBadge weather={day.weather} />
        </div>
        <div className="grid gap-2 sm:grid-cols-3">
          <div className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
            <p className="text-xs text-stone-500">活动节点</p>
            <p className="mt-1 text-sm font-semibold text-stone-100">
              {day.activities.length} 个
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
            <p className="flex items-center gap-1 text-xs text-stone-500">
              <WalletCards className="h-3.5 w-3.5" aria-hidden="true" />
              当日预算
            </p>
            <p className="mt-1 text-sm font-semibold text-stone-100">
              {dayCost} 元
            </p>
          </div>
          <div className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
            <p className="flex items-center gap-1 text-xs text-stone-500">
              <MapPinned className="h-3.5 w-3.5" aria-hidden="true" />
              地图点位
            </p>
            <p className="mt-1 text-sm font-semibold text-stone-100">
              {mappedCount}/{day.activities.length}
            </p>
          </div>
        </div>
        {risks.length > 0 ? (
          <div className="rounded-lg border border-amber-300/20 bg-amber-400/10 px-3 py-2 text-sm leading-6 text-amber-100">
            <div className="mb-1 flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              天气/风险提示
            </div>
            <p>{risks.slice(0, 2).join("；")}</p>
          </div>
        ) : (
          <div className="rounded-lg border border-sky-300/20 bg-sky-400/10 px-3 py-2 text-sm leading-6 text-sky-100">
            天气/风险提示：暂无明显风险，按当前节奏执行。
          </div>
        )}
      </CardHeader>
      <CardContent className="bg-transparent pt-5">
        {day.activities.length > 0 ? (
          <div className="space-y-1">
            {day.activities.map((activity, index) => (
              <div key={`${day.day}-${activity.time_slot}-${activity.place_name}`}>
                <ActivityItem
                  activity={activity}
                  dayNumber={day.day}
                  isQuickAdjustDisabled={isQuickAdjustDisabled}
                  onQuickAdjust={onQuickAdjust}
                />
                {index < day.activities.length - 1 ? (
                  <TransportSegment
                    transport={day.activities[index + 1].transport}
                  />
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-white/15 px-4 py-6 text-sm text-stone-500">
            暂无活动安排，可继续在对话中补充偏好让 Agent 细化。
          </div>
        )}
      </CardContent>
    </Card>
  );
}
