"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, MapPin, Mic } from "lucide-react";

import { Button } from "@/components/ui/button";

export function QuickStartInput() {
  const router = useRouter();
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const query = value.trim();
    if (!query) {
      router.push("/chat");
      return;
    }

    router.push(`/chat?q=${encodeURIComponent(query)}`);
  }

  return (
    <form
      action="/chat"
      method="get"
      onSubmit={handleSubmit}
      className="flex w-full max-w-2xl items-center gap-2 rounded-[1.65rem] border border-white/[0.16] bg-white/[0.12] p-2 shadow-[0_24px_70px_rgba(0,0,0,0.34),inset_0_1px_0_rgba(255,255,255,0.16)] backdrop-blur-2xl"
    >
      <label className="sr-only" htmlFor="quick-start-query">
        旅行需求
      </label>
      <div className="flex min-h-12 flex-1 items-center gap-3 rounded-full bg-black/[0.22] px-4">
        <MapPin className="h-5 w-5 shrink-0 text-teal-200" aria-hidden="true" />
        <input
          id="quick-start-query"
          name="q"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="h-12 min-w-0 flex-1 bg-transparent text-base text-white outline-none placeholder:text-stone-400"
          placeholder="我想去北京玩3天，预算3000元，喜欢历史文化"
        />
        <Mic className="hidden h-5 w-5 shrink-0 text-stone-500 sm:block" aria-hidden="true" />
      </div>
      <Button
        type="submit"
        aria-label="生成行程"
        className="h-12 rounded-full bg-teal-300 px-4 text-sm font-semibold text-zinc-950 shadow-[0_0_34px_rgba(45,212,191,0.24)] hover:bg-teal-200 sm:px-5"
      >
        <span className="hidden sm:inline">生成行程</span>
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </form>
  );
}
