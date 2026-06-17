import { WalletCards } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface BudgetSummaryProps {
  total: number;
  budget?: number;
  byType: Array<{
    label: string;
    amount: number;
  }>;
}

export function BudgetSummary({ total, budget, byType }: BudgetSummaryProps) {
  const remaining = budget !== undefined ? budget - total : null;
  const remainingClass =
    remaining !== null && remaining < 0 ? "text-red-700" : "text-zinc-950";

  return (
    <Card className="rounded-lg shadow-sm">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <WalletCards className="h-5 w-5 text-amber-600" aria-hidden="true" />
          费用汇总
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-amber-50 p-4">
            <p className="text-sm text-amber-700">预计总花费</p>
            <p className="mt-1 text-2xl font-semibold text-zinc-950">
              {total} 元
            </p>
          </div>
          <div className="rounded-lg bg-teal-50 p-4">
            <p className="text-sm text-teal-700">
              {remaining !== null && remaining < 0 ? "超出预算" : "预算余量"}
            </p>
            <p className={`mt-1 text-2xl font-semibold ${remainingClass}`}>
              {remaining === null ? "未设置" : `${remaining} 元`}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          {byType.length > 0 ? (
            byType.map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between rounded-lg border border-zinc-200 px-3 py-2 text-sm"
              >
                <span className="text-zinc-600">{item.label}</span>
                <span className="font-medium text-zinc-950">{item.amount} 元</span>
              </div>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-zinc-300 px-3 py-3 text-sm text-zinc-500">
              暂无可拆分的费用明细。
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
