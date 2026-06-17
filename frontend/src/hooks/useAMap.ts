"use client";

import { useEffect, useState } from "react";
import * as AMapLoader from "@amap/amap-jsapi-loader";

import type { AMapMap, AMapNamespace } from "@/types/amap";

declare global {
  interface Window {
    _AMapSecurityConfig?: {
      securityJsCode: string;
    };
  }
}

interface UseAMapResult {
  amap: AMapNamespace | null;
  error: string | null;
  isLoading: boolean;
  map: AMapMap | null;
}

function hasUsableMapSize(container: HTMLDivElement) {
  const rect = container.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

export function useAMap(
  containerRef: React.RefObject<HTMLDivElement | null>,
): UseAMapResult {
  const [amap, setAMap] = useState<AMapNamespace | null>(null);
  const [map, setMap] = useState<AMapMap | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    const key = process.env.NEXT_PUBLIC_AMAP_KEY;
    const securityJsCode = process.env.NEXT_PUBLIC_AMAP_SECRET;
    let mounted = true;
    let createdMap: AMapMap | null = null;
    let isCreating = false;
    let frameId: number | null = null;
    let resizeObserver: ResizeObserver | null = null;

    if (!container) {
      return undefined;
    }

    if (!key || !securityJsCode) {
      setError("请配置 NEXT_PUBLIC_AMAP_KEY 和 NEXT_PUBLIC_AMAP_SECRET");
      setIsLoading(false);
      return undefined;
    }

    const amapKey = key;
    const amapSecurityJsCode = securityJsCode;

    window._AMapSecurityConfig = {
      securityJsCode: amapSecurityJsCode,
    };

    setIsLoading(true);
    setError(null);

    function createMapWhenVisible() {
      const currentContainer = containerRef.current;
      if (
        !mounted ||
        isCreating ||
        createdMap ||
        !currentContainer ||
        !hasUsableMapSize(currentContainer)
      ) {
        return;
      }

      isCreating = true;

      AMapLoader.load({
        key: amapKey,
        version: "2.0",
        plugins: ["AMap.Scale", "AMap.ToolBar"],
      })
        .then((loadedAMap: AMapNamespace) => {
          const latestContainer = containerRef.current;
          if (!mounted || !latestContainer || !hasUsableMapSize(latestContainer)) {
            isCreating = false;
            return;
          }

          createdMap = new loadedAMap.Map(latestContainer, {
            center: [116.397428, 39.90923],
            mapStyle: "amap://styles/darkblue",
            pitch: 30,
            resizeEnable: true,
            viewMode: "3D",
            zoom: 11,
          });

          if (loadedAMap.Scale) {
            createdMap.addControl(new loadedAMap.Scale());
          }

          if (loadedAMap.ToolBar) {
            createdMap.addControl(new loadedAMap.ToolBar({ position: "RB" }));
          }

          window.requestAnimationFrame(() => createdMap?.resize());

          setAMap(loadedAMap);
          setMap(createdMap);
          setIsLoading(false);
        })
        .catch((loadError: unknown) => {
          if (!mounted) {
            return;
          }

          isCreating = false;
          setError(
            loadError instanceof Error
              ? loadError.message
              : "高德地图加载失败，请检查 Key 和网络",
          );
          setIsLoading(false);
        });
    }

    if (typeof ResizeObserver !== "undefined") {
      resizeObserver = new ResizeObserver(() => {
        createMapWhenVisible();
        createdMap?.resize();
      });
      resizeObserver.observe(container);
    }

    frameId = window.requestAnimationFrame(createMapWhenVisible);

    return () => {
      mounted = false;
      if (frameId !== null) {
        window.cancelAnimationFrame(frameId);
      }
      resizeObserver?.disconnect();
      createdMap?.destroy();
    };
  }, [containerRef]);

  return { amap, error, isLoading, map };
}
