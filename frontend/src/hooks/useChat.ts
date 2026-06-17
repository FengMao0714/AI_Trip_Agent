"use client";

import { useCallback } from "react";

import { fetchChat } from "@/lib/api";
import { inferTripStartDateFromText } from "@/lib/dateDisplay";
import { parseItinerary } from "@/lib/parseItinerary";
import { streamSSE } from "@/lib/sse";
import { useChatStore } from "@/store/chatStore";
import type { ChatMessage, ReasoningEventType } from "@/types/message";

function createMessageId(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function getRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function getErrorMessage(error: unknown) {
  return error instanceof Error ? error.message : "生成行程时出现未知错误。";
}

function stringifyBrief(value: unknown, fallback = "暂无详情") {
  if (value === undefined || value === null) {
    return fallback;
  }

  if (typeof value === "string") {
    return value.length > 160 ? `${value.slice(0, 160)}...` : value;
  }

  try {
    const json = JSON.stringify(value, null, 2);
    return json.length > 220 ? `${json.slice(0, 220)}...` : json;
  } catch {
    return fallback;
  }
}

function createReasoningEvent(
  type: ReasoningEventType,
  title: string,
  detail?: string,
  tool?: string,
) {
  return {
    id: createMessageId(type),
    type,
    title,
    detail,
    tool,
    created_at: new Date().toISOString(),
  };
}

export function useChat() {
  const messages = useChatStore((state) => state.messages);
  const itinerary = useChatStore((state) => state.itinerary);
  const isLoading = useChatStore((state) => state.isLoading);
  const error = useChatStore((state) => state.error);
  const sessionId = useChatStore((state) => state.sessionId);
  const sessions = useChatStore((state) => state.sessions);
  const thinkingStep = useChatStore((state) => state.thinkingStep);
  const reasoningEvents = useChatStore((state) => state.reasoningEvents);
  const isReasoningCollapsed = useChatStore(
    (state) => state.isReasoningCollapsed,
  );
  const addMessage = useChatStore((state) => state.addMessage);
  const startAssistantMessage = useChatStore(
    (state) => state.startAssistantMessage,
  );
  const appendAssistantContent = useChatStore(
    (state) => state.appendAssistantContent,
  );
  const setAssistantStreaming = useChatStore(
    (state) => state.setAssistantStreaming,
  );
  const addReasoningEvent = useChatStore((state) => state.addReasoningEvent);
  const clearReasoningEvents = useChatStore(
    (state) => state.clearReasoningEvents,
  );
  const setReasoningCollapsed = useChatStore(
    (state) => state.setReasoningCollapsed,
  );
  const setItinerary = useChatStore((state) => state.setItinerary);
  const setLoading = useChatStore((state) => state.setLoading);
  const setError = useChatStore((state) => state.setError);
  const setThinkingStep = useChatStore((state) => state.setThinkingStep);
  const reset = useChatStore((state) => state.reset);
  const switchSession = useChatStore((state) => state.switchSession);
  const deleteSession = useChatStore((state) => state.deleteSession);

  const sendMessage = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || isLoading) {
        return;
      }

      const userMessage: ChatMessage = {
        id: createMessageId("user"),
        role: "user",
        content: message,
        created_at: new Date().toISOString(),
      };
      const assistantId = createMessageId("assistant");
      let assistantStarted = false;

      addMessage(userMessage);
      setLoading(true);
      setError(null);
      clearReasoningEvents();
      setReasoningCollapsed(true);
      setThinkingStep("正在分析你的旅行需求...");

      try {
        const response = await fetchChat({
          currentItinerary: itinerary,
          message,
          sessionId,
        });

        for await (const sseEvent of streamSSE(response)) {
          const data = getRecord(sseEvent.data);

          switch (sseEvent.event) {
            case "thinking":
              {
                const step =
                  typeof data?.step === "string"
                    ? data.step
                    : "正在分析你的旅行需求...";
                setThinkingStep(step);
                addReasoningEvent(createReasoningEvent("thinking", step));
              }
              break;

            case "tool_call": {
              const tool =
                typeof data?.tool === "string" ? data.tool : "unknown_tool";
              const step = `正在调用 ${tool}...`;
              setThinkingStep(step);
              addReasoningEvent(
                createReasoningEvent(
                  "tool_call",
                  step,
                  stringifyBrief(data?.args, "无参数"),
                  tool,
                ),
              );
              break;
            }

            case "tool_result": {
              const tool =
                typeof data?.tool === "string" ? data.tool : "工具";
              const step = `${tool} 已返回结果，正在整理行程...`;
              setThinkingStep(step);
              addReasoningEvent(
                createReasoningEvent(
                  "tool_result",
                  step,
                  stringifyBrief(data?.result, "工具已返回结果"),
                  tool,
                ),
              );
              break;
            }

            case "source": {
              const label =
                typeof data?.label === "string" ? data.label : "生成来源";
              const detail =
                typeof data?.detail === "string" ? data.detail : undefined;
              const tools = Array.isArray(data?.tools)
                ? data.tools.filter((tool): tool is string => typeof tool === "string")
                : [];
              const fallbackText =
                data?.is_fallback === true ? "兜底路径" : "实时路径";
              const step = `生成来源：${label}`;
              setThinkingStep(step);
              addReasoningEvent(
                createReasoningEvent(
                  "source",
                  step,
                  [
                    detail,
                    tools.length > 0 ? `工具/依据：${tools.join("、")}` : "",
                    fallbackText,
                  ]
                    .filter(Boolean)
                    .join("\n"),
                ),
              );
              break;
            }

            case "content": {
              const content = typeof data?.text === "string" ? data.text : "";
              if (!content) {
                break;
              }

              if (!assistantStarted) {
                startAssistantMessage(assistantId);
                assistantStarted = true;
                setReasoningCollapsed(true);
              }

              appendAssistantContent(assistantId, content);
              break;
            }

            case "itinerary": {
              const parsed = parseItinerary(data?.itinerary ?? sseEvent.data);

              if (!parsed) {
                throw new Error("行程 JSON 格式不符合前端类型定义。");
              }

              setItinerary(
                parsed.start_date
                  ? parsed
                  : {
                      ...parsed,
                      start_date:
                        inferTripStartDateFromText(message) ?? undefined,
                    },
              );
              break;
            }

            case "error":
              throw new Error(
                typeof data?.message === "string"
                  ? data.message
                  : "生成行程时出现错误。",
              );

            case "done":
              return;
          }
        }
      } catch (error) {
        setError(getErrorMessage(error));
      } finally {
        if (assistantStarted) {
          setAssistantStreaming(assistantId, false);
        }

        setLoading(false);
        setThinkingStep(null);
        setReasoningCollapsed(true);
        clearReasoningEvents();
      }
    },
    [
      addMessage,
      addReasoningEvent,
      appendAssistantContent,
      clearReasoningEvents,
      isLoading,
      itinerary,
      sessionId,
      setAssistantStreaming,
      setError,
      setItinerary,
      setLoading,
      setReasoningCollapsed,
      setThinkingStep,
      startAssistantMessage,
    ],
  );

  return {
    messages,
    itinerary,
    isLoading,
    error,
    sessionId,
    sessions,
    thinkingStep,
    reasoningEvents,
    isReasoningCollapsed,
    sendMessage,
    setReasoningCollapsed,
    reset,
    switchSession,
    deleteSession,
  };
}
