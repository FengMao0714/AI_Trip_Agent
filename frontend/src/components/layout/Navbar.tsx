import Link from "next/link";
import { Compass, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";

export function Navbar() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 px-3 pt-3">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between rounded-[1.4rem] border border-white/[0.12] bg-black/[0.42] px-3 text-white shadow-[0_18px_60px_rgba(0,0,0,0.28),inset_0_1px_0_rgba(255,255,255,0.12)] backdrop-blur-2xl sm:px-4">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-3 text-base font-semibold"
          aria-label="智能 Agent 旅游助手首页"
        >
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-white/[0.14] bg-white/[0.08] text-teal-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]">
            <Compass className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="truncate">智能 Agent 旅游助手</span>
        </Link>

        <div className="hidden items-center rounded-full border border-white/10 bg-white/[0.06] px-3 py-2 text-xs text-stone-300 md:flex">
          真实后端 · SSE · 高德地图
        </div>

        <Button
          asChild
          className="h-11 rounded-full bg-white px-4 text-zinc-950 hover:bg-stone-100"
        >
          <Link href="/chat">
            <Plus className="h-4 w-4" aria-hidden="true" />
            开始规划
          </Link>
        </Button>
      </nav>
    </header>
  );
}
