import { Gauge, WalletCards } from "lucide-react";

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
    remaining !== null && remaining < 0 ? "text-red-200" : "text-stone-50";
  const usage =
    budget !== undefined && budget > 0
      ? Math.min(120, Math.round((total / budget) * 100))
      : null;
  const maxAmount = Math.max(...byType.map((item) => item.amount), 1);

  return (
    <Card className="rounded-xl border-amber-300/18 bg-[linear-gradient(135deg,rgba(245,158,11,0.13),rgba(8,18,17,0.98)_34%,rgba(4,9,9,0.98))] text-stone-100 shadow-[0_22px_60px_rgba(0,0,0,0.30),inset_0_1px_0_rgba(255,255,255,0.06)]">
      <CardHeader className="pb-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-lg text-amber-50">
            <WalletCards className="h-5 w-5 text-amber-300" aria-hidden="true" />
            旅行预算
          </CardTitle>
          <span className="inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.05] px-2.5 py-1 text-xs font-semibold text-stone-300">
            <Gauge className="h-3.5 w-3.5" aria-hidden="true" />
            预算使用率 {usage === null ? "未设置" : `${usage}%`}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-amber-300/20 bg-amber-400/10 p-4">
            <p className="text-sm text-amber-100">预计总花费</p>
            <p className="mt-1 text-2xl font-semibold text-stone-50">
              {total} 元
            </p>
          </div>
          <div className="rounded-lg border border-teal-300/20 bg-teal-400/10 p-4">
            <p className="text-sm text-teal-100">
              {remaining !== null && remaining < 0 ? "超出预算" : "预算余量"}
            </p>
            <p className={`mt-1 text-2xl font-semibold ${remainingClass}`}>
              {remaining === null ? "未设置" : `${remaining} 元`}
            </p>
          </div>
        </div>
        {usage !== null ? (
          <div className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
            <div className="mb-2 flex items-center justify-between text-xs text-stone-500">
              <span>预算进度</span>
              <span>{total} / {budget} 元</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className={`h-full rounded-full ${
                  usage > 100 ? "bg-red-400" : usage > 85 ? "bg-amber-300" : "bg-teal-300"
                }`}
                style={{ width: `${Math.min(100, usage)}%` }}
              />
            </div>
          </div>
        ) : null}

        <div className="space-y-2">
          {byType.length > 0 ? (
            byType.map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2 text-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-stone-400">{item.label}</span>
                  <span className="font-medium text-stone-100">{item.amount} 元</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-amber-300"
                    style={{ width: `${Math.max(6, (item.amount / maxAmount) * 100)}%` }}
                  />
                </div>
              </div>
            ))
          ) : (
            <div className="rounded-lg border border-dashed border-white/15 px-3 py-3 text-sm text-stone-500">
              暂无可拆分的费用明细。
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
