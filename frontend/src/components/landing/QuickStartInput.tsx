"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, MapPin } from "lucide-react";

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
      onSubmit={handleSubmit}
      className="flex w-full max-w-2xl flex-col gap-3 rounded-lg border border-white/30 bg-white/95 p-2 shadow-xl shadow-zinc-950/15 sm:flex-row"
    >
      <label className="sr-only" htmlFor="quick-start-query">
        旅行需求
      </label>
      <div className="flex min-h-12 flex-1 items-center gap-3 px-3">
        <MapPin className="h-5 w-5 shrink-0 text-teal-700" aria-hidden="true" />
        <input
          id="quick-start-query"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="h-11 min-w-0 flex-1 bg-transparent text-base text-zinc-950 outline-none placeholder:text-zinc-500"
          placeholder="我想去北京玩3天，预算3000元，喜欢历史文化"
        />
      </div>
      <Button
        type="submit"
        className="h-12 rounded-lg bg-teal-700 px-5 text-base hover:bg-teal-800"
      >
        生成行程
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Button>
    </form>
  );
}
