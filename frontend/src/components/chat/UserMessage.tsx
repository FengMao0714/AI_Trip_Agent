"use client";

import type { UserMessage as UserMessageType } from "@/types/message";

interface UserMessageProps {
  message: UserMessageType;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <article className="flex min-w-0 justify-end">
      <div className="min-w-0 max-w-[calc(100vw-2rem)] overflow-hidden break-words rounded-lg bg-zinc-950 px-4 py-3 text-sm leading-7 text-white shadow-sm sm:max-w-[85vw] lg:max-w-[600px]">
        {message.content}
      </div>
    </article>
  );
}
