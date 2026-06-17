import type { ActivityType, TransportMode } from './itinerary';

export interface Coordinates {
  lng: number;
  lat: number;
}

export interface POIMarker extends Coordinates {
  id: string;
  name: string;
  type: ActivityType;
  day: number;
  time_slot?: string;
  description?: string;
  cost?: number;
  address?: string;
  rating?: number;
  source?: string;
  source_refs?: string[];
}

export interface RoutePath {
  id: string;
  day: number;
  mode: TransportMode;
  origin: Coordinates;
  destination: Coordinates;
  distance_km: number;
  duration_min: number;
  polyline?: Coordinates[];
}

export interface MapViewport {
  center: Coordinates;
  zoom: number;
}

export interface DayRouteLayer {
  day: number;
  markers: POIMarker[];
  routes: RoutePath[];
  visible: boolean;
}
