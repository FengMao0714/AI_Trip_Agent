"use client";

import {
  Brain,
  CheckCircle2,
  ChevronDown,
  Info,
  Search,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ReasoningEvent, ReasoningEventType } from "@/types/message";

interface ThinkingIndicatorProps {
  events: ReasoningEvent[];
  isCollapsed?: boolean;
  isThinking?: boolean;
  onCollapsedChange?: (isCollapsed: boolean) => void;
  step?: string;
}

const eventIcon: Record<ReasoningEventType, typeof Brain> = {
  thinking: Brain,
  tool_call: Wrench,
  tool_result: CheckCircle2,
  source: Info,
};

const eventTone: Record<ReasoningEventType, string> = {
  thinking: "bg-sky-400/10 text-sky-200 ring-sky-300/20",
  tool_call: "bg-amber-400/10 text-amber-200 ring-amber-300/20",
  tool_result: "bg-teal-400/10 text-teal-200 ring-teal-300/20",
  source: "bg-violet-400/10 text-violet-200 ring-violet-300/20",
};

function formatEventMeta(event: ReasoningEvent) {
  if (event.type === "thinking") {
    return "思考";
  }

  if (event.type === "tool_call") {
    return event.tool ? `调用 ${event.tool}` : "调用工具";
  }

  if (event.type === "source") {
    return "生成来源";
  }

  return event.tool ? `${event.tool} 结果` : "工具结果";
}

export function ThinkingIndicator({
  events,
  isCollapsed = false,
  isThinking = false,
  onCollapsedChange,
  step = "正在分析你的旅行需求...",
}: ThinkingIndicatorProps) {
  const latestEvent = events[events.length - 1];
  const currentStep = latestEvent?.title ?? step;
  const visibleEvents = isCollapsed ? events.slice(-3) : events;
  const toolCallCount = events.filter((event) => event.type === "tool_call").length;
  const toolResultCount = events.filter(
    (event) => event.type === "tool_result",
  ).length;

  return (
    <div className="overflow-hidden rounded-lg border border-teal-300/20 bg-[#0b1313] text-sm text-stone-200 shadow-[0_18px_50px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.05)]">
      <div className="border-b border-white/10 bg-[linear-gradient(90deg,rgba(20,184,166,0.16),rgba(255,255,255,0.035),rgba(14,165,233,0.10))] px-4 py-2">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-teal-100">
            Agent Runtime
          </span>
          <span className="text-xs text-stone-500">SSE 实时流</span>
        </div>
      </div>
      <div className="flex items-start gap-3 px-4 py-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-teal-400/10 text-teal-200 ring-1 ring-teal-300/20">
          <Search className={cn("h-4 w-4", isThinking && "animate-pulse")} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-stone-50">
              {isThinking ? "Agent 正在推理" : "Agent 推理过程"}
            </p>
            <span className="rounded-md bg-white/[0.06] px-2 py-0.5 text-xs text-stone-400">
              {events.length} 步
            </span>
            {toolCallCount > 0 ? (
              <span className="rounded-md bg-amber-400/10 px-2 py-0.5 text-xs text-amber-200">
                {toolCallCount} 次工具调用
              </span>
            ) : null}
            <span className="rounded-md bg-sky-400/10 px-2 py-0.5 text-xs text-sky-200">
              实时工具链
            </span>
          </div>
          <p className="mt-1 leading-6 text-stone-300">{currentStep}</p>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <div className="rounded-md bg-white/[0.045] px-2 py-1.5 text-stone-400">
              思考 {events.filter((event) => event.type === "thinking").length}
            </div>
            <div className="rounded-md bg-amber-400/10 px-2 py-1.5 text-amber-200">
              调用 {toolCallCount}
            </div>
            <div className="rounded-md bg-teal-400/10 px-2 py-1.5 text-teal-200">
              观察 {toolResultCount}
            </div>
          </div>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-8 shrink-0 rounded-md px-2 text-stone-500 hover:bg-white/10 hover:text-stone-200"
          onClick={() => onCollapsedChange?.(!isCollapsed)}
        >
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform",
              !isCollapsed && "rotate-180",
            )}
            aria-hidden="true"
          />
          <span className="sr-only">{isCollapsed ? "展开推理过程" : "收起推理过程"}</span>
        </Button>
      </div>

      {visibleEvents.length > 0 ? (
        <div
          className={cn(
            "border-t border-white/10 px-4 py-3",
            isCollapsed && "bg-white/[0.03]",
          )}
        >
          <div
            className={cn(
              "space-y-3",
              !isCollapsed && "max-h-80 overflow-y-auto pr-1",
            )}
          >
            {visibleEvents.map((event) => {
              const Icon = eventIcon[event.type];

              return (
                <div key={event.id} className="flex gap-3">
                  <span
                    className={cn(
                      "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ring-1",
                      eventTone[event.type],
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-medium text-stone-500">
                        {formatEventMeta(event)}
                      </span>
                      {event.type === "tool_result" && toolResultCount > 0 ? (
                        <span className="text-xs text-teal-200">已观察</span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 leading-6 text-stone-200">{event.title}</p>
                    {!isCollapsed && event.detail ? (
                      <pre className="mt-2 max-h-32 overflow-auto rounded-md border border-white/10 bg-black/60 px-3 py-2 text-xs leading-5 text-stone-200">
                        {event.detail}
                      </pre>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : null}

      {isThinking ? (
        <div className="flex gap-1 border-t border-white/10 px-4 py-2" aria-hidden="true">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-300" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-300 delay-150" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-300 delay-300" />
        </div>
      ) : null}
    </div>
  );
}
