import type { Activity, Itinerary, Transport, Weather } from "@/types/itinerary";
import {
  formatSourceLabel,
  formatSourceRefs,
  getKnowledgeSourceWarning,
} from "@/lib/sourceLabels";

function formatCost(cost: number) {
  return cost > 0 ? `¥${Math.round(cost)}` : "费用待确认";
}

function formatWeather(weather?: Weather) {
  if (!weather) {
    return "天气待确认";
  }

  const temperatures =
    weather.temperature_min !== undefined && weather.temperature_max !== undefined
      ? ` ${weather.temperature_min}-${weather.temperature_max}℃`
      : "";
  const wind = weather.wind ? ` ${weather.wind}` : "";
  const advice = weather.advice ? `，${weather.advice}` : "";
  return `${weather.condition}${temperatures}${wind}${advice}`;
}

function formatTransport(transport?: Transport) {
  if (!transport) {
    return "交通待确认";
  }

  const distance =
    transport.distance_km > 0 ? `${transport.distance_km.toFixed(1)}km` : "";
  const duration =
    transport.duration_min > 0 ? `${Math.round(transport.duration_min)}分钟` : "";
  const summary = [transport.mode, distance, duration].filter(Boolean).join(" / ");
  return transport.description ? `${summary}，${transport.description}` : summary;
}

function hasRating(rating?: number): rating is number {
  return typeof rating === "number" && Number.isFinite(rating) && rating > 0;
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

function isTransportActivity(activity: Activity) {
  return activity.place_type === "交通";
}

const ROUTE_WARNING_LABELS = [
  "路线待确认",
  "交通待确认",
  "交通方式待确认",
  "转场待确认",
  "转场路线待确认",
  "到达路线待确认",
];

function isRouteWarning(warning: string) {
  return ROUTE_WARNING_LABELS.includes(warning);
}

function formatWarning(activity: Activity, warning: string) {
  if (!isRouteWarning(warning)) {
    return warning;
  }

  return isTransportActivity(activity) ? "班次/交通方式待确认" : "到达路线待确认";
}

function formatWarnings(activity: Activity, warnings: string[]) {
  return Array.from(
    new Set(warnings.map((warning) => formatWarning(activity, warning))),
  );
}

function formatRating(rating?: number) {
  return hasRating(rating) ? `${rating.toFixed(1)} 分` : "评分待确认";
}

function formatVerification(activity: Activity) {
  const sourceText = [activity.source, ...(activity.source_refs ?? [])]
    .filter(Boolean)
    .join(" ");

  if (activity.is_verified === true || /高德|amap|poi/i.test(sourceText)) {
    return isTransportActivity(activity) ? "站点已验证" : "地点已验证";
  }

  if (activity.is_verified === false) {
    return isTransportActivity(activity) ? "站点待核验" : "地点待核验";
  }

  return "未标记";
}

function getExportWarnings(activity: Activity) {
  const warnings = new Set(activity.warnings?.filter(Boolean) ?? []);

  if (!hasValidCoordinates(activity)) {
    warnings.add("坐标待确认");
  }

  if (!isTransportActivity(activity) && !hasRating(activity.rating)) {
    warnings.add("评分待确认");
  } else {
    warnings.delete("评分待确认");
  }

  if (!activity.source && activity.is_verified !== true) {
    warnings.add("来源待确认");
  }

  const knowledgeWarning = getKnowledgeSourceWarning(
    activity.source,
    activity.source_refs,
  );
  if (knowledgeWarning) {
    warnings.add(knowledgeWarning);
  }

  if (
    activity.transport &&
    (activity.transport.distance_km <= 0 || activity.transport.duration_min <= 0)
  ) {
    warnings.add("到达路线待确认");
  } else {
    ROUTE_WARNING_LABELS.forEach((warning) => warnings.delete(warning));
  }

  return Array.from(warnings);
}

function formatSource(activity: Activity) {
  const source = formatSourceLabel(activity.source, activity.source_refs);
  const refs = formatSourceRefs(activity.source_refs);
  if (refs.length === 0) {
    return source;
  }

  return `${source}（参考：${refs.join("、")}）`;
}

function formatEvidence(activity: Activity) {
  const locationLabel = isTransportActivity(activity) ? "站点/位置" : "地址";
  const parts = [
    `${locationLabel}: ${activity.address ?? `${locationLabel}待确认`}`,
    isTransportActivity(activity) ? "" : `评分: ${formatRating(activity.rating)}`,
    `来源: ${formatSource(activity)}`,
    `验证: ${formatVerification(activity)}`,
  ].filter(Boolean);

  return parts.join("；");
}

function activityToMarkdown(activity: Activity) {
  const warnings = formatWarnings(activity, getExportWarnings(activity));

  return [
    `- **${activity.time_slot}｜${activity.place_name}**`,
    `  - 类型：${activity.place_type}`,
    `  - 安排：${activity.description}`,
    `  - 可信度：${formatEvidence(activity)}`,
    warnings.length > 0 ? `  - 待确认：${warnings.join("；")}` : "",
    `  - 交通：${formatTransport(activity.transport)}`,
    `  - 费用：${formatCost(activity.cost)}`,
  ]
    .filter(Boolean)
    .join("\n");
}

function activityToPlainText(activity: Activity) {
  const warnings = formatWarnings(activity, getExportWarnings(activity));

  return [
    `${activity.time_slot} ${activity.place_name}`,
    `类型: ${activity.place_type}`,
    `安排: ${activity.description}`,
    `可信度: ${formatEvidence(activity)}`,
    warnings.length > 0 ? `待确认: ${warnings.join("；")}` : "",
    `交通: ${formatTransport(activity.transport)}`,
    `费用: ${formatCost(activity.cost)}`,
  ]
    .filter(Boolean)
    .join("\n");
}

export function itineraryToMarkdown(itinerary: Itinerary) {
  const lines = [
    `# ${itinerary.destination}行程`,
    "",
    itinerary.summary ? `> ${itinerary.summary}` : "",
    "",
    `- 预计总费用：${formatCost(itinerary.total_cost)}`,
    itinerary.budget ? `- 预算上限：${formatCost(itinerary.budget)}` : "",
    "",
  ].filter((line, index, values) => line || values[index - 1]);

  for (const day of itinerary.days) {
    lines.push(`## Day ${day.day}｜${day.date}`);
    lines.push("");
    lines.push(`天气：${formatWeather(day.weather)}`);
    lines.push("");
    lines.push(...day.activities.map(activityToMarkdown));
    lines.push("");
  }

  return `${lines.join("\n").trim()}\n`;
}

export function itineraryToPlainText(itinerary: Itinerary) {
  const lines = [
    `${itinerary.destination}行程`,
    itinerary.summary ?? "",
    `预计总费用: ${formatCost(itinerary.total_cost)}`,
    itinerary.budget ? `预算上限: ${formatCost(itinerary.budget)}` : "",
    "",
  ].filter((line, index, values) => line || values[index - 1]);

  for (const day of itinerary.days) {
    lines.push(`Day ${day.day} ${day.date}`);
    lines.push(`天气: ${formatWeather(day.weather)}`);
    lines.push(...day.activities.map(activityToPlainText));
    lines.push("");
  }

  return `${lines.join("\n").trim()}\n`;
}

export function itineraryFilename(itinerary: Itinerary, extension: "md" | "txt") {
  const destination = itinerary.destination.replace(/[^\p{L}\p{N}-]+/gu, "-");
  return `${destination || "itinerary"}-${itinerary.days.length}d.${extension}`;
}

export function downloadTextFile(
  filename: string,
  content: string,
  mimeType = "text/plain;charset=utf-8",
) {
  if (typeof document === "undefined") {
    return;
  }

  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
