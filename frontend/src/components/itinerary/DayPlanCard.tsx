import { CalendarDays } from "lucide-react";

import { ActivityItem } from "@/components/itinerary/ActivityItem";
import { TransportSegment } from "@/components/itinerary/TransportSegment";
import { WeatherBadge } from "@/components/itinerary/WeatherBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDayCalendarLabel, getDayTitle } from "@/lib/dateDisplay";
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

  return (
    <Card className="rounded-lg shadow-sm">
      <CardHeader className="space-y-3 pb-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-sm font-medium text-teal-700">Day {day.day}</p>
            <CardTitle className="mt-1 text-xl">{getDayTitle(day)}</CardTitle>
            <p className="mt-2 flex items-center gap-1.5 text-sm text-zinc-600">
              <CalendarDays className="h-4 w-4 text-teal-700" aria-hidden="true" />
              {calendarLabel ?? "日期待确认"}
            </p>
          </div>
          <WeatherBadge weather={day.weather} />
        </div>
        {day.weather?.advice ? (
          <p className="rounded-lg bg-sky-50 px-3 py-2 text-sm leading-6 text-sky-800">
            {day.weather.advice}
          </p>
        ) : null}
      </CardHeader>
      <CardContent>
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
          <div className="rounded-lg border border-dashed border-zinc-300 px-4 py-6 text-sm text-zinc-500">
            暂无活动安排，可继续在对话中补充偏好让 Agent 细化。
          </div>
        )}
      </CardContent>
    </Card>
  );
}
