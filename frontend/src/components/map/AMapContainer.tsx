"use client";

import { AlertTriangle, Loader2, MapPinned } from "lucide-react";
import type { RefObject } from "react";

interface AMapContainerProps {
  containerRef: RefObject<HTMLDivElement | null>;
  error?: string | null;
  isLoading?: boolean;
}

export function AMapContainer({
  containerRef,
  error,
  isLoading,
}: AMapContainerProps) {
  return (
    <div className="relative h-full min-h-[420px] overflow-hidden rounded-lg border border-white/10 bg-[#050b0b]">
      <div ref={containerRef} className="absolute inset-0" />

      {isLoading ? (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#050b0b]/80 text-sm text-stone-300 backdrop-blur-sm">
          <Loader2 className="mr-2 h-4 w-4 animate-spin text-teal-300" />
          地图加载中
        </div>
      ) : null}

      {error ? (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-[#050b0b] p-6">
          <div className="max-w-sm rounded-lg border border-amber-300/25 bg-amber-400/10 p-4 text-sm text-amber-100">
            <div className="mb-2 flex items-center gap-2 font-semibold">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              地图暂不可用
            </div>
            <p className="leading-6">{error}</p>
          </div>
        </div>
      ) : null}

      {!isLoading && !error ? (
        <div className="pointer-events-none absolute left-3 top-3 z-10 flex items-center gap-2 rounded-lg border border-white/10 bg-[#07100f]/85 px-3 py-2 text-xs font-medium text-stone-300 shadow-lg backdrop-blur">
          <MapPinned className="h-4 w-4 text-teal-300" aria-hidden="true" />
          高德地图
        </div>
      ) : null}
    </div>
  );
}
