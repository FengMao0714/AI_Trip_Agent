"use client";

import { useEffect, useRef } from "react";

import type { AMapMap, AMapMarker, AMapNamespace } from "@/types/amap";
import { detachAMapOverlay } from "@/lib/amapOverlay";
import type { ActivityType } from "@/types/itinerary";
import type { POIMarker as POIMarkerData } from "@/types/map";

interface POIMarkerProps {
  active?: boolean;
  amap: AMapNamespace | null;
  map: AMapMap | null;
  marker: POIMarkerData;
  onClick: (marker: POIMarkerData) => void;
  onOverlayReady: (id: string, overlay: AMapMarker) => void;
  onOverlayRemove: (id: string) => void;
}

const markerColor: Record<ActivityType, string> = {
  景点: "bg-sky-500",
  餐厅: "bg-amber-400 text-zinc-950",
  住宿: "bg-violet-500",
  交通: "bg-teal-400 text-zinc-950",
  其他: "bg-stone-500",
};

function getMarkerClassName(type: ActivityType, active: boolean) {
  return [
    "flex h-8 w-8 items-center justify-center rounded-full border-2 border-white/80 text-xs font-bold text-white shadow-[0_0_26px_rgba(45,212,191,0.35)] transition-transform",
    markerColor[type],
    active ? "scale-110 ring-4 ring-teal-300/35" : "",
  ].join(" ");
}

function hasValidMarkerCoordinates(lng: number, lat: number) {
  return (
    Number.isFinite(lng) &&
    Number.isFinite(lat) &&
    lng >= -180 &&
    lng <= 180 &&
    lat >= -90 &&
    lat <= 90 &&
    !(lng === 0 && lat === 0)
  );
}

export function POIMarker({
  active = false,
  amap,
  map,
  marker,
  onClick,
  onOverlayReady,
  onOverlayRemove,
}: POIMarkerProps) {
  const { day, id, lat, lng, name, type } = marker;
  const activeRef = useRef(active);
  const contentRef = useRef<HTMLButtonElement | null>(null);
  const markerRef = useRef(marker);
  const onClickRef = useRef(onClick);
  const overlayRef = useRef<AMapMarker | null>(null);

  activeRef.current = active;
  markerRef.current = marker;
  onClickRef.current = onClick;

  useEffect(() => {
    const content = contentRef.current;
    if (content) {
      content.className = getMarkerClassName(type, active);
    }

    try {
      overlayRef.current?.setzIndex(active ? 120 : 100);
    } catch (error) {
      console.warn("Failed to update POI marker zIndex.", error);
    }
  }, [active, type]);

  useEffect(() => {
    if (!amap || !map || !hasValidMarkerCoordinates(lng, lat)) {
      contentRef.current = null;
      overlayRef.current = null;
      return undefined;
    }

    const content = document.createElement("button");
    contentRef.current = content;
    content.type = "button";
    content.title = name;
    content.className = getMarkerClassName(type, activeRef.current);
    content.textContent = day.toString();
    const handleContentClick = (event: MouseEvent) => {
      event.stopPropagation();
      onClickRef.current(markerRef.current);
    };
    content.addEventListener("click", handleContentClick);

    const overlay = new amap.Marker({
      anchor: "bottom-center",
      content,
      offset: new amap.Pixel(0, 0),
      position: [lng, lat],
      zIndex: activeRef.current ? 120 : 100,
    });
    overlayRef.current = overlay;

    const handleOverlayClick = () => onClickRef.current(markerRef.current);
    overlay.on("click", handleOverlayClick);

    try {
      map.add(overlay);
    } catch (error) {
      console.warn("Failed to add POI marker overlay.", error);
      detachAMapOverlay(overlay, "POI marker overlay");
      content.removeEventListener("click", handleContentClick);
      contentRef.current = null;
      overlayRef.current = null;
      return undefined;
    }

    onOverlayReady(id, overlay);

    return () => {
      onOverlayRemove(id);
      content.removeEventListener("click", handleContentClick);
      detachAMapOverlay(overlay, "POI marker overlay");
      if (contentRef.current === content) {
        contentRef.current = null;
      }
      if (overlayRef.current === overlay) {
        overlayRef.current = null;
      }
    };
  }, [
    amap,
    day,
    id,
    lat,
    lng,
    map,
    name,
    onOverlayReady,
    onOverlayRemove,
    type,
  ]);

  return null;
}
