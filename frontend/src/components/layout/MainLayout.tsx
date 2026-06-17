"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  Database,
  MapPinned,
  MessageSquareText,
  Radio,
  Route,
  ShieldCheck,
} from "lucide-react";

import { ChatHeader } from "@/components/layout/ChatHeader";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";
import { ItineraryView } from "@/components/itinerary/ItineraryView";
import { useChat } from "@/hooks/useChat";
import { clearSession } from "@/lib/api";
import { useChatStore } from "@/store/chatStore";
import { Button } from "@/components/ui/button";
import { getItineraryInsights } from "@/lib/itineraryInsights";
import { cn } from "@/lib/utils";
import type { Itinerary } from "@/types/itinerary";

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
  isQuickAdjustDisabled,
  itinerary,
  onQuickAdjust,
  sessionId,
}: {
  isQuickAdjustDisabled?: boolean;
  itinerary: Itinerary | null;
  onQuickAdjust?: (instruction: string) => void;
  sessionId?: string;
}) {
  return (
    <>
      <main className="min-h-0 overflow-auto rounded-xl border border-white/10 bg-[#07100f]/95 p-3 shadow-[0_24px_70px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.06)]">
        {itinerary ? (
          <ItineraryView
            itinerary={itinerary}
            isQuickAdjustDisabled={isQuickAdjustDisabled}
            onQuickAdjust={onQuickAdjust}
            sessionId={sessionId}
          />
        ) : (
          <EmptyItineraryPanel />
        )}
      </main>
      <aside className="grid min-h-0 grid-rows-[minmax(360px,1fr)_auto] gap-3">
        {itinerary ? (
          <MapView itinerary={itinerary} />
        ) : (
          <EmptyItineraryPanel compact />
        )}
        <VerificationPanel itinerary={itinerary} />
      </aside>
    </>
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

      <div className="hidden min-h-0 flex-1 gap-3 p-3 lg:grid lg:grid-cols-[minmax(340px,25%)_minmax(0,45%)_minmax(360px,30%)]">
        <section className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-white/10 bg-[#07100f]/95 shadow-[0_24px_70px_rgba(0,0,0,0.38),inset_0_1px_0_rgba(255,255,255,0.06)]">
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
        <DesktopOutputGrid
          isQuickAdjustDisabled={isLoading}
          itinerary={visibleItinerary}
          onQuickAdjust={handleQuickAdjust}
          sessionId={generatedItinerary ? sessionId : undefined}
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
