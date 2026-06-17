"use client";

import ReactMarkdown from "react-markdown";
import { Bot } from "lucide-react";

import { StreamingText } from "@/components/chat/StreamingText";
import type { AssistantMessage as AssistantMessageType } from "@/types/message";

interface AssistantMessageProps {
  message: AssistantMessageType;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  return (
    <article className="flex min-w-0 items-start gap-3">
      <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal-700 text-white">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>
      <div className="min-w-0 max-w-[calc(100vw-5.25rem)] overflow-hidden break-words rounded-lg border border-zinc-200 bg-white px-4 py-3 text-sm leading-7 text-zinc-800 shadow-sm lg:max-w-[600px]">
        {message.is_streaming ? (
          <StreamingText text={message.content} isStreaming />
        ) : (
          <ReactMarkdown
            components={{
              h2: ({ children }) => (
                <h2 className="mb-2 mt-4 text-lg font-semibold text-zinc-950">
                  {children}
                </h2>
              ),
              p: ({ children }) => <p className="my-2">{children}</p>,
              ul: ({ children }) => (
                <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-zinc-950">
                  {children}
                </strong>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        )}
      </div>
    </article>
  );
}
