"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  CalendarDays,
  Loader2,
  MapPin,
  SendHorizontal,
  SlidersHorizontal,
  WalletCards,
} from "lucide-react";

import { QuickPrompts } from "@/components/chat/QuickPrompts";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface ChatInputProps {
  initialValue?: string;
  isLoading?: boolean;
  onSend: (text: string) => void;
}

export function ChatInput({
  initialValue = "",
  isLoading = false,
  onSend,
}: ChatInputProps) {
  const [value, setValue] = useState(initialValue);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setValue(initialValue);
  }, [initialValue]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const text = value.trim();
    if (!text || isLoading) {
      return;
    }

    onSend(text);
    setValue("");
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="min-w-0 border-t border-white/10 bg-[#07100f]/95 p-3 shadow-[0_-18px_50px_rgba(0,0,0,0.32)] sm:p-4"
    >
      <div className="mb-3 flex flex-col gap-3 rounded-lg border border-white/10 bg-white/[0.045] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)] sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-amber-50">规划控制台</p>
          <p className="mt-1 text-xs leading-5 text-stone-400">
            一句话写清目的地、天数、预算、同行人和偏好，Agent 会保留上下文做局部微调。
          </p>
        </div>
        <div className="grid grid-cols-4 gap-1.5 text-xs text-stone-400 sm:flex">
          {[
            { label: "目的地", icon: MapPin },
            { label: "天数", icon: CalendarDays },
            { label: "预算", icon: WalletCards },
            { label: "偏好", icon: SlidersHorizontal },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <span
                key={item.label}
                className="inline-flex h-7 items-center justify-center gap-1 rounded-md border border-white/10 bg-white/[0.04] px-2"
              >
                <Icon className="h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
                {item.label}
              </span>
            );
          })}
        </div>
      </div>
      <QuickPrompts
        onPick={(prompt) => {
          setValue(prompt);
          textareaRef.current?.focus();
        }}
      />
      <div className="mt-3 flex min-w-0 items-end gap-2">
        <div className="min-w-0 flex-1 rounded-lg border border-white/10 bg-[#0b1313] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] focus-within:border-teal-300/45 focus-within:ring-2 focus-within:ring-teal-300/10">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="例如：我想去北京玩3天，预算3000元，喜欢历史文化，不吃辣，希望少走路"
            className="max-h-36 min-h-14 min-w-0 resize-none border-0 bg-transparent text-sm leading-6 text-stone-100 shadow-none placeholder:text-stone-500 focus-visible:ring-0"
          />
          <div className="flex items-center justify-between border-t border-white/10 px-3 py-2 text-xs text-stone-500">
            <span>Enter 发送，Shift + Enter 换行</span>
            <span>{value.trim().length} 字</span>
          </div>
        </div>
        <Button
          type="submit"
          size="icon"
          className="h-14 w-14 shrink-0 rounded-full bg-teal-400 text-zinc-950 shadow-[0_0_34px_rgba(45,212,191,0.25)] hover:bg-teal-300"
          disabled={isLoading || !value.trim()}
          aria-label="发送消息"
        >
          {isLoading ? (
            <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
          ) : (
            <SendHorizontal className="h-5 w-5" aria-hidden="true" />
          )}
        </Button>
      </div>
    </form>
  );
}
