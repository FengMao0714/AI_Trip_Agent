import type { LucideIcon } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface FeatureCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  tone: "teal" | "amber" | "sky" | "rose";
}

const toneClassName: Record<FeatureCardProps["tone"], string> = {
  teal: "bg-teal-50 text-teal-700",
  amber: "bg-amber-50 text-amber-700",
  sky: "bg-sky-50 text-sky-700",
  rose: "bg-rose-50 text-rose-700",
};

export function FeatureCard({
  icon: Icon,
  title,
  description,
  tone,
}: FeatureCardProps) {
  return (
    <Card className="rounded-lg border-zinc-200 shadow-sm">
      <CardHeader className="pb-3">
        <div
          className={`mb-4 flex h-10 w-10 items-center justify-center rounded-lg ${toneClassName[tone]}`}
        >
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <CardDescription className="text-base leading-7">
          {description}
        </CardDescription>
      </CardContent>
    </Card>
  );
}
