"use client";

import Link from "next/link";
import { useMemo } from "react";
import { ExternalLink } from "lucide-react";

import { BudgetSummary } from "@/components/itinerary/BudgetSummary";
import { DayPlanCard } from "@/components/itinerary/DayPlanCard";
import { DayTabBar } from "@/components/itinerary/DayTabBar";
import { ExportDialog } from "@/components/itinerary/ExportDialog";
import { QualityPanel } from "@/components/itinerary/QualityPanel";
import { TripSummaryCard } from "@/components/itinerary/TripSummaryCard";
import { useItinerary } from "@/hooks/useItinerary";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { validateItinerary } from "@/lib/validateItinerary";
import type { Itinerary } from "@/types/itinerary";

interface ItineraryViewProps {
  itinerary: Itinerary;
  isQuickAdjustDisabled?: boolean;
  onQuickAdjust?: (instruction: string) => void;
  sessionId?: string;
  showDetailLink?: boolean;
}

export function ItineraryView({
  itinerary,
  isQuickAdjustDisabled = false,
  onQuickAdjust,
  sessionId,
  showDetailLink = true,
}: ItineraryViewProps) {
  const { selectedDay, setSelectedDay, costSummary } = useItinerary(itinerary);
  const qualityChecks = useMemo(
    () => validateItinerary(itinerary),
    [itinerary],
  );
  const detailHref = sessionId
    ? `/itinerary/${encodeURIComponent(sessionId)}`
    : null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-200/80">
            Generated Travel Plan
          </p>
          <p className="mt-1 text-sm text-stone-400">
            可导出、可微调、可地图核验的行程成果包
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
        {showDetailLink && detailHref ? (
          <Button
            asChild
            type="button"
            variant="outline"
            size="sm"
            className="rounded-lg border-white/10 bg-white/[0.04] text-stone-200 hover:bg-white/10 hover:text-stone-50"
          >
            <Link href={detailHref}>
              <ExternalLink className="h-4 w-4" aria-hidden="true" />
              详情
            </Link>
          </Button>
        ) : null}
        <ExportDialog itinerary={itinerary} />
        </div>
      </div>
      <TripSummaryCard itinerary={itinerary} />
      <QualityPanel checks={qualityChecks} />
      <Tabs value={selectedDay} onValueChange={setSelectedDay}>
        <DayTabBar days={itinerary.days} tripStartDate={itinerary.start_date} />
        {itinerary.days.map((day) => (
          <TabsContent key={day.day} value={day.day.toString()} className="mt-3">
            <DayPlanCard
              day={day}
              tripStartDate={itinerary.start_date}
              isQuickAdjustDisabled={isQuickAdjustDisabled}
              onQuickAdjust={onQuickAdjust}
            />
          </TabsContent>
        ))}
      </Tabs>
      <BudgetSummary
        total={costSummary.total}
        budget={itinerary.budget}
        byType={costSummary.byType}
      />
    </div>
  );
}
