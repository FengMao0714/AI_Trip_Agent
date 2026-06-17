import Link from "next/link";
import {
  ArrowRight,
  Map,
  MessageSquareText,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { QuickStartInput } from "@/components/landing/QuickStartInput";

export function HeroSection() {
  return (
    <section
      className="relative isolate min-h-[760px] overflow-hidden bg-zinc-950 pt-24 text-white"
      style={{
        backgroundImage:
          'linear-gradient(90deg, rgba(9, 9, 11, 0.88), rgba(9, 9, 11, 0.68) 42%, rgba(9, 9, 11, 0.24)), url("/hero-beijing.png")',
        backgroundPosition: "center",
        backgroundSize: "cover",
      }}
    >
      <div className="mx-auto grid max-w-7xl gap-10 px-4 pb-16 pt-12 sm:px-6 lg:grid-cols-[minmax(0,1fr)_460px] lg:px-8 lg:pb-24 lg:pt-20">
        <div className="flex max-w-3xl flex-col justify-center">
          <p className="mb-5 inline-flex w-fit items-center gap-2 rounded-lg border border-white/25 bg-white/10 px-3 py-2 text-sm text-zinc-100 backdrop-blur">
            <MessageSquareText className="h-4 w-4" aria-hidden="true" />
            ReAct Agent · 真实 POI · 路线与天气
          </p>
          <h1 className="max-w-3xl text-5xl font-semibold leading-tight text-white sm:text-6xl lg:text-7xl">
            智能 Agent 旅游助手
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-100 sm:text-xl">
            用一句话描述目的地、天数、预算和偏好，自动生成包含景点、餐饮、住宿、路线和天气的可执行行程。
          </p>

          <div className="mt-9">
            <QuickStartInput />
          </div>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Button
              asChild
              size="lg"
              className="rounded-lg bg-white text-zinc-950 hover:bg-zinc-100"
            >
              <Link href="/chat">
                开始规划
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </Button>
            <Button
              asChild
              size="lg"
              variant="outline"
              className="rounded-lg border-white/40 bg-white/10 text-white hover:bg-white hover:text-zinc-950"
            >
              <Link href="/chat?q=%E6%88%91%E6%83%B3%E5%8E%BB%E5%8C%97%E4%BA%AC%E7%8E%A93%E5%A4%A9%EF%BC%8C%E9%A2%84%E7%AE%973000%E5%85%83%EF%BC%8C%E5%96%9C%E6%AC%A2%E5%8E%86%E5%8F%B2%E6%96%87%E5%8C%96">
                查看示例
              </Link>
            </Button>
          </div>
        </div>

        <div className="self-end lg:pt-16">
          <div className="rounded-lg border border-white/25 bg-white/95 p-4 text-zinc-950 shadow-2xl shadow-zinc-950/30 backdrop-blur">
            <div className="flex items-center justify-between border-b border-zinc-200 pb-4">
              <div>
                <p className="text-sm text-zinc-500">实时规划工作台</p>
                <h2 className="text-xl font-semibold">等待你的旅行需求</h2>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-700 text-white">
                <Map className="h-5 w-5" aria-hidden="true" />
              </div>
            </div>

            <div className="grid gap-3 py-4 sm:grid-cols-3 lg:grid-cols-1">
              {["目的地与天数", "预算与偏好", "景点路线天气"].map((item) => (
                <div key={item} className="rounded-lg bg-zinc-100 p-3">
                  <div className="mb-2 flex items-center gap-2 text-sm font-medium text-zinc-700">
                    <Sparkles className="h-4 w-4 text-teal-700" />
                    {item}
                  </div>
                  <p className="text-sm leading-6 text-zinc-500">
                    提交需求后由 Agent 调用真实工具补全。
                  </p>
                </div>
              ))}
            </div>

            <div className="rounded-lg border border-dashed border-zinc-300 p-4 text-sm leading-6 text-zinc-500">
              这里不会预加载示例行程。生成完成后，行程卡片、预算汇总和地图标注会同步出现。
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
