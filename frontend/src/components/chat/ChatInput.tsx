"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { SendHorizontal } from "lucide-react";

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
      className="min-w-0 border-t border-zinc-200 bg-white p-3 sm:p-4"
    >
      <QuickPrompts
        onPick={(prompt) => {
          setValue(prompt);
          textareaRef.current?.focus();
        }}
      />
      <div className="mt-3 flex min-w-0 items-end gap-2">
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
          placeholder="告诉我你想去哪、玩几天、预算和偏好"
          className="max-h-36 min-h-12 min-w-0 flex-1 resize-none rounded-lg bg-zinc-50 text-sm leading-6"
        />
        <Button
          type="submit"
          size="icon"
          className="h-12 w-12 shrink-0 rounded-lg bg-teal-700 hover:bg-teal-800"
          disabled={isLoading || !value.trim()}
          aria-label="发送消息"
        >
          <SendHorizontal className="h-5 w-5" aria-hidden="true" />
        </Button>
      </div>
    </form>
  );
}
