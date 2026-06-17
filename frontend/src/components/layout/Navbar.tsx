import Link from "next/link";
import { Compass } from "lucide-react";

import { Button } from "@/components/ui/button";

export function Navbar() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/20 bg-white/85 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link
          href="/"
          className="flex items-center gap-2 text-base font-semibold text-zinc-950"
          aria-label="智能 Agent 旅游助手首页"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-zinc-950 text-white">
            <Compass className="h-5 w-5" aria-hidden="true" />
          </span>
          <span>智能 Agent 旅游助手</span>
        </Link>

        <Button asChild className="rounded-lg bg-zinc-950 hover:bg-zinc-800">
          <Link href="/chat">开始规划</Link>
        </Button>
      </nav>
    </header>
  );
}
