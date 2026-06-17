import { Badge } from "@/components/ui/badge";

interface CostBadgeProps {
  cost: number;
}

export function CostBadge({ cost }: CostBadgeProps) {
  const label = cost === 0 ? "免费" : `${cost} 元`;

  return (
    <Badge
      variant="outline"
      className="shrink-0 rounded-lg border-amber-200 bg-amber-50 text-amber-700"
    >
      {label}
    </Badge>
  );
}
