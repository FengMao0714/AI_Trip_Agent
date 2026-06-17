import { TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getDayCalendarLabel } from "@/lib/dateDisplay";
import type { DayPlan } from "@/types/itinerary";

interface DayTabBarProps {
  days: DayPlan[];
  tripStartDate?: string;
}

export function DayTabBar({ days, tripStartDate }: DayTabBarProps) {
  return (
    <div className="overflow-x-auto pb-1">
      <TabsList className="grid h-auto min-w-max grid-cols-3 rounded-lg border border-white/10 bg-white/[0.045] p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        {days.map((day) => {
          const calendarLabel = getDayCalendarLabel(day, tripStartDate);

          return (
            <TabsTrigger
              key={day.day}
              value={day.day.toString()}
              className="min-w-36 rounded-md px-4 py-2 text-stone-400 data-[state=active]:bg-teal-400 data-[state=active]:text-zinc-950"
            >
              <span className="flex flex-col items-center leading-tight">
                <span>Day {day.day}</span>
                {calendarLabel ? (
                  <span className="mt-1 text-xs font-normal opacity-75">
                    {calendarLabel}
                  </span>
                ) : null}
              </span>
            </TabsTrigger>
          );
        })}
      </TabsList>
    </div>
  );
}
