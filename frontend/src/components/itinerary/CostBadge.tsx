import { Badge } from "@/components/ui/badge";

interface CostBadgeProps {
  cost: number;
}

export function CostBadge({ cost }: CostBadgeProps) {
  const label = cost === 0 ? "免费" : `${cost} 元`;

  return (
    <Badge
      variant="outline"
      className="shrink-0 rounded-lg border-amber-300/25 bg-amber-400/10 text-amber-100"
    >
      {label}
    </Badge>
  );
}
