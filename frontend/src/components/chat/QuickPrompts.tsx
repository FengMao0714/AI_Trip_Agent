"use client";

import { Building2, HeartHandshake, Landmark } from "lucide-react";

import { Button } from "@/components/ui/button";

const prompts = [
  {
    label: "北京3天历史文化路线",
    meta: "中轴线 · 博物馆 · 预算内",
    icon: Landmark,
  },
  {
    label: "成都4天老人友好行程",
    meta: "少走路 · 餐饮稳妥",
    icon: HeartHandshake,
  },
  {
    label: "上海2天亲子轻松游",
    meta: "亲子 · 城市交通",
    icon: Building2,
  },
];

interface QuickPromptsProps {
  onPick: (prompt: string) => void;
}

export function QuickPrompts({ onPick }: QuickPromptsProps) {
  return (
    <div className="flex min-w-0 max-w-full flex-wrap gap-2 pb-1">
      {prompts.map((prompt) => {
        const Icon = prompt.icon;
        return (
          <Button
            key={prompt.label}
            type="button"
            variant="outline"
            size="sm"
            className="h-auto min-w-[9.25rem] flex-1 justify-start rounded-lg border-white/10 bg-white/[0.045] px-3 py-2 text-left text-stone-200 hover:border-teal-300/35 hover:bg-teal-400/10 hover:text-teal-50"
            onClick={() => onPick(prompt.label)}
          >
            <Icon className="h-4 w-4 text-teal-300" aria-hidden="true" />
            <span className="flex flex-col leading-tight">
              <span>{prompt.label}</span>
              <span className="mt-0.5 text-[11px] font-normal text-stone-500">
                {prompt.meta}
              </span>
            </span>
          </Button>
        );
      })}
    </div>
  );
}
