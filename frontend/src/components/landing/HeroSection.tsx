import Link from "next/link";
import {
  ArrowRight,
  CheckCircle2,
  CloudSun,
  Map,
  MessageSquareText,
  Route,
  ShieldCheck,
  Sparkles,
  WalletCards,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { QuickStartInput } from "@/components/landing/QuickStartInput";

const previewDays = [
  { day: "Day 1", title: "古都初探", detail: "城墙 · 博物馆 · 回民街" },
  { day: "Day 2", title: "兵马俑与汉文化", detail: "低步行强度 · 路线已核验" },
  { day: "Day 3", title: "城市慢游", detail: "咖啡 · 书店 · 夜景" },
];

const systemStats = [
  { label: "可执行分", value: "48", suffix: "/100", icon: ShieldCheck },
  { label: "预算使用", value: "98", suffix: "%", icon: WalletCards },
  { label: "地图核验", value: "20", suffix: "/20", icon: Map },
];

function IphonePreview() {
  return (
    <div className="relative mx-auto w-full max-w-[23rem] lg:mr-0">
      <div className="absolute -left-6 top-16 hidden h-16 w-16 rounded-full border border-amber-200/20 bg-amber-300/20 blur-2xl sm:block" />
      <div className="absolute -right-8 bottom-24 hidden h-20 w-20 rounded-full border border-cyan-200/20 bg-cyan-300/20 blur-2xl sm:block" />

      <div className="relative rounded-[2.35rem] border border-white/[0.18] bg-black/[0.72] p-2 shadow-[0_34px_90px_rgba(0,0,0,0.55),inset_0_1px_0_rgba(255,255,255,0.18)] backdrop-blur-2xl">
        <div className="relative overflow-hidden rounded-[1.9rem] border border-white/10 bg-[#070b0f]">
          <div className="absolute left-1/2 top-3 z-20 h-7 w-28 -translate-x-1/2 rounded-full bg-black shadow-[inset_0_-1px_0_rgba(255,255,255,0.16)]" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,rgba(45,212,191,0.22),transparent_34%),radial-gradient(circle_at_86%_12%,rgba(251,191,36,0.15),transparent_28%)]" />

          <div className="relative min-h-[610px] px-5 pb-5 pt-14 text-stone-100">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-teal-200/80">
                  AI Trip Agent
                </p>
                <h2 className="mt-1 text-2xl font-semibold tracking-normal text-white">
                  西安 5 天
                </h2>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-teal-200/20 bg-teal-300/15 text-teal-100">
                <Sparkles className="h-5 w-5" aria-hidden="true" />
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.06] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]">
              <div className="mb-3 flex items-center justify-between text-xs text-stone-400">
                <span>实时规划中</span>
                <span className="rounded-full bg-emerald-400/15 px-2 py-1 text-emerald-200">
                  SSE 已连接
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {systemStats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-xl border border-white/[0.08] bg-black/[0.28] px-2.5 py-3"
                  >
                    <stat.icon className="mb-2 h-4 w-4 text-teal-200" aria-hidden="true" />
                    <p className="text-[11px] text-stone-500">{stat.label}</p>
                    <p className="mt-1 text-lg font-semibold text-white">
                      {stat.value}
                      <span className="text-xs text-stone-500">{stat.suffix}</span>
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.055] p-3">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-semibold text-white">今日路线</p>
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-300/15 px-2 py-1 text-xs text-amber-100">
                  <CloudSun className="h-3.5 w-3.5" aria-hidden="true" />
                  多云 20-26°C
                </span>
              </div>
              <div className="space-y-2">
                {previewDays.map((item, index) => (
                  <div
                    key={item.day}
                    className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-black/[0.22] p-3"
                  >
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-teal-200/20 bg-teal-300/15 text-sm font-semibold text-teal-100">
                      {index + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold text-stone-100">
                        {item.day} · {item.title}
                      </p>
                      <p className="mt-0.5 truncate text-xs text-stone-500">
                        {item.detail}
                      </p>
                    </div>
                    <CheckCircle2 className="h-4 w-4 text-emerald-300" aria-hidden="true" />
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 rounded-2xl border border-teal-200/[0.16] bg-teal-300/10 p-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-200/15 text-teal-100">
                  <Route className="h-5 w-5" aria-hidden="true" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">地图联动已准备</p>
                  <p className="mt-1 text-xs text-teal-100/70">
                    生成后同步展示 POI、路线和天气风险。
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function HeroSection() {
  return (
    <section
      className="relative isolate overflow-hidden bg-[#030706] text-white"
      style={{
        backgroundImage:
          'linear-gradient(90deg, rgba(3,7,6,0.92), rgba(3,7,6,0.76) 44%, rgba(3,7,6,0.5)), url("/hero-beijing.png")',
        backgroundPosition: "center",
        backgroundSize: "cover",
      }}
    >
      <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-black/75 to-transparent" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[#030706] to-transparent" />
      <div className="absolute left-0 top-28 h-px w-full bg-gradient-to-r from-transparent via-white/20 to-transparent" />

      <div className="relative mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-4 pb-14 pt-28 sm:px-6 lg:grid-cols-[minmax(0,1fr)_25rem] lg:px-8">
        <div className="max-w-3xl">
          <p className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-white/[0.14] bg-white/[0.08] px-3 py-2 text-sm text-stone-200 shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] backdrop-blur-xl">
            <MessageSquareText className="h-4 w-4 text-teal-200" aria-hidden="true" />
            ReAct Agent · 真实 POI · 路线与天气
          </p>

          <h1 className="max-w-3xl text-5xl font-semibold leading-tight tracking-normal text-white sm:text-6xl lg:text-7xl">
            智能 Agent 旅游助手
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-stone-200 sm:text-xl">
            像在 iPhone 上发一条消息一样描述目的地、天数、预算和偏好，Agent 会生成可执行的行程，并同步地图、预算、天气和来源验证。
          </p>

          <div className="mt-8">
            <QuickStartInput />
          </div>

          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Button
              asChild
              size="lg"
              className="h-12 rounded-full bg-white px-6 text-zinc-950 shadow-[0_16px_40px_rgba(255,255,255,0.18)] hover:bg-stone-100"
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
              className="h-12 rounded-full border-white/[0.18] bg-white/[0.08] px-6 text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.1)] backdrop-blur-xl hover:bg-white/[0.14] hover:text-white"
            >
              <Link href="/chat?q=%E6%88%91%E6%83%B3%E5%8E%BB%E5%8C%97%E4%BA%AC%E7%8E%A93%E5%A4%A9%EF%BC%8C%E9%A2%84%E7%AE%973000%E5%85%83%EF%BC%8C%E5%96%9C%E6%AC%A2%E5%8E%86%E5%8F%B2%E6%96%87%E5%8C%96">
                查看示例
              </Link>
            </Button>
          </div>

          <div className="mt-8 grid max-w-2xl grid-cols-3 gap-3 text-xs text-stone-400 sm:text-sm">
            {["SSE 流式输出", "高德地图点位", "天气风险提示"].map((item) => (
              <div
                key={item}
                className="rounded-lg border border-white/10 bg-white/[0.055] px-3 py-2 backdrop-blur"
              >
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="pb-8 lg:pb-0">
          <IphonePreview />
        </div>
      </div>
    </section>
  );
}
