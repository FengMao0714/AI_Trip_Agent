import type { Activity, Itinerary } from "@/types/itinerary";

export interface ItineraryInsights {
  activityCount: number;
  averageDailyCost: number;
  budgetRemaining: number | null;
  budgetUsage: number | null;
  confidenceScore: number;
  coordinateMissingCount: number;
  dayCount: number;
  highRiskCount: number;
  longTransferCount: number;
  mapVerifiedCount: number;
  sourceCoverage: number;
  sourceReadyCount: number;
  totalTransportMinutes: number;
  verifiedCount: number;
  warningCount: number;
  weatherReadyCount: number;
}

export function hasValidActivityCoordinates(activity: Activity) {
  return (
    Number.isFinite(activity.lng) &&
    Number.isFinite(activity.lat) &&
    activity.lng >= -180 &&
    activity.lng <= 180 &&
    activity.lat >= -90 &&
    activity.lat <= 90 &&
    !(activity.lng === 0 && activity.lat === 0)
  );
}

function hasSource(activity: Activity) {
  return Boolean(activity.source?.trim() || activity.source_refs?.length);
}

function isVerified(activity: Activity) {
  const sourceText = [activity.source, ...(activity.source_refs ?? [])]
    .filter(Boolean)
    .join(" ");
  return activity.is_verified === true || /高德|amap|poi/i.test(sourceText);
}

function normalizeScore(value: number) {
  return Math.max(45, Math.min(98, Math.round(value)));
}

export function getItineraryInsights(itinerary: Itinerary): ItineraryInsights {
  const activities = itinerary.days.flatMap((day) => day.activities);
  const activityCount = activities.length;
  const dayCount = itinerary.days.length;
  const mapVerifiedCount = activities.filter(hasValidActivityCoordinates).length;
  const coordinateMissingCount = activityCount - mapVerifiedCount;
  const verifiedCount = activities.filter(isVerified).length;
  const sourceReadyCount = activities.filter(hasSource).length;
  const sourceCoverage =
    activityCount > 0 ? Math.round((sourceReadyCount / activityCount) * 100) : 0;
  const warningCount = activities.reduce(
    (total, activity) => total + (activity.warnings?.length ?? 0),
    0,
  );
  const highRiskCount = activities.filter(
    (activity) => activity.risk_level === "high",
  ).length;
  const longTransferCount = activities.filter(
    (activity) => (activity.transport?.duration_min ?? 0) > 60,
  ).length;
  const totalTransportMinutes = activities.reduce(
    (total, activity) => total + Math.max(0, activity.transport?.duration_min ?? 0),
    0,
  );
  const weatherReadyCount = itinerary.days.filter((day) => day.weather).length;
  const budgetUsage =
    itinerary.budget && itinerary.budget > 0
      ? Math.round((itinerary.total_cost / itinerary.budget) * 100)
      : null;
  const budgetRemaining =
    itinerary.budget !== undefined ? itinerary.budget - itinerary.total_cost : null;
  const overBudgetPenalty =
    budgetRemaining !== null && budgetRemaining < 0
      ? Math.min(18, Math.abs(budgetRemaining) / Math.max(1, itinerary.total_cost) * 40)
      : 0;
  const explicitScore =
    typeof itinerary.quality_score === "number" &&
    Number.isFinite(itinerary.quality_score)
      ? itinerary.quality_score
      : null;
  const derivedScore =
    92 -
    coordinateMissingCount * 7 -
    Math.max(0, activityCount - sourceReadyCount) * 4 -
    warningCount * 3 -
    highRiskCount * 6 -
    longTransferCount * 4 -
    Math.max(0, dayCount - weatherReadyCount) * 2 -
    overBudgetPenalty;

  return {
    activityCount,
    averageDailyCost: dayCount > 0 ? Math.round(itinerary.total_cost / dayCount) : 0,
    budgetRemaining,
    budgetUsage,
    confidenceScore: normalizeScore(explicitScore ?? derivedScore),
    coordinateMissingCount,
    dayCount,
    highRiskCount,
    longTransferCount,
    mapVerifiedCount,
    sourceCoverage,
    sourceReadyCount,
    totalTransportMinutes,
    verifiedCount,
    warningCount,
    weatherReadyCount,
  };
}
