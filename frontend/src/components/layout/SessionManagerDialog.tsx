"use client";

import { useState } from "react";
import {
  Check,
  Clock3,
  History,
  MessageSquareText,
  Plus,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatSessionSnapshot } from "@/store/chatStore";

interface SessionManagerDialogProps {
  activeSessionId: string;
  isLoading?: boolean;
  sessions: ChatSessionSnapshot[];
  onDeleteSession: (sessionId: string) => void;
  onNewSession: () => void;
  onSelectSession: (sessionId: string) => void;
}

function formatSessionTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "刚刚";
  }

  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatMessageCount(count: number) {
  if (count <= 0) {
    return "未开始";
  }

  return `${count} 轮对话`;
}

export function SessionManagerDialog({
  activeSessionId,
  isLoading = false,
  sessions,
  onDeleteSession,
  onNewSession,
  onSelectSession,
}: SessionManagerDialogProps) {
  const [open, setOpen] = useState(false);

  function handleNewSession() {
    onNewSession();
    setOpen(false);
  }

  function handleSelectSession(sessionId: string) {
    onSelectSession(sessionId);
    setOpen(false);
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="rounded-lg"
          aria-label="历史会话"
        >
          <History className="h-4 w-4" aria-hidden="true" />
          <span className="hidden sm:inline">历史</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-xl gap-5 rounded-lg p-0">
        <DialogHeader className="border-b border-zinc-200 px-5 py-4">
          <DialogTitle className="text-base">最近会话</DialogTitle>
          <DialogDescription>
            保存在当前浏览器中的旅行规划对话。
          </DialogDescription>
        </DialogHeader>

        <div className="px-5">
          <Button
            type="button"
            variant="outline"
            className="h-10 w-full rounded-lg justify-start"
            disabled={isLoading}
            onClick={handleNewSession}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            新建会话
          </Button>
        </div>

        <ScrollArea className="max-h-[420px] px-5 pb-5">
          {sessions.length > 0 ? (
            <div className="space-y-2">
              {sessions.map((session) => {
                const isActive = session.id === activeSessionId;

                return (
                  <div
                    key={session.id}
                    className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-white p-2"
                  >
                    <button
                      type="button"
                      className="flex min-w-0 flex-1 items-start gap-3 rounded-md px-2 py-2 text-left hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={isLoading}
                      onClick={() => handleSelectSession(session.id)}
                    >
                      <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-teal-700">
                        {isActive ? (
                          <Check className="h-4 w-4" aria-hidden="true" />
                        ) : (
                          <MessageSquareText
                            className="h-4 w-4"
                            aria-hidden="true"
                          />
                        )}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-zinc-950">
                          {session.title}
                        </span>
                        <span className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500">
                          <span>{formatMessageCount(session.messageCount)}</span>
                          <span className="inline-flex items-center gap-1">
                            <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                            {formatSessionTime(session.updatedAt)}
                          </span>
                        </span>
                      </span>
                    </button>

                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 rounded-lg text-zinc-500 hover:text-red-600"
                      aria-label={`删除 ${session.title}`}
                      disabled={isLoading}
                      onClick={() => onDeleteSession(session.id)}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex min-h-[180px] flex-col items-center justify-center rounded-lg border border-dashed border-zinc-300 bg-zinc-50 px-6 text-center">
              <MessageSquareText className="h-8 w-8 text-zinc-400" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium text-zinc-900">
                暂无历史会话
              </p>
            </div>
          )}
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
