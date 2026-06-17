import { Bot, CloudSun, MapPinned, WalletCards } from "lucide-react";

import { FeatureCard } from "@/components/landing/FeatureCard";

const features = [
  {
    icon: Bot,
    title: "对话式规划",
    description: "从自然语言里提取目的地、天数、预算和偏好，必要时继续追问补齐信息。",
    tone: "teal" as const,
  },
  {
    icon: MapPinned,
    title: "真实地点与路线",
    description: "围绕 POI、路线距离和交通耗时组织行程，减少只好看但难执行的安排。",
    tone: "sky" as const,
  },
  {
    icon: CloudSun,
    title: "天气感知",
    description: "结合未来天气调整户外、室内和休息节点，让每天的节奏更稳。",
    tone: "amber" as const,
  },
  {
    icon: WalletCards,
    title: "预算约束",
    description: "把门票、餐饮、住宿和市内交通放进同一张账单，保留机动空间。",
    tone: "rose" as const,
  },
];

export function FeatureGrid() {
  return (
    <section className="bg-zinc-50 py-16 sm:py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <p className="text-sm font-semibold uppercase text-teal-700">
            Agent Workflow
          </p>
          <h2 className="mt-3 text-3xl font-semibold text-zinc-950 sm:text-4xl">
            从想法到行程，一屏完成
          </h2>
          <p className="mt-4 text-base leading-7 text-zinc-600">
            前端围绕对话、行程卡片和地图视图展开，后续可以直接接入 SSE 流和高德地图数据。
          </p>
        </div>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </div>
    </section>
  );
}
