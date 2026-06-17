"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, MapPinned, Route, ShieldCheck } from "lucide-react";

import { AMapContainer } from "@/components/map/AMapContainer";
import { DayFilterBar } from "@/components/map/DayFilterBar";
import { MarkerPopup } from "@/components/map/MarkerPopup";
import { POIMarker } from "@/components/map/POIMarker";
import { RouteLine } from "@/components/map/RouteLine";
import { useAMap } from "@/hooks/useAMap";
import { getItineraryInsights } from "@/lib/itineraryInsights";
import type { Itinerary } from "@/types/itinerary";
import type { AMapOverlay } from "@/types/amap";
import type { POIMarker as POIMarkerData, RoutePath } from "@/types/map";

type SelectedDay = "all" | number;

const FIT_VIEW_PADDING: [number, number, number, number] = [56, 40, 56, 40];

interface MapViewProps {
  itinerary: Itinerary;
}

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

function hasUsableContainerSize(container: HTMLDivElement | null) {
  if (!container) {
    return false;
  }

  const rect = container.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function markerCenter(markers: POIMarkerData[]) {
  if (markers.length === 0) {
    return null;
  }

  const total = markers.reduce(
    (sum, marker) => ({
      lat: sum.lat + marker.lat,
      lng: sum.lng + marker.lng,
    }),
    { lat: 0, lng: 0 },
  );

  return {
    lat: total.lat / markers.length,
    lng: total.lng / markers.length,
  };
}

function createMapLayers(itinerary: Itinerary) {
  const markers: POIMarkerData[] = [];
  const routes: RoutePath[] = [];

  itinerary.days.forEach((day) => {
    day.activities.forEach((activity, index) => {
      if (!hasValidCoordinates(activity)) {
        return;
      }

      const id = `day-${day.day}-activity-${index}`;

      markers.push({
        address: activity.address,
        cost: activity.cost,
        day: day.day,
        description: activity.description,
        id,
        lat: activity.lat,
        lng: activity.lng,
        name: activity.place_name,
        rating: activity.rating,
        source: activity.source,
        source_refs: activity.source_refs,
        is_verified: activity.is_verified,
        time_slot: activity.time_slot,
        type: activity.place_type,
      });

      const previousActivity = day.activities[index - 1];

      if (
        index > 0 &&
        previousActivity &&
        hasValidCoordinates(previousActivity) &&
        activity.transport
      ) {
        routes.push({
          day: day.day,
          destination: {
            lat: activity.lat,
            lng: activity.lng,
          },
          distance_km: activity.transport.distance_km,
          duration_min: activity.transport.duration_min,
          id: `day-${day.day}-route-${index}`,
          mode: activity.transport.mode,
          origin: {
            lat: previousActivity.lat,
            lng: previousActivity.lng,
          },
        });
      }
    });
  });

  return { markers, routes };
}

export function MapView({ itinerary }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const { amap, error, isLoading, map } = useAMap(containerRef);
  const [selectedDay, setSelectedDay] = useState<SelectedDay>("all");
  const [selectedMarker, setSelectedMarker] = useState<POIMarkerData | null>(
    null,
  );
  const overlaysRef = useRef(new Map<string, AMapOverlay>());

  const { markers, routes } = useMemo(
    () => createMapLayers(itinerary),
    [itinerary],
  );
  const insights = useMemo(() => getItineraryInsights(itinerary), [itinerary]);

  const visibleMarkers = useMemo(
    () =>
      selectedDay === "all"
        ? markers
        : markers.filter((marker) => marker.day === selectedDay),
    [markers, selectedDay],
  );

  const visibleRoutes = useMemo(
    () =>
      selectedDay === "all"
        ? routes
        : routes.filter((route) => route.day === selectedDay),
    [routes, selectedDay],
  );

  const visibleActivities = useMemo(
    () =>
      itinerary.days
        .filter((day) => selectedDay === "all" || day.day === selectedDay)
        .flatMap((day) =>
          day.activities.map((activity) => ({
            day: day.day,
            name: activity.place_name,
            timeSlot: activity.time_slot,
          })),
        ),
    [itinerary.days, selectedDay],
  );

  const visibleOverlayIds = useMemo(
    () => [
      ...visibleRoutes.map((route) => route.id),
      ...visibleMarkers.map((marker) => marker.id),
    ],
    [visibleMarkers, visibleRoutes],
  );

  const fitVisibleOverlays = useCallback(() => {
    if (!map || !hasUsableContainerSize(containerRef.current)) {
      return;
    }

    const overlays = visibleOverlayIds
      .map((id) => overlaysRef.current.get(id))
      .filter((overlay): overlay is AMapOverlay => Boolean(overlay));

    if (overlays.length > 0) {
      window.requestAnimationFrame(() => {
        if (!hasUsableContainerSize(containerRef.current)) {
          return;
        }

        try {
          map.resize();
          map.setFitView(overlays, false, FIT_VIEW_PADDING, 14);
        } catch (error) {
          console.warn("Failed to fit map overlays.", error);
        }
      });
      return;
    }

    const center = markerCenter(visibleMarkers);
    if (center) {
      window.requestAnimationFrame(() => {
        if (!hasUsableContainerSize(containerRef.current)) {
          return;
        }

        try {
          map.resize();
          if (map.setZoomAndCenter) {
            map.setZoomAndCenter(12, [center.lng, center.lat]);
          } else {
            map.setCenter?.([center.lng, center.lat]);
          }
        } catch (error) {
          console.warn("Failed to center map markers.", error);
        }
      });
    }
  }, [map, visibleMarkers, visibleOverlayIds]);

  const handleSelectedDayChange = useCallback((day: SelectedDay) => {
    setSelectedDay(day);
    setSelectedMarker(null);
  }, []);

  const handleOverlayReady = useCallback(
    (id: string, overlay: AMapOverlay) => {
      overlaysRef.current.set(id, overlay);
      fitVisibleOverlays();
    },
    [fitVisibleOverlays],
  );

  const handleOverlayRemove = useCallback((id: string) => {
    overlaysRef.current.delete(id);
  }, []);

  useEffect(() => {
    if (
      selectedDay !== "all" &&
      !itinerary.days.some((day) => day.day === selectedDay)
    ) {
      setSelectedDay("all");
      setSelectedMarker(null);
    }
  }, [itinerary.days, selectedDay]);

  useEffect(() => {
    if (
      selectedMarker &&
      !visibleMarkers.some((marker) => marker.id === selectedMarker.id)
    ) {
      setSelectedMarker(null);
    }
  }, [selectedMarker, visibleMarkers]);

  useEffect(() => {
    fitVisibleOverlays();
  }, [fitVisibleOverlays]);

  useEffect(() => {
    if (!map || visibleMarkers.length === 0) {
      return undefined;
    }

    const timer = window.setTimeout(fitVisibleOverlays, 600);
    return () => window.clearTimeout(timer);
  }, [fitVisibleOverlays, map, visibleMarkers.length]);

  return (
    <div className="flex h-full min-h-[520px] flex-col overflow-hidden rounded-xl border border-white/10 bg-[#07100f] text-stone-100 shadow-[0_24px_70px_rgba(0,0,0,0.36),inset_0_1px_0_rgba(255,255,255,0.06)]">
      <div className="border-b border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.045),rgba(255,255,255,0.015))] px-4 py-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-teal-200/80">
              Map Verification
            </p>
            <h3 className="mt-1 text-base font-semibold text-amber-50">
              行程地图
            </h3>
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <span className="inline-flex items-center gap-1 rounded-md bg-teal-400/10 px-2 py-1 font-semibold text-teal-100 ring-1 ring-teal-300/20">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              {insights.mapVerifiedCount}/{insights.activityCount}
            </span>
            <span className="inline-flex items-center gap-1 rounded-md bg-sky-400/10 px-2 py-1 font-semibold text-sky-100 ring-1 ring-sky-300/20">
              <Route className="h-3.5 w-3.5" aria-hidden="true" />
              {routes.length} 段
            </span>
            <span className="inline-flex items-center gap-1 rounded-md bg-amber-400/10 px-2 py-1 font-semibold text-amber-100 ring-1 ring-amber-300/20">
              <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
              缺 {insights.coordinateMissingCount}
            </span>
          </div>
        </div>
      </div>
      <div className="relative min-h-[420px] flex-1">
        <AMapContainer
          containerRef={containerRef}
          error={error}
          isLoading={isLoading}
        />

        {!error ? (
          <>
          {visibleRoutes.map((route) => (
            <RouteLine
              key={route.id}
              amap={amap}
              map={map}
              onOverlayReady={handleOverlayReady}
              onOverlayRemove={handleOverlayRemove}
              route={route}
            />
          ))}

          {visibleMarkers.map((marker) => (
            <POIMarker
              key={marker.id}
              active={selectedMarker?.id === marker.id}
              amap={amap}
              map={map}
              marker={marker}
              onClick={setSelectedMarker}
              onOverlayReady={handleOverlayReady}
              onOverlayRemove={handleOverlayRemove}
            />
          ))}

          <MarkerPopup amap={amap} map={map} marker={selectedMarker} />

          <div className="absolute left-3 right-3 top-14 z-10 sm:left-4 sm:right-auto">
            <DayFilterBar
              days={itinerary.days}
              selectedDay={selectedDay}
              onSelectedDayChange={handleSelectedDayChange}
            />
          </div>

          <div className="absolute bottom-3 left-3 z-10 rounded-lg border border-white/10 bg-[#07100f]/90 px-3 py-2 text-xs text-stone-400 shadow-lg backdrop-blur">
            <MapPinned className="mr-1 inline h-3.5 w-3.5 text-teal-300" aria-hidden="true" />
            <span className="font-semibold text-stone-100">
              {visibleMarkers.length}
            </span>{" "}
            个地点 ·{" "}
            <span className="font-semibold text-stone-100">
              {visibleRoutes.length}
            </span>{" "}
            段路线
          </div>

          {visibleMarkers.length === 0 ? (
            <div className="absolute inset-x-4 top-28 z-10 mx-auto max-w-md rounded-lg border border-amber-300/25 bg-[#100d06]/95 px-4 py-3 text-sm leading-6 text-amber-100 shadow-lg backdrop-blur">
              <p>
                {markers.length === 0
                  ? "行程中暂无可用经纬度，地图标注会在 Agent 返回坐标后显示。"
                  : "当前筛选暂无可用经纬度，可切换到其他天查看地图标注。"}
              </p>
              {visibleActivities.length > 0 ? (
                <div className="mt-2 space-y-1 text-xs text-amber-100/90">
                  {visibleActivities.slice(0, 8).map((activity, index) => (
                    <p
                      key={`${activity.day}-${activity.timeSlot}-${activity.name}-${index}`}
                      className="truncate"
                      title={activity.name}
                    >
                      Day {activity.day} · {activity.timeSlot} · {activity.name}
                    </p>
                  ))}
                  {visibleActivities.length > 8 ? (
                    <p className="text-amber-200/80">
                      另有 {visibleActivities.length - 8} 个行程点待坐标确认
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {visibleMarkers.length > 0 ? (
            <div className="absolute bottom-3 right-3 z-10 max-h-44 w-56 overflow-auto rounded-lg border border-white/10 bg-[#07100f]/90 p-3 text-xs text-stone-400 shadow-lg backdrop-blur">
              <p className="mb-2 font-semibold text-stone-100">当前地图点位</p>
              <div className="space-y-1.5">
                {visibleMarkers.slice(0, 6).map((marker) => (
                  <button
                    key={marker.id}
                    type="button"
                    className="block w-full truncate rounded-md px-2 py-1 text-left hover:bg-teal-400/10 hover:text-teal-100"
                    onClick={() => setSelectedMarker(marker)}
                    title={marker.name}
                  >
                    Day {marker.day} · {marker.name}
                  </button>
                ))}
              </div>
              {visibleMarkers.length > 6 ? (
                <p className="mt-2 text-stone-500">
                  另有 {visibleMarkers.length - 6} 个地点
                </p>
              ) : null}
            </div>
          ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}
