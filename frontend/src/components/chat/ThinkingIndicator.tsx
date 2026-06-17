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
  thinking: "bg-sky-50 text-sky-700 ring-sky-100",
  tool_call: "bg-amber-50 text-amber-700 ring-amber-100",
  tool_result: "bg-teal-50 text-teal-700 ring-teal-100",
  source: "bg-violet-50 text-violet-700 ring-violet-100",
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
    <div className="rounded-lg border border-teal-100 bg-white text-sm text-zinc-800 shadow-sm">
      <div className="flex items-start gap-3 px-4 py-3">
        <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700 ring-1 ring-teal-100">
          <Search className={cn("h-4 w-4", isThinking && "animate-pulse")} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-zinc-950">
              {isThinking ? "Agent 正在推理" : "Agent 推理过程"}
            </p>
            <span className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-600">
              {events.length} 步
            </span>
            {toolCallCount > 0 ? (
              <span className="rounded-md bg-amber-50 px-2 py-0.5 text-xs text-amber-700">
                {toolCallCount} 次工具调用
              </span>
            ) : null}
          </div>
          <p className="mt-1 leading-6 text-zinc-600">{currentStep}</p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-8 shrink-0 rounded-md px-2 text-zinc-500"
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
            "border-t border-zinc-100 px-4 py-3",
            isCollapsed && "bg-zinc-50/70",
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
                      <span className="text-xs font-medium text-zinc-500">
                        {formatEventMeta(event)}
                      </span>
                      {event.type === "tool_result" && toolResultCount > 0 ? (
                        <span className="text-xs text-teal-700">已观察</span>
                      ) : null}
                    </div>
                    <p className="mt-0.5 leading-6 text-zinc-800">{event.title}</p>
                    {!isCollapsed && event.detail ? (
                      <pre className="mt-2 max-h-32 overflow-auto rounded-md bg-zinc-950 px-3 py-2 text-xs leading-5 text-zinc-100">
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
        <div className="flex gap-1 border-t border-zinc-100 px-4 py-2" aria-hidden="true">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-700" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-700 delay-150" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal-700 delay-300" />
        </div>
      ) : null}
    </div>
  );
}
