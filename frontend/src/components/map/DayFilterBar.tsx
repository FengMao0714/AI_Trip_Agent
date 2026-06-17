"use client";

import { MapPinned } from "lucide-react";

import { cn } from "@/lib/utils";
import type { DayPlan } from "@/types/itinerary";

type SelectedDay = "all" | number;

interface DayFilterBarProps {
  days: DayPlan[];
  selectedDay: SelectedDay;
  onSelectedDayChange: (day: SelectedDay) => void;
}

export function DayFilterBar({
  days,
  selectedDay,
  onSelectedDayChange,
}: DayFilterBarProps) {
  return (
    <div className="flex max-w-full items-center gap-1 overflow-x-auto rounded-lg bg-white/95 p-1 shadow-sm ring-1 ring-zinc-200 backdrop-blur">
      <button
        type="button"
        className={cn(
          "flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium text-zinc-600 transition-colors",
          selectedDay === "all" && "bg-teal-700 text-white",
        )}
        onClick={() => onSelectedDayChange("all")}
      >
        <MapPinned className="h-4 w-4" aria-hidden="true" />
        全部
      </button>
      {days.map((day) => (
        <button
          key={day.day}
          type="button"
          className={cn(
            "h-9 shrink-0 rounded-md px-3 text-sm font-medium text-zinc-600 transition-colors",
            selectedDay === day.day && "bg-teal-700 text-white",
          )}
          onClick={() => onSelectedDayChange(day.day)}
        >
          Day {day.day}
        </button>
      ))}
    </div>
  );
}
