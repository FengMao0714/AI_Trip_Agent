"use client";

import { useEffect } from "react";

import { formatSourceLabel, formatSourceRefs } from "@/lib/sourceLabels";
import type { AMapMap, AMapNamespace } from "@/types/amap";
import type { POIMarker } from "@/types/map";

interface MarkerPopupProps {
  amap: AMapNamespace | null;
  map: AMapMap | null;
  marker: POIMarker | null;
}

function appendText(parent: HTMLElement, tag: string, text: string, className: string) {
  const node = document.createElement(tag);
  node.textContent = text;
  node.className = className;
  parent.appendChild(node);
}

function formatRating(rating?: number) {
  return typeof rating === "number" && Number.isFinite(rating) && rating > 0
    ? `${rating.toFixed(1)} 分`
    : "评分待确认";
}

function isTransportLikeMarker(marker: POIMarker) {
  const markerText = [
    marker.type,
    marker.name,
    marker.description,
    marker.time_slot,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    marker.type === "交通" ||
    /高铁|动车|火车|车站|机场|航班|返程|离店|前往|去往|转场|出发|抵达|地铁|公交|打车|接驳/u.test(
      markerText,
    )
  );
}

function getRatingLine(marker: POIMarker) {
  if (isTransportLikeMarker(marker)) {
    return null;
  }

  return `评分：${formatRating(marker.rating)}`;
}

function hasValidMarkerCoordinates(marker: POIMarker) {
  return (
    Number.isFinite(marker.lng) &&
    Number.isFinite(marker.lat) &&
    marker.lng >= -180 &&
    marker.lng <= 180 &&
    marker.lat >= -90 &&
    marker.lat <= 90 &&
    !(marker.lng === 0 && marker.lat === 0)
  );
}

export function MarkerPopup({ amap, map, marker }: MarkerPopupProps) {
  useEffect(() => {
    if (!amap || !map || !marker || !hasValidMarkerCoordinates(marker)) {
      return undefined;
    }

    const content = document.createElement("div");
    content.className =
      "min-w-56 rounded-lg border border-zinc-200 bg-white p-3 text-zinc-950 shadow-lg";

    appendText(content, "div", marker.name, "text-sm font-semibold");
    appendText(
      content,
      "div",
      `Day ${marker.day} · ${marker.time_slot ?? "时间待定"} · ${marker.type}`,
      "mt-1 text-xs text-zinc-500",
    );

    if (marker.description) {
      appendText(content, "p", marker.description, "mt-2 line-clamp-3 text-xs leading-5 text-zinc-600");
    }

    appendText(
      content,
      "div",
      `地址：${marker.address ?? "地址待确认"}`,
      "mt-2 text-xs leading-5 text-zinc-600",
    );
    const ratingLine = getRatingLine(marker);
    if (ratingLine) {
      appendText(
        content,
        "div",
        ratingLine,
        "mt-1 text-xs leading-5 text-zinc-600",
      );
    }

    if (marker.source) {
      const sourceRefs = formatSourceRefs(marker.source_refs, 2);
      appendText(
        content,
        "div",
        `来源：${formatSourceLabel(marker.source, marker.source_refs)}${
          sourceRefs.length > 0 ? `（参考：${sourceRefs.join("、")}）` : ""
        }`,
        "mt-1 text-xs leading-5 text-zinc-600",
      );
    }

    appendText(
      content,
      "div",
      `${marker.cost ?? 0} 元`,
      "mt-3 inline-flex rounded-md bg-teal-50 px-2 py-1 text-xs font-semibold text-teal-700",
    );

    const infoWindow = new amap.InfoWindow({
      anchor: "bottom-center",
      content,
      isCustom: true,
      offset: new amap.Pixel(0, -34),
    });

    try {
      infoWindow.open(map, [marker.lng, marker.lat]);
    } catch (error) {
      console.warn("Failed to open marker popup.", error);
      infoWindow.close();
      return undefined;
    }

    return () => {
      infoWindow.close();
    };
  }, [amap, map, marker]);

  return null;
}
