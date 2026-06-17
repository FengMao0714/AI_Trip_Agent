"use client";

import { useMemo, useState } from "react";

import type { DayPlan, Itinerary } from "@/types/itinerary";

interface CostSummary {
  total: number;
  activityTotal: number;
  byType: Array<{
    label: string;
    amount: number;
  }>;
}

const UNALLOCATED_COST_LABEL = "住宿/其他未拆分";
const COST_TYPE_ORDER = [
  "景点",
  "餐厅",
  "住宿",
  "交通",
  "其他",
  UNALLOCATED_COST_LABEL,
];

function normalizeCost(value: number) {
  return Number.isFinite(value) && value > 0 ? Math.round(value) : 0;
}

function sortCostTypes(
  left: [string, number],
  right: [string, number],
) {
  const leftIndex = COST_TYPE_ORDER.indexOf(left[0]);
  const rightIndex = COST_TYPE_ORDER.indexOf(right[0]);

  if (leftIndex !== -1 || rightIndex !== -1) {
    return (
      (leftIndex === -1 ? COST_TYPE_ORDER.length : leftIndex) -
      (rightIndex === -1 ? COST_TYPE_ORDER.length : rightIndex)
    );
  }

  return left[0].localeCompare(right[0], "zh-Hans-CN");
}

export function useItinerary(itinerary: Itinerary) {
  const [selectedDay, setSelectedDay] = useState(
    itinerary.days[0]?.day.toString() ?? "1",
  );

  const currentDay = useMemo<DayPlan>(() => {
    return (
      itinerary.days.find((day) => day.day.toString() === selectedDay) ??
      itinerary.days[0]
    );
  }, [itinerary.days, selectedDay]);

  const costSummary = useMemo<CostSummary>(() => {
    const byType = new Map<string, number>();
    let activityTotal = 0;

    for (const day of itinerary.days) {
      for (const activity of day.activities) {
        const cost = normalizeCost(activity.cost);
        activityTotal += cost;
        byType.set(
          activity.place_type,
          (byType.get(activity.place_type) ?? 0) + cost,
        );
      }
    }

    const reportedTotal = normalizeCost(itinerary.total_cost);
    const total = Math.max(activityTotal, reportedTotal);
    const unallocatedCost = total - activityTotal;
    if (unallocatedCost > 0) {
      byType.set(
        UNALLOCATED_COST_LABEL,
        (byType.get(UNALLOCATED_COST_LABEL) ?? 0) + unallocatedCost,
      );
    }

    return {
      total,
      activityTotal,
      byType: Array.from(byType.entries())
        .sort(sortCostTypes)
        .map(([label, amount]) => ({
          label,
          amount,
        })),
    };
  }, [itinerary.days, itinerary.total_cost]);

  return {
    selectedDay,
    setSelectedDay,
    currentDay,
    costSummary,
  };
}
