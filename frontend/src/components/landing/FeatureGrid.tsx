import { Bot, CloudSun, MapPinned, ShieldCheck, WalletCards } from "lucide-react";

import { FeatureCard } from "@/components/landing/FeatureCard";

const features = [
  {
    icon: Bot,
    title: "对话式规划",
    metric: "1 句话",
    description:
      "从自然语言里提取目的地、天数、预算和偏好，必要时继续追问补齐信息。",
    tone: "teal" as const,
  },
  {
    icon: MapPinned,
    title: "真实地点与路线",
    metric: "POI 核验",
    description:
      "围绕景点、餐饮、住宿和交通耗时组织行程，减少只好看但难执行的安排。",
    tone: "sky" as const,
  },
  {
    icon: CloudSun,
    title: "天气感知",
    metric: "风险提示",
    description:
      "结合天气结果调整室外、室内和休息节点，让每天的节奏更稳。",
    tone: "amber" as const,
  },
  {
    icon: WalletCards,
    title: "预算约束",
    metric: "费用汇总",
    description:
      "把门票、餐饮、住宿和市内交通放进同一张账单，保留机动空间。",
    tone: "rose" as const,
  },
];

export function FeatureGrid() {
  return (
    <section className="bg-[#030706] py-14 text-stone-100 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-8 lg:grid-cols-[0.9fr_1.4fr] lg:items-end">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-200/80">
              Agent Workflow
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal text-white sm:text-4xl">
              从想法到行程，一屏完成
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-stone-400">
              首页只负责让用户快速进入真实工作台；生成完成后，行程卡片、预算汇总、天气风险和地图标注会同步出现。
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            {[
              { label: "真实后端", value: "FastAPI" },
              { label: "流式输出", value: "SSE" },
              { label: "地图能力", value: "AMap" },
              { label: "会话状态", value: "Store" },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-white/10 bg-white/[0.055] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
              >
                <p className="text-stone-500">{item.label}</p>
                <p className="mt-1 font-semibold text-stone-100">{item.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>

        <div className="mt-3 rounded-lg border border-teal-200/[0.14] bg-teal-300/[0.075] p-4 text-sm leading-6 text-teal-50/80">
          <ShieldCheck className="mr-2 inline h-4 w-4 text-teal-200" aria-hidden="true" />
          不预加载示例行程，不替换真实接口；这里只展示工作台能力，实际生成仍走现有对话、SSE 和地图链路。
        </div>
      </div>
    </section>
  );
}
