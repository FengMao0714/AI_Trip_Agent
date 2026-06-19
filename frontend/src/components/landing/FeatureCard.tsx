import type { LucideIcon } from "lucide-react";

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  metric: string;
  description: string;
  tone: "teal" | "amber" | "sky" | "rose";
}

const toneClassName: Record<FeatureCardProps["tone"], string> = {
  teal: "border-teal-200/[0.18] bg-teal-300/[0.075] text-teal-100",
  amber: "border-amber-200/[0.18] bg-amber-300/[0.08] text-amber-100",
  sky: "border-sky-200/[0.18] bg-sky-300/[0.075] text-sky-100",
  rose: "border-rose-200/[0.18] bg-rose-300/[0.075] text-rose-100",
};

export function FeatureCard({
  icon: Icon,
  title,
  metric,
  description,
  tone,
}: FeatureCardProps) {
  return (
    <article className="rounded-lg border border-white/10 bg-white/[0.055] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-lg border ${toneClassName[tone]}`}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <span className="rounded-full border border-white/10 bg-black/20 px-2.5 py-1 text-xs font-semibold text-stone-300">
          {metric}
        </span>
      </div>
      <h3 className="mt-5 text-lg font-semibold text-white">{title}</h3>
      <p className="mt-3 text-sm leading-6 text-stone-400">{description}</p>
    </article>
  );
}
