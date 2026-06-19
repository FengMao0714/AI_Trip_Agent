"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Database,
  FileText,
  PanelLeftClose,
  PanelLeftOpen,
  MapPinned,
  MessageSquareText,
  Radio,
  Route,
  ShieldCheck,
  WalletCards,
} from "lucide-react";

import { ChatHeader } from "@/components/layout/ChatHeader";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";
import { ExportDialog } from "@/components/itinerary/ExportDialog";
import { ItineraryView } from "@/components/itinerary/ItineraryView";
import { useChat } from "@/hooks/useChat";
import { clearSession } from "@/lib/api";
import { useChatStore } from "@/store/chatStore";
import { Button } from "@/components/ui/button";
import { getDayTitle } from "@/lib/dateDisplay";
import { getItineraryInsights } from "@/lib/itineraryInsights";
import { cn } from "@/lib/utils";
import type { Activity as TripActivity, DayPlan, Itinerary } from "@/types/itinerary";

type MobileView = "chat" | "itinerary" | "map";

interface MainLayoutProps {
  initialQuery?: string;
}

const MapView = dynamic(
  () => import("@/components/map/MapView").then((module) => module.MapView),
  {
    loading: () => (
      <div className="flex h-full min-h-[420px] items-center justify-center rounded-lg border border-teal-400/15 bg-[#07100f] text-sm text-teal-100/70">
        地图加载中
      </div>
    ),
    ssr: false,
  },
);

function WorkspaceStatusBar({
  error,
  isLoading,
  itinerary,
  thinkingStep,
}: {
  error?: string | null;
  isLoading?: boolean;
  itinerary: Itinerary | null;
  thinkingStep?: string | null;
}) {
  const insights = itinerary ? getItineraryInsights(itinerary) : null;
  const statusLabel = error
    ? "需要处理"
    : isLoading
      ? "生成中"
      : itinerary
        ? "已生成"
        : "待输入";

  return (
    <div className="border-b border-white/10 bg-[#020605]/85 px-4 py-3 text-stone-100 backdrop-blur-xl sm:px-6">
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto] xl:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex h-8 items-center gap-2 rounded-lg border border-teal-300/20 bg-teal-400/10 px-3 text-sm font-semibold text-teal-100 shadow-[0_0_30px_rgba(45,212,191,0.08)]">
              <Radio
                className={cn("h-4 w-4", isLoading && "animate-pulse")}
                aria-hidden="true"
              />
              实时 Agent 状态
            </span>
            <span
              className={cn(
                "inline-flex h-8 items-center rounded-lg px-3 text-xs font-semibold ring-1",
                error
                  ? "bg-red-500/10 text-red-200 ring-red-400/20"
                  : isLoading
                    ? "bg-amber-400/10 text-amber-200 ring-amber-300/20"
                    : itinerary
                      ? "bg-emerald-400/10 text-emerald-200 ring-emerald-300/20"
                      : "bg-white/5 text-stone-300 ring-white/10",
              )}
            >
              {statusLabel}
            </span>
          </div>
          <p className="mt-2 truncate text-sm text-stone-300/80">
            {error ??
              thinkingStep ??
              (itinerary
                ? `${itinerary.destination} · ${insights?.dayCount ?? 0} 天 · ${insights?.activityCount ?? 0} 个可执行节点`
                : "输入目的地、天数、预算和偏好后，右侧会同步生成行程、预算、风险和地图。")}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-2 sm:flex sm:items-center">
          <StatusMetric
            icon={ShieldCheck}
            label="可信执行分"
            value={insights ? `${insights.confidenceScore}` : "--"}
          />
          <StatusMetric
            icon={MapPinned}
            label="地图点位"
            value={insights ? `${insights.mapVerifiedCount}/${insights.activityCount}` : "--"}
          />
          <StatusMetric
            icon={Route}
            label="交通耗时"
            value={
              insights ? `${Math.round(insights.totalTransportMinutes / 60)}h` : "--"
            }
          />
        </div>
      </div>
    </div>
  );
}

function StatusMetric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof ShieldCheck;
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0 rounded-lg border border-white/10 bg-white/[0.045] px-3 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
      <div className="flex items-center gap-2 text-xs text-stone-400">
        <Icon className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
        <span className="truncate">{label}</span>
      </div>
      <p className="mt-1 text-sm font-semibold text-stone-100">{value}</p>
    </div>
  );
}

function DesktopOutputGrid({
  itinerary,
}: {
  itinerary: Itinerary | null;
}) {
  return (
    <>
      <MapWorkspace itinerary={itinerary} />
      <ItinerarySummaryPanel itinerary={itinerary} />
    </>
  );
}

function formatCurrency(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value)
    ? `${Math.round(value).toLocaleString("zh-CN")} 元`
    : "--";
}

function getDaySubtitle(day: DayPlan) {
  const names = day.activities
    .slice(0, 3)
    .map((activity) => activity.place_name)
    .filter(Boolean);

  return names.length > 0 ? names.join(" · ") : "等待 Agent 补全当日节点";
}

function getActivityBadge(activity: TripActivity) {
  if (activity.is_verified) {
    return "官方验证";
  }

  if (activity.source || activity.source_refs?.length) {
    return "来源可追溯";
  }

  return "待核验";
}

function MapWorkspace({ itinerary }: { itinerary: Itinerary | null }) {
  const insights = itinerary ? getItineraryInsights(itinerary) : null;

  return (
    <main className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto] overflow-hidden rounded-xl border border-white/10 bg-[#07100f]/95 shadow-[0_24px_70px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.06)]">
      <div className="min-h-0 p-3 pb-0">
        {itinerary ? (
          <MapView itinerary={itinerary} variant="immersive" />
        ) : (
          <EmptyItineraryPanel />
        )}
      </div>

      <div className="mx-3 mb-3 mt-3 grid grid-cols-4 overflow-hidden rounded-xl border border-white/10 bg-[#0b1514]/88 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
        <MapFooterStat
          icon={WalletCards}
          label="预计费用"
          value={itinerary ? formatCurrency(itinerary.total_cost) : "--"}
        />
        <MapFooterStat
          icon={MapPinned}
          label="景点数量"
          value={insights ? `${insights.activityCount} 个` : "--"}
        />
        <MapFooterStat
          icon={CalendarDays}
          label="行程天数"
          value={insights ? `${insights.dayCount} 天` : "--"}
        />
        <MapFooterStat
          icon={Clock3}
          label="总时长预估"
          value={
            insights
              ? `${Math.max(1, Math.round(insights.totalTransportMinutes / 60))} 小时`
              : "--"
          }
        />
      </div>
    </main>
  );
}

function MapFooterStat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof WalletCards;
  label: string;
  value: string;
}) {
  return (
    <div className="min-w-0 border-r border-white/10 px-4 py-3 last:border-r-0">
      <div className="flex items-center gap-2 text-xs text-stone-400">
        <Icon className="h-4 w-4 shrink-0 text-teal-300" aria-hidden="true" />
        <span className="truncate">{label}</span>
      </div>
      <p className="mt-1 truncate text-lg font-semibold text-stone-100">{value}</p>
    </div>
  );
}

function ItinerarySummaryPanel({
  itinerary,
}: {
  itinerary: Itinerary | null;
}) {
  const [expandedDayNumbers, setExpandedDayNumbers] = useState<Set<number>>(
    () => new Set(itinerary?.days[0] ? [itinerary.days[0].day] : []),
  );

  useEffect(() => {
    setExpandedDayNumbers(new Set(itinerary?.days[0] ? [itinerary.days[0].day] : []));
  }, [itinerary]);

  if (!itinerary) {
    return (
      <aside className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-3">
        <EmptyItineraryPanel compact />
        <VerificationPanel itinerary={null} />
      </aside>
    );
  }

  function toggleDay(dayNumber: number) {
    setExpandedDayNumbers((current) => {
      const next = new Set(current);
      if (next.has(dayNumber)) {
        next.delete(dayNumber);
      } else {
        next.add(dayNumber);
      }
      return next;
    });
  }

  return (
    <aside className="grid min-h-0 grid-rows-[minmax(0,1fr)_auto] gap-3">
      <div className="min-h-0 space-y-3 overflow-auto pr-1">
        <section className="overflow-hidden rounded-xl border border-white/10 bg-[#07100f]/95 text-stone-100 shadow-[0_24px_70px_rgba(0,0,0,0.36),inset_0_1px_0_rgba(255,255,255,0.06)]">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-teal-200/75">
                Itinerary
              </p>
              <h3 className="mt-1 text-base font-semibold text-amber-50">行程</h3>
            </div>
            <span className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.04] px-3 text-xs font-medium text-stone-300">
              <FileText className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
              结构化行程
            </span>
          </div>

          <div className="space-y-3 p-3">
            <div className="space-y-2">
              {itinerary.days.map((day) => {
                const isExpanded = expandedDayNumbers.has(day.day);
                return (
                  <DayAccordionCard
                    key={day.day}
                    day={day}
                    isExpanded={isExpanded}
                    onToggle={() => toggleDay(day.day)}
                  />
                );
              })}
            </div>
          </div>
        </section>

        <VerificationPanel itinerary={itinerary} />
      </div>

      <div className="rounded-xl border border-amber-300/20 bg-[linear-gradient(135deg,rgba(245,158,11,0.18),rgba(20,184,166,0.10))] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
        <ExportDialog
          itinerary={itinerary}
          triggerClassName="h-11 w-full justify-center border-amber-200/35 bg-amber-300/90 font-semibold text-zinc-950 hover:bg-amber-200 hover:text-zinc-950"
          triggerLabel="导出行程方案"
        />
      </div>
    </aside>
  );
}

function DayAccordionCard({
  day,
  isExpanded,
  onToggle,
}: {
  day: DayPlan;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <article
      className={cn(
        "overflow-hidden rounded-lg border transition-colors",
        isExpanded
          ? "border-teal-300/35 bg-teal-400/12 text-teal-50 shadow-[0_0_32px_rgba(20,184,166,0.12)]"
          : "border-white/10 bg-white/[0.035] text-stone-300",
      )}
    >
      <button
        type="button"
        className="w-full px-3 py-2.5 text-left hover:bg-white/[0.035]"
        aria-expanded={isExpanded}
        onClick={onToggle}
      >
        <div className="flex items-center justify-between gap-3">
          <span className="inline-flex items-center gap-2 font-semibold">
            <CalendarDays
              className={cn(
                "h-4 w-4",
                isExpanded ? "text-teal-200" : "text-stone-500",
              )}
              aria-hidden="true"
            />
            Day {day.day}
          </span>
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform",
              isExpanded && "rotate-180 text-teal-200",
            )}
            aria-hidden="true"
          />
        </div>
        <p className="mt-1 truncate text-sm font-medium text-stone-200">
          {getDayTitle(day)}
        </p>
        <p className="mt-0.5 truncate text-xs text-stone-500">
          {getDaySubtitle(day)}
        </p>
      </button>

      {isExpanded ? (
        <div className="space-y-2 border-t border-white/10 bg-black/15 p-3">
          {day.weather?.advice ? (
            <div className="rounded-md border border-amber-300/20 bg-amber-400/10 px-3 py-2 text-xs leading-5 text-amber-100">
              {day.weather.advice}
            </div>
          ) : null}
          {day.activities.length > 0 ? (
            day.activities.map((activity, index) => (
              <ActivityRow
                key={`${day.day}-${activity.time_slot}-${activity.place_name}-${index}`}
                activity={activity}
                index={index}
              />
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-white/10 bg-white/[0.035] px-3 py-2 text-xs leading-5 text-stone-400">
              当天还没有可展示的活动节点，等待 Agent 返回更多结构化行程。
            </div>
          )}
        </div>
      ) : null}
    </article>
  );
}

function ActivityRow({
  activity,
  index,
}: {
  activity: TripActivity;
  index: number;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.045] p-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-teal-300/20 bg-teal-400/10 text-xs font-semibold text-teal-100">
          {index + 1}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-stone-100">
                {activity.place_name}
              </p>
              <p className="mt-0.5 truncate text-xs text-stone-500">
                {activity.place_type}
                {activity.address ? ` · ${activity.address}` : ""}
              </p>
            </div>
            <span className="shrink-0 rounded-md border border-amber-300/20 bg-amber-400/10 px-2 py-1 text-xs font-semibold text-amber-100">
              {activity.cost > 0 ? formatCurrency(activity.cost) : "免费"}
            </span>
          </div>

          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span className="inline-flex items-center gap-1 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-stone-300">
              <Clock3 className="h-3.5 w-3.5 text-amber-200" aria-hidden="true" />
              {activity.time_slot}
            </span>
            <span className="rounded-md border border-teal-300/20 bg-teal-400/10 px-2 py-1 font-medium text-teal-100">
              {getActivityBadge(activity)}
            </span>
            {activity.rating ? (
              <span className="rounded-md border border-sky-300/20 bg-sky-400/10 px-2 py-1 font-medium text-sky-100">
                评分 {activity.rating}
              </span>
            ) : null}
          </div>

          <p className="mt-2 line-clamp-3 text-xs leading-5 text-stone-400">
            {activity.description}
          </p>
        </div>
      </div>
    </div>
  );
}

function VerificationPanel({ itinerary }: { itinerary: Itinerary | null }) {
  const insights = itinerary ? getItineraryInsights(itinerary) : null;
  const source = itinerary?.generation_source;
  const sourceCoverage = insights?.sourceCoverage ?? 0;
  const verifiedCount = insights?.verifiedCount ?? 0;
  const pendingCount = insights
    ? insights.warningCount + insights.coordinateMissingCount
    : 0;
  const tools = source?.tools?.length ? source.tools : ["poi_search", "route_plan", "weather"];

  return (
    <section className="overflow-hidden rounded-xl border border-white/10 bg-[radial-gradient(circle_at_88%_18%,rgba(45,212,191,0.18),transparent_32%),linear-gradient(145deg,rgba(11,20,19,0.96),rgba(4,9,9,0.98))] p-4 text-stone-100 shadow-[0_22px_60px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.06)]">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-200/80">
            Source Validation
          </p>
          <h3 className="mt-1 text-base font-semibold text-stone-100">
            来源与验证
          </h3>
          <p className="mt-2 text-sm text-teal-200">
            {insights ? `全链路通过 ${sourceCoverage}%` : "等待行程生成后核验"}
          </p>
        </div>
        <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl border border-teal-300/25 bg-teal-400/10 text-teal-200 shadow-[0_0_40px_rgba(45,212,191,0.18)]">
          <ShieldCheck className="h-7 w-7" aria-hidden="true" />
        </div>
      </div>

      <div className="mt-4 grid gap-2 text-sm">
        <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
          <span className="inline-flex items-center gap-2 text-stone-300">
            <CheckCircle2 className="h-4 w-4 text-teal-300" aria-hidden="true" />
            已验证地点
          </span>
          <span className="font-semibold text-stone-100">{verifiedCount} 个</span>
        </div>
        <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
          <span className="inline-flex items-center gap-2 text-stone-300">
            <AlertTriangle className="h-4 w-4 text-amber-300" aria-hidden="true" />
            待确认事项
          </span>
          <span className="font-semibold text-stone-100">{pendingCount} 项</span>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
          <div className="flex items-center gap-2 text-stone-300">
            <Database className="h-4 w-4 text-sky-300" aria-hidden="true" />
            数据来源
          </div>
          <p className="mt-1 text-sm font-medium text-stone-100">
            {source?.label ?? "AI 生成 · Agent 工具链"}
          </p>
          {source?.detail ? (
            <p className="mt-1 text-xs leading-5 text-stone-400">{source.detail}</p>
          ) : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {tools.map((tool) => (
          <span
            key={tool}
            className="rounded-md border border-teal-300/20 bg-teal-400/10 px-2 py-1 text-xs font-medium text-teal-100"
          >
            {tool}
          </span>
        ))}
      </div>
    </section>
  );
}

function EmptyItineraryPanel({ compact = false }: { compact?: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-xl border border-dashed border-teal-300/20 bg-[radial-gradient(circle_at_top,rgba(20,184,166,0.13),transparent_38%),linear-gradient(135deg,rgba(8,15,15,0.96),rgba(2,6,6,0.98))] px-6 text-center text-stone-100",
        compact ? "min-h-[360px]" : "min-h-[420px]",
      )}
    >
      <div className="max-w-sm">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-teal-300/20 bg-teal-400/10 text-teal-200 shadow-[0_0_38px_rgba(45,212,191,0.14)]">
          <Activity className="h-5 w-5" aria-hidden="true" />
        </div>
        <p className="mt-4 text-sm font-semibold text-stone-100">还没有生成行程</p>
        <p className="mt-2 text-sm leading-6 text-stone-400">
          发送目的地、天数、预算和偏好后，这里会展示真实生成的行程和地图标注。
        </p>
        <div className="mt-4 grid grid-cols-3 gap-2 text-xs text-stone-400">
          {["行程", "预算", "地图"].map((item) => (
            <span
              key={item}
              className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-1"
            >
              {item}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function MainLayout({ initialQuery = "" }: MainLayoutProps) {
  const {
    messages,
    itinerary: generatedItinerary,
    isLoading,
    error,
    isReasoningCollapsed,
    reasoningEvents,
    thinkingStep,
    sendMessage,
    sessionId,
    sessions,
    setReasoningCollapsed,
    reset,
    switchSession,
    deleteSession,
  } = useChat();
  const [initialInput, setInitialInput] = useState(initialQuery);
  const [mobileView, setMobileView] = useState<MobileView>("chat");
  const [isChatCollapsed, setChatCollapsed] = useState(false);
  const visibleItinerary = generatedItinerary;
  const lastMessage = messages[messages.length - 1];
  const showThinking =
    isLoading &&
    (lastMessage?.role !== "assistant" || lastMessage.content.length === 0);

  useEffect(() => {
    void useChatStore.persist.rehydrate();
  }, []);

  useEffect(() => {
    setInitialInput(initialQuery);
  }, [initialQuery]);

  function handleNewSession() {
    reset();
    setInitialInput("");
    setMobileView("chat");
  }

  function handleSelectSession(targetSessionId: string) {
    switchSession(targetSessionId);
    setInitialInput("");
    setMobileView("chat");
  }

  function handleDeleteSession(targetSessionId: string) {
    void clearSession(targetSessionId).catch(() => undefined);
    deleteSession(targetSessionId);
    setInitialInput("");
    if (targetSessionId === sessionId) {
      setMobileView("chat");
    }
  }

  function handleSend(text: string) {
    setInitialInput("");
    setMobileView("chat");
    void sendMessage(text);
  }

  function handleQuickAdjust(instruction: string) {
    setInitialInput("");
    setMobileView("chat");
    void sendMessage(instruction);
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[#020605] text-stone-100 [background-image:radial-gradient(circle_at_18%_10%,rgba(245,158,11,0.10),transparent_28%),radial-gradient(circle_at_82%_8%,rgba(20,184,166,0.16),transparent_30%),linear-gradient(180deg,#030706_0%,#020605_48%,#010303_100%)]">
      <ChatHeader
        activeSessionId={sessionId}
        isLoading={isLoading}
        sessions={sessions}
        onDeleteSession={handleDeleteSession}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
      />
      <WorkspaceStatusBar
        error={error}
        isLoading={isLoading}
        itinerary={visibleItinerary}
        thinkingStep={thinkingStep}
      />

      <div
        className={cn(
          "hidden min-h-0 flex-1 gap-3 p-3 transition-[grid-template-columns] duration-300 lg:grid",
          isChatCollapsed
            ? "lg:grid-cols-[4.75rem_minmax(0,1fr)_minmax(360px,28%)]"
            : "lg:grid-cols-[minmax(330px,23%)_minmax(0,1fr)_minmax(320px,24%)]",
        )}
      >
        {isChatCollapsed ? (
          <section className="flex min-h-0 flex-col items-center overflow-hidden rounded-xl border border-white/10 bg-[#07100f]/95 px-2 py-3 shadow-[0_24px_70px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.06)]">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="h-11 w-11 rounded-lg border-teal-300/25 bg-teal-400/10 text-teal-100 hover:bg-teal-300/15 hover:text-teal-50"
              aria-label="展开对话面板"
              onClick={() => setChatCollapsed(false)}
            >
              <PanelLeftOpen className="h-5 w-5" aria-hidden="true" />
            </Button>
            <div className="mt-4 flex h-11 w-11 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04] text-stone-300">
              <MessageSquareText className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="mt-4 h-px w-8 bg-white/10" />
            <div className="mt-4 flex flex-col items-center gap-2 text-[10px] font-medium text-stone-500 [writing-mode:vertical-rl]">
              <span>对话已收起</span>
            </div>
            {isLoading ? (
              <span className="mt-auto h-2.5 w-2.5 rounded-full bg-amber-300 shadow-[0_0_18px_rgba(252,211,77,0.7)]" />
            ) : (
              <span className="mt-auto h-2.5 w-2.5 rounded-full bg-teal-300 shadow-[0_0_18px_rgba(45,212,191,0.55)]" />
            )}
          </section>
        ) : (
          <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-white/10 bg-[#07100f]/95 shadow-[0_24px_70px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.06)]">
            <div className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 px-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-stone-200">
                <MessageSquareText className="h-4 w-4 text-teal-300" aria-hidden="true" />
                对话
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 rounded-md text-stone-400 hover:bg-white/10 hover:text-stone-100"
                aria-label="收起对话面板"
                onClick={() => setChatCollapsed(true)}
              >
                <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            <div className="min-h-0 flex-1">
              <MessageList
                messages={messages}
                isThinking={showThinking}
                isReasoningCollapsed={isReasoningCollapsed}
                onReasoningCollapsedChange={setReasoningCollapsed}
                reasoningEvents={reasoningEvents}
                thinkingStep={thinkingStep ?? "正在组织景点、路线和天气信息..."}
              />
              {error ? (
                <div className="mx-4 mb-4 flex items-center gap-2 rounded-lg border border-red-400/25 bg-red-500/10 px-3 py-2 text-sm text-red-200 sm:mx-6">
                  <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                  {error}
                </div>
              ) : null}
            </div>
            <ChatInput
              initialValue={initialInput}
              isLoading={isLoading}
              onSend={handleSend}
            />
          </section>
        )}
        <DesktopOutputGrid
          itinerary={visibleItinerary}
        />
      </div>

      <div className="flex min-h-0 flex-1 flex-col bg-[#020605] lg:hidden">
        <div className="min-h-0 flex-1 overflow-hidden">
          {mobileView === "chat" ? (
            <div className="flex h-full flex-col">
              <div className="min-h-0 flex-1">
                <MessageList
                  messages={messages}
                  isThinking={showThinking}
                  isReasoningCollapsed={isReasoningCollapsed}
                  onReasoningCollapsedChange={setReasoningCollapsed}
                  reasoningEvents={reasoningEvents}
                  thinkingStep={thinkingStep ?? "正在组织景点、路线和天气信息..."}
                />
                {error ? (
                  <div className="mx-4 mb-4 flex items-center gap-2 rounded-lg border border-red-400/25 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                    <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                    {error}
                  </div>
                ) : null}
              </div>
              <ChatInput
                initialValue={initialInput}
                isLoading={isLoading}
                onSend={handleSend}
              />
            </div>
          ) : null}

          {mobileView === "itinerary" ? (
            <div className="h-full overflow-auto p-4">
              {visibleItinerary ? (
                <ItineraryView
                  itinerary={visibleItinerary}
                  isQuickAdjustDisabled={isLoading}
                  onQuickAdjust={handleQuickAdjust}
                  sessionId={sessionId}
                />
              ) : (
                <EmptyItineraryPanel />
              )}
              <Button
                className="fixed bottom-20 right-4 rounded-lg bg-teal-500 text-zinc-950 hover:bg-teal-400"
                onClick={() => setMobileView("chat")}
              >
                返回对话
              </Button>
            </div>
          ) : null}

          {mobileView === "map" ? (
            <div className="h-full overflow-auto p-4">
              {visibleItinerary ? (
                <MapView itinerary={visibleItinerary} />
              ) : (
                <EmptyItineraryPanel />
              )}
              <Button
                className="fixed bottom-20 right-4 rounded-lg bg-teal-500 text-zinc-950 hover:bg-teal-400"
                onClick={() => setMobileView("chat")}
              >
                返回对话
              </Button>
            </div>
          ) : null}
        </div>

        <nav className="grid h-16 shrink-0 grid-cols-3 border-t border-white/10 bg-[#07100f]/95">
          <button
            type="button"
            className={`flex flex-col items-center justify-center gap-1 text-xs ${
              mobileView === "chat" ? "text-teal-200" : "text-stone-500"
            }`}
            onClick={() => setMobileView("chat")}
          >
            <MessageSquareText className="h-5 w-5" aria-hidden="true" />
            对话
          </button>
          <button
            type="button"
            className={`flex flex-col items-center justify-center gap-1 text-xs ${
              mobileView === "itinerary" ? "text-teal-200" : "text-stone-500"
            }`}
            onClick={() => setMobileView("itinerary")}
          >
            <CalendarDays className="h-5 w-5" aria-hidden="true" />
            行程
          </button>
          <button
            type="button"
            className={`flex flex-col items-center justify-center gap-1 text-xs ${
              mobileView === "map" ? "text-teal-200" : "text-stone-500"
            }`}
            onClick={() => setMobileView("map")}
          >
            <MapPinned className="h-5 w-5" aria-hidden="true" />
            地图
          </button>
        </nav>
      </div>
    </div>
  );
}
