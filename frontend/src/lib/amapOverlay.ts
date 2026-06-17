import type { AMapOverlay } from "@/types/amap";

export function detachAMapOverlay(overlay: AMapOverlay, label: string) {
  try {
    overlay.setMap(null);
  } catch (error) {
    console.warn(`Failed to remove ${label}.`, error);
  }
}
