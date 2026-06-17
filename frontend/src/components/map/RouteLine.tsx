"use client";

import { useEffect } from "react";

import type { AMapMap, AMapNamespace, AMapOverlay } from "@/types/amap";
import { detachAMapOverlay } from "@/lib/amapOverlay";
import { toAMapPosition } from "@/types/amap";
import type { RoutePath } from "@/types/map";

interface RouteLineProps {
  amap: AMapNamespace | null;
  map: AMapMap | null;
  onOverlayReady: (id: string, overlay: AMapOverlay) => void;
  onOverlayRemove: (id: string) => void;
  route: RoutePath;
}

const routeColor: Record<number, string> = {
  1: "#2563eb",
  2: "#059669",
  3: "#f97316",
};

function hasValidCoordinates(value: { lng: number; lat: number }) {
  return (
    Number.isFinite(value.lng) &&
    Number.isFinite(value.lat) &&
    value.lng >= -180 &&
    value.lng <= 180 &&
    value.lat >= -90 &&
    value.lat <= 90 &&
    !(value.lng === 0 && value.lat === 0)
  );
}

export function RouteLine({
  amap,
  map,
  onOverlayReady,
  onOverlayRemove,
  route,
}: RouteLineProps) {
  useEffect(() => {
    if (
      !amap ||
      !map ||
      !hasValidCoordinates(route.origin) ||
      !hasValidCoordinates(route.destination) ||
      route.polyline?.some((point) => !hasValidCoordinates(point))
    ) {
      return undefined;
    }

    const path = (route.polyline ?? [route.origin, route.destination]).map(
      toAMapPosition,
    );
    const overlay = new amap.Polyline({
      borderWeight: 1,
      geodesic: true,
      lineJoin: "round",
      path,
      showDir: true,
      strokeColor: routeColor[route.day] ?? "#7c3aed",
      strokeOpacity: 0.86,
      strokeStyle: route.mode === "步行" ? "dashed" : "solid",
      strokeWeight: 5,
      zIndex: 60,
    });

    try {
      map.add(overlay);
    } catch (error) {
      console.warn("Failed to add route overlay.", error);
      detachAMapOverlay(overlay, "route overlay");
      return undefined;
    }

    onOverlayReady(route.id, overlay);

    return () => {
      onOverlayRemove(route.id);
      detachAMapOverlay(overlay, "route overlay");
    };
  }, [amap, map, onOverlayReady, onOverlayRemove, route]);

  return null;
}
