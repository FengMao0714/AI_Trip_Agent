"use client";

import Link from "next/link";
import { Compass, Plus, Radio } from "lucide-react";

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
    <header className="flex h-20 min-w-0 shrink-0 items-center justify-between gap-3 border-b border-white/10 bg-[#020605]/90 px-4 text-stone-100 backdrop-blur-xl sm:px-6">
      <Link
        href="/"
        className="flex min-w-0 flex-1 items-center gap-3 text-sm font-semibold text-stone-100 sm:text-base"
      >
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-amber-200/35 bg-[radial-gradient(circle_at_35%_35%,#f9e7ad,#b98331_42%,#15100b_68%)] text-zinc-950 shadow-[0_0_34px_rgba(245,158,11,0.26)]">
          <Compass className="h-5 w-5" aria-hidden="true" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-lg tracking-normal text-amber-50">
            AI 旅行规划工作台
          </span>
          <span className="hidden items-center gap-1 text-xs font-normal text-stone-400 sm:flex">
            <Radio className="h-3 w-3 text-teal-300" aria-hidden="true" />
            真实后端 · SSE 流式输出 · 高德地图联动
          </span>
        </span>
      </Link>

      <div className="hidden min-w-0 flex-1 justify-center xl:flex">
        <div className="min-w-0 text-center">
          <p className="truncate text-xl font-semibold text-amber-50">
            智能旅行 Agent 工作台
          </p>
          <p className="mt-1 text-xs text-stone-500">
            可执行行程 · 来源核验 · 地图联动 · 预算控制
          </p>
        </div>
      </div>

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
          className="rounded-lg border-teal-300/30 bg-teal-400/10 text-teal-100 hover:bg-teal-300/15 hover:text-teal-50"
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
