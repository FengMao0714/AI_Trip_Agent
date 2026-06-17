"use client";

import { Button } from "@/components/ui/button";

const prompts = [
  "北京3天历史文化路线",
  "成都4天老人友好行程",
  "上海2天亲子轻松游",
];

interface QuickPromptsProps {
  onPick: (prompt: string) => void;
}

export function QuickPrompts({ onPick }: QuickPromptsProps) {
  return (
    <div className="flex min-w-0 max-w-full flex-wrap gap-2 overflow-hidden pb-1 sm:flex-nowrap sm:overflow-x-auto">
      {prompts.map((prompt) => (
        <Button
          key={prompt}
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0 rounded-lg bg-white"
          onClick={() => onPick(prompt)}
        >
          {prompt}
        </Button>
      ))}
    </div>
  );
}
