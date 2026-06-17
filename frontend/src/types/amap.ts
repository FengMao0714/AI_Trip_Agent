import type { Coordinates } from "@/types/map";

export type AMapPosition = [number, number];

export interface AMapOverlay {
  setMap(map: AMapMap | null): void;
}

export interface AMapMap {
  add(overlay: AMapOverlay | AMapOverlay[]): void;
  addControl(control: unknown): void;
  destroy(): void;
  remove(overlay: AMapOverlay | AMapOverlay[]): void;
  resize(): void;
  setCenter?(center: AMapPosition): void;
  setFitView(
    overlays?: AMapOverlay[],
    immediately?: boolean,
    avoid?: [number, number, number, number],
    maxZoom?: number,
  ): void;
  setZoomAndCenter?(zoom: number, center: AMapPosition): void;
}

export interface AMapMarker extends AMapOverlay {
  on(eventName: "click", handler: () => void): void;
  setzIndex(zIndex: number): void;
}

export type AMapPolyline = AMapOverlay;

export interface AMapInfoWindow {
  close(): void;
  open(map: AMapMap, position: AMapPosition): void;
}

export interface AMapNamespace {
  InfoWindow: new (options: {
    anchor?: string;
    content: HTMLElement;
    isCustom?: boolean;
    offset?: unknown;
  }) => AMapInfoWindow;
  Map: new (
    container: HTMLDivElement,
    options: {
      center: AMapPosition;
      mapStyle?: string;
      pitch?: number;
      resizeEnable?: boolean;
      viewMode?: "2D" | "3D";
      zoom: number;
    },
  ) => AMapMap;
  Marker: new (options: {
    anchor?: string;
    content?: HTMLElement;
    offset?: unknown;
    position: AMapPosition;
    zIndex?: number;
  }) => AMapMarker;
  Pixel: new (x: number, y: number) => unknown;
  Polyline: new (options: {
    borderWeight?: number;
    geodesic?: boolean;
    lineJoin?: string;
    path: AMapPosition[];
    showDir?: boolean;
    strokeColor: string;
    strokeOpacity?: number;
    strokeStyle?: string;
    strokeWeight?: number;
    zIndex?: number;
  }) => AMapPolyline;
  Scale?: new () => unknown;
  ToolBar?: new (options?: { position?: string }) => unknown;
}

export function toAMapPosition(coordinates: Coordinates): AMapPosition {
  return [coordinates.lng, coordinates.lat];
}
