"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  MapPinned,
  MessageSquareText,
} from "lucide-react";

import { ChatHeader } from "@/components/layout/ChatHeader";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageList } from "@/components/chat/MessageList";
import { ItineraryView } from "@/components/itinerary/ItineraryView";
import { useChat } from "@/hooks/useChat";
import { clearSession } from "@/lib/api";
import { useChatStore } from "@/store/chatStore";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Itinerary } from "@/types/itinerary";

type MobileView = "chat" | "itinerary" | "map";

interface MainLayoutProps {
  initialQuery?: string;
}

const MapView = dynamic(
  () => import("@/components/map/MapView").then((module) => module.MapView),
  {
    loading: () => (
      <div className="flex h-full min-h-[420px] items-center justify-center rounded-lg border border-zinc-200 bg-zinc-100 text-sm text-zinc-500">
        地图加载中
      </div>
    ),
    ssr: false,
  },
);

type RightPanelView = "itinerary" | "map";

function RightPanel({
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
  const [rightPanelView, setRightPanelView] =
    useState<RightPanelView>("itinerary");

  return (
    <Tabs
      value={rightPanelView}
      onValueChange={(value) => setRightPanelView(value as RightPanelView)}
      className="flex h-full flex-col"
    >
      <div className="border-b border-zinc-200 bg-white p-3">
        <TabsList className="grid w-full grid-cols-2 rounded-lg">
          <TabsTrigger value="itinerary" className="rounded-md">
            行程
          </TabsTrigger>
          <TabsTrigger value="map" className="rounded-md">
            地图
          </TabsTrigger>
        </TabsList>
      </div>
      <TabsContent value="itinerary" className="m-0 min-h-0 flex-1 overflow-auto p-4">
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
      </TabsContent>
      <TabsContent value="map" className="m-0 min-h-0 flex-1 overflow-auto p-4">
        {rightPanelView === "map" && itinerary ? (
          <MapView itinerary={itinerary} />
        ) : (
          <EmptyItineraryPanel />
        )}
      </TabsContent>
    </Tabs>
  );
}

function EmptyItineraryPanel() {
  return (
    <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-dashed border-zinc-300 bg-zinc-50 px-6 text-center">
      <div className="max-w-sm">
        <p className="text-sm font-medium text-zinc-900">还没有生成行程</p>
        <p className="mt-2 text-sm leading-6 text-zinc-500">
          发送目的地、天数、预算和偏好后，这里会展示真实生成的行程和地图标注。
        </p>
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
    <div className="flex h-screen flex-col overflow-hidden bg-zinc-50 text-zinc-950">
      <ChatHeader
        activeSessionId={sessionId}
        isLoading={isLoading}
        sessions={sessions}
        onDeleteSession={handleDeleteSession}
        onNewSession={handleNewSession}
        onSelectSession={handleSelectSession}
      />

      <div className="hidden min-h-0 flex-1 lg:grid lg:grid-cols-[minmax(380px,45%)_minmax(0,55%)]">
        <section className="flex min-h-0 flex-col border-r border-zinc-200 bg-zinc-50">
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
              <div className="mx-4 mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 sm:mx-6">
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

        <aside className="min-h-0 bg-white">
          <RightPanel
            isQuickAdjustDisabled={isLoading}
            itinerary={visibleItinerary}
            onQuickAdjust={handleQuickAdjust}
            sessionId={generatedItinerary ? sessionId : undefined}
          />
        </aside>
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:hidden">
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
                  <div className="mx-4 mb-4 flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
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
                className="fixed bottom-20 right-4 rounded-lg bg-teal-700 hover:bg-teal-800"
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
                className="fixed bottom-20 right-4 rounded-lg bg-teal-700 hover:bg-teal-800"
                onClick={() => setMobileView("chat")}
              >
                返回对话
              </Button>
            </div>
          ) : null}
        </div>

        <nav className="grid h-16 shrink-0 grid-cols-3 border-t border-zinc-200 bg-white">
          <button
            type="button"
            className={`flex flex-col items-center justify-center gap-1 text-xs ${
              mobileView === "chat" ? "text-teal-700" : "text-zinc-500"
            }`}
            onClick={() => setMobileView("chat")}
          >
            <MessageSquareText className="h-5 w-5" aria-hidden="true" />
            对话
          </button>
          <button
            type="button"
            className={`flex flex-col items-center justify-center gap-1 text-xs ${
              mobileView === "itinerary" ? "text-teal-700" : "text-zinc-500"
            }`}
            onClick={() => setMobileView("itinerary")}
          >
            <CalendarDays className="h-5 w-5" aria-hidden="true" />
            行程
          </button>
          <button
            type="button"
            className={`flex flex-col items-center justify-center gap-1 text-xs ${
              mobileView === "map" ? "text-teal-700" : "text-zinc-500"
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
