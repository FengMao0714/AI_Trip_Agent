"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import {
  AlertTriangle,
  BedDouble,
  BookOpen,
  Clock3,
  CheckCircle2,
  Coffee,
  ExternalLink,
  Footprints,
  Landmark,
  MapPin,
  PencilLine,
  RefreshCw,
  SendHorizonal,
  ShieldCheck,
  Soup,
  Star,
  TrainFront,
  WalletCards,
} from "lucide-react";

import { CostBadge } from "@/components/itinerary/CostBadge";
import { Textarea } from "@/components/ui/textarea";
import {
  formatSourceLabel,
  formatSourceRefs,
  getKnowledgeSourceWarning,
  hasTrustedKnowledgeSource,
} from "@/lib/sourceLabels";
import type { Activity, ActivityType } from "@/types/itinerary";

interface ActivityItemProps {
  activity: Activity;
  dayNumber: number;
  isQuickAdjustDisabled?: boolean;
  onQuickAdjust?: (instruction: string) => void;
}

const typeIcon: Record<ActivityType, typeof MapPin> = {
  景点: Landmark,
  餐厅: Soup,
  住宿: BedDouble,
  交通: TrainFront,
  其他: MapPin,
};

const typeColor: Record<ActivityType, string> = {
  景点: "bg-sky-400/10 text-sky-200 ring-sky-300/20",
  餐厅: "bg-amber-400/10 text-amber-200 ring-amber-300/20",
  住宿: "bg-violet-400/10 text-violet-200 ring-violet-300/20",
  交通: "bg-teal-400/10 text-teal-200 ring-teal-300/20",
  其他: "bg-white/[0.06] text-stone-300 ring-white/10",
};

interface ConfidenceBadge {
  label: string;
  className: string;
  icon: typeof MapPin;
  title?: string;
}

const ROUTE_WARNING_LABELS = [
  "路线待确认",
  "交通待确认",
  "交通方式待确认",
  "转场待确认",
  "转场路线待确认",
  "到达路线待确认",
];
const ROUTE_WARNING_TITLE =
  "路线指从上一站或出发点到当前活动的交通方式、距离和耗时。";

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

function hasRating(rating?: number): rating is number {
  return typeof rating === "number" && Number.isFinite(rating) && rating > 0;
}

function formatRating(rating?: number) {
  return hasRating(rating) ? `${rating.toFixed(1)} 分` : "评分待确认";
}

function getActivityConfidence(activity: Activity, warnings: string[]) {
  if (typeof activity.confidence === "number" && Number.isFinite(activity.confidence)) {
    return Math.max(0, Math.min(100, Math.round(activity.confidence)));
  }

  let score = 88;
  if (!hasValidCoordinates(activity)) {
    score -= 18;
  }
  if (!activity.source && activity.is_verified !== true) {
    score -= 10;
  }
  if (activity.is_verified === true) {
    score += 6;
  }
  if (!hasRating(activity.rating) && activity.place_type !== "交通") {
    score -= 4;
  }
  score -= Math.min(24, warnings.length * 5);
  return Math.max(45, Math.min(98, score));
}

const riskClassName: Record<NonNullable<Activity["risk_level"]>, string> = {
  low: "bg-sky-400/10 text-sky-200 ring-sky-300/20",
  medium: "bg-amber-400/10 text-amber-200 ring-amber-300/20",
  high: "bg-red-500/10 text-red-200 ring-red-400/20",
};

const riskLabel: Record<NonNullable<Activity["risk_level"]>, string> = {
  low: "低风险",
  medium: "需注意",
  high: "高风险",
};

function inferActivityType(activity: Activity): ActivityType {
  if (activity.place_type !== "其他") {
    return activity.place_type;
  }

  const text = `${activity.place_name} ${activity.description}`;
  if (/高铁|动车|火车|车站|机场|航班|返程|退房|离店|前往|去往|转场|出发|抵达|地铁|公交|打车|接驳/u.test(text)) {
    return "交通";
  }

  return activity.place_type;
}

function needsPoiRating(activityType: ActivityType) {
  return activityType !== "交通";
}

function hasUnconfirmedTransport(activity: Activity) {
  const { transport } = activity;
  return Boolean(
    transport &&
      (transport.distance_km <= 0 || transport.duration_min <= 0),
  );
}

function isRouteWarning(warning: string) {
  return ROUTE_WARNING_LABELS.includes(warning);
}

function displayWarningLabel(warning: string, activityType: ActivityType) {
  if (!isRouteWarning(warning)) {
    return warning;
  }

  return activityType === "交通" ? "班次/交通方式待确认" : "到达路线待确认";
}

function displayWarnings(warnings: string[], activityType: ActivityType) {
  return Array.from(
    new Set(warnings.map((warning) => displayWarningLabel(warning, activityType))),
  );
}

function cleanupWarningForActivityType(warning: string, activityType: ActivityType) {
  if (activityType !== "交通") {
    return warning;
  }

  return warning
    .replace(/评分待确认/g, "")
    .replace(/[；;，,、]\s*$/u, "")
    .replace(/^[；;，,、]\s*/u, "")
    .trim();
}

function getWarnings(activity: Activity, activityType: ActivityType) {
  const warnings = new Set(
    (activity.warnings?.filter(Boolean) ?? [])
      .map((warning) => cleanupWarningForActivityType(warning, activityType))
      .filter(Boolean),
  );

  if (!hasValidCoordinates(activity)) {
    warnings.add("坐标待确认");
  }

  if (needsPoiRating(activityType) && !hasRating(activity.rating)) {
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

  if (hasUnconfirmedTransport(activity)) {
    warnings.add("到达路线待确认");
  } else {
    ROUTE_WARNING_LABELS.forEach((warning) => warnings.delete(warning));
  }

  return Array.from(warnings);
}

function getConfidenceBadges(
  activity: Activity,
  activityType: ActivityType,
  warnings: string[],
) {
  const sourceText = [activity.source, ...(activity.source_refs ?? [])]
    .filter(Boolean)
    .join(" ");
  const badges: ConfidenceBadge[] = [];
  const warningSet = new Set(warnings);
  const hasVerifiedSource =
    activity.is_verified === true || /高德|amap|poi/i.test(sourceText);

  function addPendingBadge(label: string, title?: string) {
    if (badges.some((badge) => badge.label === label)) {
      return;
    }

    badges.push({
      label,
      className: "bg-amber-400/10 text-amber-200 ring-amber-300/20",
      icon: AlertTriangle,
      title,
    });
  }

  if (hasVerifiedSource) {
    badges.push({
      label: activityType === "交通" ? "站点已验证" : "地点已验证",
      className: "bg-emerald-400/10 text-emerald-200 ring-emerald-300/20",
      icon: CheckCircle2,
    });
  }

  if (hasTrustedKnowledgeSource(activity.source, activity.source_refs)) {
    badges.push({
      label: "本地知识库推荐",
      className: "bg-sky-400/10 text-sky-200 ring-sky-300/20",
      icon: BookOpen,
    });
  }

  if (warningSet.has("坐标待确认")) {
    addPendingBadge("坐标待确认");
  }

  if (warnings.some(isRouteWarning)) {
    addPendingBadge(
      activityType === "交通" ? "班次待确认" : "到达路线待确认",
      ROUTE_WARNING_TITLE,
    );
  }

  if (warningSet.has("评分待确认")) {
    addPendingBadge("评分缺失");
  }

  if (warningSet.has("来源待确认")) {
    addPendingBadge("来源待确认");
  }

  if (warningSet.has("知识库依据待核验")) {
    addPendingBadge("知识库依据待核验");
  }

  for (const warning of warnings) {
    if (
      [
        "坐标待确认",
        "评分待确认",
        "来源待确认",
        "知识库依据待核验",
      ].includes(warning) ||
      isRouteWarning(warning)
    ) {
      continue;
    }
    addPendingBadge(warning);
  }

  if (activity.is_verified === false && warnings.length === 0) {
    addPendingBadge(activityType === "交通" ? "班次待确认" : "地点待核验");
  }

  if (badges.length === 0 && activity.source) {
    badges.push({
      label: "来源已标注",
      className: "bg-white/[0.06] text-stone-300 ring-white/10",
      icon: BookOpen,
    });
  }

  return badges;
}

function buildQuickAdjustInstruction(
  action: "replace" | "lessWalking" | "addRest" | "lowerBudget",
  dayNumber: number,
  activity: Activity,
) {
  const target = `第 ${dayNumber} 天 ${activity.time_slot} 的 ${activity.place_name}`;
  const keepUnchanged = "其余日期和未提到的活动保持不变，请返回完整行程 JSON。";

  switch (action) {
    case "replace":
      return `请把${target}换成一个同类型、距离更近且更适合当前行程节奏的地点，${keepUnchanged}`;
    case "lessWalking":
      return `请优化${target}，优先减少步行距离和转场时间，必要时替换为更近、步行更少的地点，${keepUnchanged}`;
    case "addRest":
      return `请在${target}前后增加适当休息时间，或压缩这个活动的停留时长，让当天节奏更轻松，${keepUnchanged}`;
    case "lowerBudget":
      return `请降低${target}的预算，优先替换为费用更低但类型相近的安排，${keepUnchanged}`;
  }
}

function normalizeCustomAdjustText(text: string) {
  const trimmed = text.trim();
  if (!trimmed) {
    return "";
  }

  return /[。！？!?]$/u.test(trimmed) ? trimmed : `${trimmed}。`;
}

function buildCustomQuickAdjustInstruction(
  customText: string,
  dayNumber: number,
  activity: Activity,
) {
  const normalizedText = normalizeCustomAdjustText(customText);
  if (!normalizedText) {
    return "";
  }

  return `请针对第 ${dayNumber} 天 ${activity.time_slot} 的「${activity.place_name}」进行局部微调：${normalizedText}其余日期和未提到的活动保持不变，请返回完整行程 JSON。`;
}

export function ActivityItem({
  activity,
  dayNumber,
  isQuickAdjustDisabled = false,
  onQuickAdjust,
}: ActivityItemProps) {
  const [isCustomAdjustOpen, setIsCustomAdjustOpen] = useState(false);
  const [customAdjustText, setCustomAdjustText] = useState("");
  const activityType = inferActivityType(activity);
  const Icon = typeIcon[activityType];
  const warnings = getWarnings(activity, activityType);
  const confidence = getActivityConfidence(activity, warnings);
  const warningLabels = displayWarnings(warnings, activityType);
  const confidenceBadges = getConfidenceBadges(activity, activityType, warnings);
  const sourceRefs = formatSourceRefs(activity.source_refs, 2);
  const sourceLabel =
    activity.source ?? (activity.is_verified ? "高德 POI 验证" : "来源待确认");
  const formattedSourceLabel = formatSourceLabel(sourceLabel, activity.source_refs);
  const quickActions = [
    { action: "replace" as const, label: "换一个", icon: RefreshCw },
    { action: "lessWalking" as const, label: "少走路", icon: Footprints },
    { action: "addRest" as const, label: "加休息", icon: Coffee },
    { action: "lowerBudget" as const, label: "降预算", icon: WalletCards },
  ];
  const addressLabel = activityType === "交通" ? "站点/位置" : "地址";
  const sourceLabelPrefix = activityType === "交通" ? "依据" : "来源";
  const customInstruction = buildCustomQuickAdjustInstruction(
    customAdjustText,
    dayNumber,
    activity,
  );

  function handleCustomAdjustSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onQuickAdjust || isQuickAdjustDisabled || !customInstruction) {
      return;
    }

    onQuickAdjust(customInstruction);
    setCustomAdjustText("");
    setIsCustomAdjustOpen(false);
  }

  return (
    <div className="grid grid-cols-[5rem_1.75rem_minmax(0,1fr)] gap-3">
      <time className="break-words pt-1 text-xs font-medium leading-5 text-stone-500">
        {activity.time_slot}
      </time>
      <div className="flex flex-col items-center">
        <span
          className={`flex h-7 w-7 items-center justify-center rounded-lg ring-1 ${typeColor[activityType]}`}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="mt-2 h-full min-h-6 w-px bg-teal-300/25" />
      </div>
      <div className="min-w-0 rounded-lg border border-white/10 bg-white/[0.045] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-colors hover:border-teal-300/30 hover:bg-white/[0.065]">
        <div className="mb-3 flex items-center justify-between gap-3 border-b border-white/10 pb-3">
          <span className="inline-flex items-center gap-1.5 rounded-md bg-white/[0.045] px-2 py-1 text-xs font-semibold text-stone-300 ring-1 ring-white/10">
            <ShieldCheck className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
            置信度 {confidence}
          </span>
          {activity.risk_level ? (
            <span
              className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold ring-1 ${riskClassName[activity.risk_level]}`}
            >
              <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
              {riskLabel[activity.risk_level]}
            </span>
          ) : null}
        </div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h4 className="truncate text-base font-semibold text-stone-50">
              {activity.place_name}
            </h4>
            <p className="mt-1 text-sm text-stone-500">{activityType}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {confidenceBadges.map((badge) => {
                const BadgeIcon = badge.icon;
                return (
                  <span
                    key={badge.label}
                    title={badge.title}
                    className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold ring-1 ${badge.className}`}
                  >
                    <BadgeIcon className="h-3.5 w-3.5" aria-hidden="true" />
                    {badge.label}
                  </span>
                );
              })}
            </div>
          </div>
          <CostBadge cost={activity.cost} />
        </div>
        <p className="mt-3 text-sm leading-6 text-stone-300">
          {activity.description}
        </p>
        <div className="mt-3 grid gap-2 text-xs leading-5 text-stone-400">
          <div className="flex min-w-0 items-start gap-2">
            <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-500" aria-hidden="true" />
            <span className="min-w-0 break-words">
              {addressLabel}：{activity.address ?? `${addressLabel}待确认`}
            </span>
          </div>
          {needsPoiRating(activityType) ? (
            <div className="flex min-w-0 items-start gap-2">
              <Star className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-500" aria-hidden="true" />
              <span>评分：{formatRating(activity.rating)}</span>
            </div>
          ) : null}
          {activity.opening_hours ? (
            <div className="flex min-w-0 items-start gap-2">
              <Clock3 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-500" aria-hidden="true" />
              <span className="min-w-0 break-words">
                营业/开放：{activity.opening_hours}
              </span>
            </div>
          ) : null}
          {activity.reservation_required !== undefined ? (
            <div className="flex min-w-0 items-start gap-2">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-500" aria-hidden="true" />
              <span>
                预约：{activity.reservation_required ? "建议提前预约" : "暂不要求预约"}
              </span>
            </div>
          ) : null}
          <div className="flex min-w-0 items-start gap-2">
            <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-stone-500" aria-hidden="true" />
            <span className="min-w-0 break-words">
              {sourceLabelPrefix}：{formattedSourceLabel}
              {sourceRefs.length > 0 ? `（参考：${sourceRefs.join("、")}）` : ""}
            </span>
          </div>
          {activity.source_url ? (
            <a
              href={activity.source_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex w-fit items-center gap-1 rounded-md border border-teal-300/20 bg-teal-400/10 px-2 py-1 text-xs font-medium text-teal-100 hover:bg-teal-400/15"
            >
              <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              查看来源链接
            </a>
          ) : null}
        </div>
        {warningLabels.length > 0 ? (
          <div className="mt-3 flex items-start gap-2 rounded-lg bg-amber-400/10 px-3 py-2 text-xs leading-5 text-amber-100 ring-1 ring-amber-300/20">
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>{warningLabels.slice(0, 3).join("；")}</span>
          </div>
        ) : null}
        {onQuickAdjust ? (
          <div className="mt-3 flex flex-wrap gap-2 border-t border-white/10 pt-3">
            {quickActions.map((item) => {
              const ActionIcon = item.icon;
              return (
                <button
                  key={item.action}
                  type="button"
                  disabled={isQuickAdjustDisabled}
                  className="inline-flex min-h-8 items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs font-medium text-stone-300 transition-colors hover:border-teal-300/30 hover:bg-teal-400/10 hover:text-teal-100 disabled:cursor-not-allowed disabled:opacity-50"
                  onClick={() =>
                    onQuickAdjust(
                      buildQuickAdjustInstruction(item.action, dayNumber, activity),
                    )
                  }
                >
                  <ActionIcon className="h-3.5 w-3.5" aria-hidden="true" />
                  {item.label}
                </button>
              );
            })}
            <button
              type="button"
              disabled={isQuickAdjustDisabled}
              className="inline-flex min-h-8 items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04] px-2.5 py-1 text-xs font-medium text-stone-300 transition-colors hover:border-teal-300/30 hover:bg-teal-400/10 hover:text-teal-100 disabled:cursor-not-allowed disabled:opacity-50"
              aria-expanded={isCustomAdjustOpen}
              onClick={() => setIsCustomAdjustOpen((isOpen) => !isOpen)}
            >
              <PencilLine className="h-3.5 w-3.5" aria-hidden="true" />
              自定义
            </button>
          </div>
        ) : null}
        {onQuickAdjust && isCustomAdjustOpen ? (
          <form className="mt-3 space-y-2" onSubmit={handleCustomAdjustSubmit}>
            <Textarea
              value={customAdjustText}
              disabled={isQuickAdjustDisabled}
              rows={2}
              className="min-h-16 resize-none rounded-lg border-white/10 bg-[#0b1313] text-sm text-stone-100 placeholder:text-stone-500"
              placeholder="例如：换成适合看日落的地方"
              onChange={(event) => setCustomAdjustText(event.target.value)}
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={isQuickAdjustDisabled || !customInstruction}
                className="inline-flex min-h-8 items-center gap-1.5 rounded-md bg-teal-400 px-3 py-1 text-xs font-semibold text-zinc-950 transition-colors hover:bg-teal-300 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <SendHorizonal className="h-3.5 w-3.5" aria-hidden="true" />
                发送微调
              </button>
            </div>
          </form>
        ) : null}
      </div>
    </div>
  );
}
