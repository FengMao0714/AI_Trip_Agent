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
    <div className="flex max-w-full items-center gap-1 overflow-x-auto rounded-lg border border-white/10 bg-[#07100f]/90 p-1 shadow-lg backdrop-blur">
      <button
        type="button"
        className={cn(
          "flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium text-stone-400 transition-colors",
          selectedDay === "all" && "bg-teal-400 text-zinc-950",
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
            "h-9 shrink-0 rounded-md px-3 text-sm font-medium text-stone-400 transition-colors",
            selectedDay === day.day && "bg-teal-400 text-zinc-950",
          )}
          onClick={() => onSelectedDayChange(day.day)}
        >
          Day {day.day}
        </button>
      ))}
    </div>
  );
}
