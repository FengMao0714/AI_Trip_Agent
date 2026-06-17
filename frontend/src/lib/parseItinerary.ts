import type {
  Activity,
  ActivityType,
  DayPlan,
  Itinerary,
  Transport,
  TransportMode,
  Weather,
} from "@/types/itinerary";

const activityTypes: ActivityType[] = ["景点", "餐厅", "住宿", "交通", "其他"];
const activityTypeAliases: Record<string, ActivityType> = {
  景区: "景点",
  公园: "景点",
  博物馆: "景点",
  浴场: "景点",
  海滩: "景点",
  海水浴场: "景点",
  餐饮: "餐厅",
  饭店: "餐厅",
  酒楼: "餐厅",
  海鲜: "餐厅",
  咖啡: "餐厅",
  酒店: "住宿",
  民宿: "住宿",
  客栈: "住宿",
  交通枢纽: "交通",
  高铁: "交通",
  动车: "交通",
  火车: "交通",
  车站: "交通",
  机场: "交通",
  航班: "交通",
  返程: "交通",
  退房: "交通",
  离店: "交通",
  前往: "交通",
  去往: "交通",
  转场: "交通",
  出发: "交通",
  抵达: "交通",
  地铁: "交通",
  公交: "交通",
  打车: "交通",
  接驳: "交通",
};
const transportModes: TransportMode[] = [
  "步行",
  "公交",
  "地铁",
  "打车",
  "驾车",
  "自驾",
  "包车",
  "网约车",
  "接驳",
  "飞机",
  "火车",
  "骑行",
  "未知",
];

const transportModeAliases: Record<string, TransportMode> = {
  地铁站: "地铁",
  轨道交通: "地铁",
  地铁: "地铁",
  步行: "步行",
  徒步: "步行",
  公交车: "公交",
  巴士: "公交",
  出租车: "打车",
  打车: "打车",
  网约: "网约车",
  网约车: "网约车",
  自驾车: "自驾",
  租车: "自驾",
  SUV: "自驾",
  包车: "包车",
  接驳车: "接驳",
  景区接驳: "接驳",
  市郊铁路: "火车",
  高铁: "火车",
  火车: "火车",
  航班: "飞机",
  飞机: "飞机",
  公共交通: "公交",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function asString(value: unknown, fallback = "") {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }

  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }

  return fallback;
}

function asNumber(value: unknown, fallback = 0) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const parsed = Number(value.replace(/[^\d.-]/g, ""));
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return fallback;
}

function asOptionalNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }

  if (typeof value === "string") {
    const normalized = value.replace(/[^\d.-]/g, "");
    if (!normalized || normalized === "-" || normalized === ".") {
      return undefined;
    }

    const parsed = Number(normalized);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }

  return undefined;
}

function asBoolean(value: unknown) {
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "number" && Number.isFinite(value)) {
    return value !== 0;
  }

  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    if (["true", "yes", "y", "1", "是", "已验证", "verified"].includes(normalized)) {
      return true;
    }

    if (["false", "no", "n", "0", "否", "未验证", "待确认"].includes(normalized)) {
      return false;
    }
  }

  return undefined;
}

function normalizeRiskLevel(value: unknown): Activity["risk_level"] {
  const raw = asString(value).toLowerCase();
  if (["low", "medium", "high"].includes(raw)) {
    return raw as Activity["risk_level"];
  }

  if (["低", "提示", "轻微"].includes(raw)) {
    return "low";
  }

  if (["中", "注意", "中等"].includes(raw)) {
    return "medium";
  }

  if (["高", "重点", "严重"].includes(raw)) {
    return "high";
  }

  return undefined;
}

function asStringArray(value: unknown) {
  if (Array.isArray(value)) {
    return value.map((item) => asString(item)).filter(Boolean);
  }

  const singleValue = asString(value);
  return singleValue ? [singleValue] : [];
}

function pick(source: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = source[key];
    if (value !== undefined && value !== null) {
      return value;
    }
  }

  return undefined;
}

function normalizeActivityType(value: unknown, fallbackText = ""): ActivityType {
  const raw = asString(value);
  if (activityTypes.includes(raw as ActivityType)) {
    return raw as ActivityType;
  }

  const text = `${raw} ${fallbackText}`;
  for (const [keyword, type] of Object.entries(activityTypeAliases)) {
    if (text.includes(keyword)) {
      return type;
    }
  }

  return "其他";
}

function normalizeTransportMode(value: unknown): TransportMode {
  const raw = asString(value);
  if (transportModes.includes(raw as TransportMode)) {
    return raw as TransportMode;
  }

  for (const [keyword, mode] of Object.entries(transportModeAliases)) {
    if (raw.includes(keyword)) {
      return mode;
    }
  }

  return "未知";
}

function parseWeather(input: unknown): Weather | undefined {
  if (!isRecord(input)) {
    return undefined;
  }

  const condition = asString(pick(input, ["condition", "weather", "text"]), "天气待确认");
  const weather: Weather = { condition };
  const temperatureMin = pick(input, ["temperature_min", "temperatureMin", "temp_min"]);
  const temperatureMax = pick(input, ["temperature_max", "temperatureMax", "temp_max"]);
  const wind = asString(input.wind);
  const advice = asString(input.advice);

  if (temperatureMin !== undefined) {
    weather.temperature_min = asNumber(temperatureMin);
  }

  if (temperatureMax !== undefined) {
    weather.temperature_max = asNumber(temperatureMax);
  }

  if (wind) {
    weather.wind = wind;
  }

  if (advice) {
    weather.advice = advice;
  }

  return weather;
}

function parseTransport(input: unknown): Transport | undefined {
  if (!isRecord(input)) {
    return undefined;
  }

  const description = asString(input.description);
  const mode = normalizeTransportMode(input.mode);
  return {
    mode: mode === "未知" ? normalizeTransportMode(description) : mode,
    distance_km: asNumber(pick(input, ["distance_km", "distanceKm", "distance"])),
    duration_min: asNumber(pick(input, ["duration_min", "durationMin", "duration"])),
    ...(description ? { description } : {}),
  };
}

function parseCoordinates(input: Record<string, unknown>) {
  const location = isRecord(input.location) ? input.location : {};

  return {
    lng: asNumber(
      pick(input, ["lng", "lon", "longitude"]) ??
        pick(location, ["lng", "lon", "longitude"]),
    ),
    lat: asNumber(
      pick(input, ["lat", "latitude"]) ?? pick(location, ["lat", "latitude"]),
    ),
  };
}

function parseActivity(input: unknown, index: number): Activity | null {
  if (!isRecord(input)) {
    return null;
  }

  const { lng, lat } = parseCoordinates(input);
  const description = asString(input.description, "暂无详细说明。");
  const transport = parseTransport(input.transport);
  const placeName = asString(
    pick(input, ["place_name", "placeName", "name", "title"]),
    `待定地点 ${index + 1}`,
  );
  const placeType = normalizeActivityType(
    pick(input, ["place_type", "placeType", "type", "category"]),
    `${placeName} ${description}`,
  );
  const address = asString(
    pick(input, ["address", "addr", "formatted_address", "formattedAddress"]),
  );
  const rating = asOptionalNumber(pick(input, ["rating", "score", "stars"]));
  const confidence = asOptionalNumber(
    pick(input, ["confidence", "confidence_score", "confidenceScore"]),
  );
  const indoor = asBoolean(pick(input, ["indoor", "is_indoor", "isIndoor"]));
  const openingHours = asString(
    pick(input, ["opening_hours", "openingHours", "hours"]),
  );
  const reservationRequired = asBoolean(
    pick(input, [
      "reservation_required",
      "reservationRequired",
      "needs_reservation",
      "needsReservation",
    ]),
  );
  const riskLevel = normalizeRiskLevel(
    pick(input, ["risk_level", "riskLevel", "risk"]),
  );
  const source = asString(
    pick(input, ["source", "source_desc", "sourceDescription", "source_type", "sourceType"]),
  );
  const sourceUrl = asString(
    pick(input, ["source_url", "sourceUrl", "url", "reference_url", "referenceUrl"]),
  );
  const sourceRefs = asStringArray(
    pick(input, ["source_refs", "sourceRefs", "references", "refs"]),
  );
  const isVerified = asBoolean(
    pick(input, ["is_verified", "isVerified", "verified"]),
  );
  const warnings = asStringArray(
    pick(input, [
      "warnings",
      "pending_items",
      "pendingItems",
      "uncertainties",
      "notes_to_confirm",
      "notesToConfirm",
    ]),
  );

  return {
    time_slot: asString(
      pick(input, ["time_slot", "timeSlot", "time", "time_range"]),
      "时间待定",
    ),
    place_name: placeName,
    place_type: placeType,
    lng,
    lat,
    description,
    cost: asNumber(pick(input, ["cost", "price", "fee"])),
    ...(address ? { address } : {}),
    ...(confidence !== undefined ? { confidence } : {}),
    ...(indoor !== undefined ? { indoor } : {}),
    ...(openingHours ? { opening_hours: openingHours } : {}),
    ...(rating !== undefined && rating > 0 ? { rating } : {}),
    ...(reservationRequired !== undefined
      ? { reservation_required: reservationRequired }
      : {}),
    ...(riskLevel ? { risk_level: riskLevel } : {}),
    ...(source ? { source } : {}),
    ...(sourceUrl ? { source_url: sourceUrl } : {}),
    ...(sourceRefs.length > 0 ? { source_refs: sourceRefs } : {}),
    ...(isVerified !== undefined ? { is_verified: isVerified } : {}),
    ...(warnings.length > 0 ? { warnings } : {}),
    ...(transport ? { transport } : {}),
  };
}

function parseDay(input: unknown, index: number): DayPlan | null {
  if (!isRecord(input)) {
    return null;
  }

  const activitiesInput = pick(input, ["activities", "items", "plans"]);
  const activities = Array.isArray(activitiesInput)
    ? activitiesInput
        .map((activity, activityIndex) => parseActivity(activity, activityIndex))
        .filter((activity): activity is Activity => activity !== null)
    : [];
  const weather = parseWeather(input.weather);
  const riskSummary = asStringArray(
    pick(input, ["risk_summary", "riskSummary", "risks", "alerts"]),
  );

  return {
    day: asNumber(input.day, index + 1),
    date: asString(input.date, `第 ${index + 1} 天`),
    activities,
    ...(riskSummary.length > 0 ? { risk_summary: riskSummary } : {}),
    ...(weather ? { weather } : {}),
  };
}

function parseGenerationSource(input: unknown) {
  if (!isRecord(input)) {
    return undefined;
  }

  const kind = asString(input.kind);
  const label = asString(input.label);
  if (!kind || !label) {
    return undefined;
  }

  const detail = asString(input.detail);
  const tools = asStringArray(input.tools);
  const isFallback = asBoolean(
    pick(input, ["is_fallback", "isFallback", "fallback"]),
  );

  return {
    kind,
    label,
    ...(detail ? { detail } : {}),
    ...(tools.length > 0 ? { tools } : {}),
    ...(isFallback !== undefined ? { is_fallback: isFallback } : {}),
  };
}

export function parseItinerary(input: unknown): Itinerary | null {
  const payload =
    isRecord(input) && isRecord(input.itinerary) ? input.itinerary : input;

  if (!isRecord(payload)) {
    return null;
  }

  const daysInput = pick(payload, ["days", "day_plans", "dayPlans"]);
  const days = Array.isArray(daysInput)
    ? daysInput
        .map((day, index) => parseDay(day, index))
        .filter((day): day is DayPlan => day !== null)
    : [];

  const computedTotal = days.reduce(
    (total, day) =>
      total +
      day.activities.reduce((dayTotal, activity) => dayTotal + activity.cost, 0),
    0,
  );

  const destination = asString(
    pick(payload, ["destination", "city", "dest"]),
    "未命名目的地",
  );
  const summary = asString(payload.summary);
  const budgetValue = pick(payload, ["budget", "total_budget", "totalBudget"]);
  const qualityScore = asOptionalNumber(
    pick(payload, ["quality_score", "qualityScore", "score"]),
  );
  const totalCostValue = pick(payload, ["total_cost", "totalCost", "cost"]);
  const startDate = asString(
    pick(payload, ["start_date", "startDate", "trip_start_date", "tripStartDate"]),
  );
  const generationSource = parseGenerationSource(
    pick(payload, ["generation_source", "generationSource", "source_meta"]),
  );

  return {
    destination,
    days,
    total_cost: asNumber(totalCostValue, computedTotal),
    ...(budgetValue !== undefined ? { budget: asNumber(budgetValue) } : {}),
    ...(qualityScore !== undefined ? { quality_score: qualityScore } : {}),
    ...(startDate ? { start_date: startDate } : {}),
    ...(summary ? { summary } : {}),
    ...(generationSource ? { generation_source: generationSource } : {}),
  };
}
