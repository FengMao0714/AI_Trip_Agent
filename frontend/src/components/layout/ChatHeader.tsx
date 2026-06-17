"use client";

import Link from "next/link";
import { Compass, Plus } from "lucide-react";

import { SessionManagerDialog } from "@/components/layout/SessionManagerDialog";
import { Button } from "@/components/ui/button";
import type { ChatSessionSnapshot } from "@/store/chatStore";

interface ChatHeaderProps {
  activeSessionId: string;
  isLoading?: boolean;
  sessions: ChatSessionSnapshot[];
  onDeleteSession: (sessionId: string) => void;
  onNewSession: () => void;
  onSelectSession: (sessionId: string) => void;
}

export function ChatHeader({
  activeSessionId,
  isLoading = false,
  sessions,
  onDeleteSession,
  onNewSession,
  onSelectSession,
}: ChatHeaderProps) {
  return (
    <header className="flex h-16 min-w-0 shrink-0 items-center justify-between gap-3 border-b border-zinc-200 bg-white px-4 sm:px-6">
      <Link
        href="/"
        className="flex min-w-0 flex-1 items-center gap-2 text-sm font-semibold text-zinc-950 sm:text-base"
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-950 text-white">
          <Compass className="h-5 w-5" aria-hidden="true" />
        </span>
        <span className="truncate">智能 Agent 旅游助手</span>
      </Link>

      <div className="flex shrink-0 items-center gap-2">
        <SessionManagerDialog
          activeSessionId={activeSessionId}
          isLoading={isLoading}
          sessions={sessions}
          onDeleteSession={onDeleteSession}
          onNewSession={onNewSession}
          onSelectSession={onSelectSession}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="rounded-lg"
          disabled={isLoading}
          aria-label="新建会话"
          onClick={onNewSession}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">新建会话</span>
        </Button>
      </div>
    </header>
  );
}
