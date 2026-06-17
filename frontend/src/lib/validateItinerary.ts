import type { Activity, Itinerary } from "@/types/itinerary";

export type ItineraryQualityStatus = "pass" | "risk";
export type ItineraryQualitySeverity = "low" | "medium" | "high";

export interface ItineraryQualityCheck {
  id: string;
  title: string;
  detail: string;
  status: ItineraryQualityStatus;
  severity?: ItineraryQualitySeverity;
}

const MAX_ACTIVITIES_PER_DAY = 6;
const MAX_TRANSPORT_DURATION_MIN = 60;
const MAX_WEATHER_RISK_OUTDOOR_ACTIVITIES = 3;

function formatCost(value: number) {
  return `${Math.round(value)} 元`;
}

function hasBudget(itinerary: Itinerary): itinerary is Itinerary & { budget: number } {
  return (
    typeof itinerary.budget === "number" &&
    Number.isFinite(itinerary.budget) &&
    itinerary.budget > 0
  );
}

function hasValidCoordinates(activity: Activity) {
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

function isOutdoorActivity(activity: Activity) {
  return activity.place_type === "景点" || activity.place_type === "交通";
}

function hasWeatherRiskText(text: string) {
  return /雨|雪|雷|暴|台风|大风|风大|高温|炎热|寒潮|降温|雾|霾|沙尘|紫外线|日晒/u.test(
    text,
  );
}

function validateBudget(itinerary: Itinerary): ItineraryQualityCheck {
  if (!hasBudget(itinerary)) {
    return {
      id: "budget-missing",
      title: "预算待确认",
      detail: "当前行程没有预算上限，暂时无法判断总费用是否超支。",
      status: "risk",
      severity: "low",
    };
  }

  const budget = itinerary.budget;
  const overrun = itinerary.total_cost - budget;

  if (overrun > 0) {
    return {
      id: "budget-overrun",
      title: "预算超限",
      detail: `预计总费用 ${formatCost(itinerary.total_cost)}，超过预算 ${formatCost(
        budget,
      )} 约 ${formatCost(overrun)}。`,
      status: "risk",
      severity: overrun / budget > 0.15 ? "high" : "medium",
    };
  }

  return {
    id: "budget-ok",
    title: "预算合理",
    detail: `预计总费用 ${formatCost(itinerary.total_cost)}，未超过预算 ${formatCost(
      budget,
    )}。`,
    status: "pass",
  };
}

function validateCoordinates(itinerary: Itinerary): ItineraryQualityCheck {
  const invalidActivities = itinerary.days.flatMap((day) =>
    day.activities
      .filter((activity) => !hasValidCoordinates(activity))
      .map((activity) => `Day ${day.day} ${activity.place_name}`),
  );

  if (invalidActivities.length > 0) {
    const examples = invalidActivities.slice(0, 3).join("、");
    const moreCount = invalidActivities.length - 3;

    return {
      id: "coordinates-invalid",
      title: "存在无效坐标",
      detail: `${examples}${moreCount > 0 ? ` 等 ${invalidActivities.length} 个地点` : ""} 的经纬度待确认，地图标注可能不完整。`,
      status: "risk",
      severity: "high",
    };
  }

  return {
    id: "coordinates-ok",
    title: "坐标完整",
    detail: "所有活动地点都有可用于地图展示的经纬度。",
    status: "pass",
  };
}

function validateActivityCounts(itinerary: Itinerary): ItineraryQualityCheck[] {
  const crowdedDays = itinerary.days.filter(
    (day) => day.activities.length > MAX_ACTIVITIES_PER_DAY,
  );

  if (crowdedDays.length === 0) {
    return [
      {
        id: "activity-count-ok",
        title: "活动数量适中",
        detail: `每天活动不超过 ${MAX_ACTIVITIES_PER_DAY} 个，节奏相对可控。`,
        status: "pass",
      },
    ];
  }

  return crowdedDays.map((day) => ({
    id: `activity-count-day-${day.day}`,
    title: `Day ${day.day} 活动较多`,
    detail: `当天安排了 ${day.activities.length} 个活动，建议预留休息、排队或临时调整时间。`,
    status: "risk",
    severity: day.activities.length >= MAX_ACTIVITIES_PER_DAY + 2 ? "high" : "medium",
  }));
}

function validateTransportDurations(itinerary: Itinerary): ItineraryQualityCheck {
  const longTransports = itinerary.days.flatMap((day) =>
    day.activities
      .filter(
        (activity) =>
          activity.transport &&
          activity.transport.duration_min > MAX_TRANSPORT_DURATION_MIN,
      )
      .map((activity) => ({
        day: day.day,
        placeName: activity.place_name,
        duration: activity.transport?.duration_min ?? 0,
        mode: activity.transport?.mode ?? "未知",
      })),
  );

  if (longTransports.length > 0) {
    const examples = longTransports
      .slice(0, 3)
      .map(
        (transport) =>
          `Day ${transport.day} 到 ${transport.placeName} ${Math.round(
            transport.duration,
          )} 分钟`,
      )
      .join("、");
    const longestDuration = Math.max(
      ...longTransports.map((transport) => transport.duration),
    );

    return {
      id: "transport-long",
      title: "存在长距离转场",
      detail: `${examples}，建议确认交通方式和出发时间。`,
      status: "risk",
      severity: longestDuration > 90 ? "high" : "medium",
    };
  }

  return {
    id: "transport-ok",
    title: "交通耗时合理",
    detail: `单段交通耗时均不超过 ${MAX_TRANSPORT_DURATION_MIN} 分钟。`,
    status: "pass",
  };
}

function validateWeatherRisks(itinerary: Itinerary): ItineraryQualityCheck {
  const riskyDays = itinerary.days
    .map((day) => {
      const weatherText = [day.weather?.condition, day.weather?.advice]
        .filter(Boolean)
        .join(" ");
      const outdoorCount = day.activities.filter(isOutdoorActivity).length;

      return {
        day: day.day,
        outdoorCount,
        weatherText,
        hasRisk: hasWeatherRiskText(weatherText),
      };
    })
    .filter(
      (day) =>
        day.hasRisk && day.outdoorCount >= MAX_WEATHER_RISK_OUTDOOR_ACTIVITIES,
    );

  if (riskyDays.length > 0) {
    const examples = riskyDays
      .slice(0, 2)
      .map((day) => `Day ${day.day} 有 ${day.outdoorCount} 个户外/交通活动`)
      .join("、");

    return {
      id: "weather-risk",
      title: "天气风险需关注",
      detail: `${examples}，且天气提示存在风险，建议准备室内备选或缩短户外停留。`,
      status: "risk",
      severity: "medium",
    };
  }

  return {
    id: "weather-ok",
    title: "天气安排可控",
    detail: "暂未发现明显天气风险与高密度户外安排叠加的问题。",
    status: "pass",
  };
}

export function validateItinerary(itinerary: Itinerary): ItineraryQualityCheck[] {
  return [
    validateBudget(itinerary),
    validateCoordinates(itinerary),
    ...validateActivityCounts(itinerary),
    validateTransportDurations(itinerary),
    validateWeatherRisks(itinerary),
  ];
}
