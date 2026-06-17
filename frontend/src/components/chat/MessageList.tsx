"use client";

import { useEffect, useRef } from "react";

import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator";
import { UserMessage } from "@/components/chat/UserMessage";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatMessage, ReasoningEvent } from "@/types/message";

interface MessageListProps {
  messages: ChatMessage[];
  isThinking?: boolean;
  isReasoningCollapsed?: boolean;
  onReasoningCollapsedChange?: (isCollapsed: boolean) => void;
  reasoningEvents?: ReasoningEvent[];
  thinkingStep?: string;
}

export function MessageList({
  messages,
  isThinking = false,
  isReasoningCollapsed = false,
  onReasoningCollapsedChange,
  reasoningEvents = [],
  thinkingStep,
}: MessageListProps) {
  const viewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) {
      return;
    }

    viewport.scrollTo({
      top: viewport.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <ScrollArea className="h-full" viewportRef={viewportRef}>
      <div className="space-y-5 p-4 sm:p-6">
        {messages.map((message) => {
          if (message.role === "user") {
            return <UserMessage key={message.id} message={message} />;
          }

          if (message.role === "assistant") {
            return <AssistantMessage key={message.id} message={message} />;
          }

          return null;
        })}
        {isThinking ? (
          <ThinkingIndicator
            events={reasoningEvents}
            isCollapsed={isReasoningCollapsed}
            isThinking={isThinking}
            onCollapsedChange={onReasoningCollapsedChange}
            step={thinkingStep}
          />
        ) : null}
      </div>
    </ScrollArea>
  );
}
