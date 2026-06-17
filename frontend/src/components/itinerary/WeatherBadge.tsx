import { CloudSun, Wind } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Weather } from "@/types/itinerary";

interface WeatherBadgeProps {
  weather?: Weather;
}

export function WeatherBadge({ weather }: WeatherBadgeProps) {
  if (!weather) {
    return null;
  }

  const temperature =
    weather.temperature_min !== undefined && weather.temperature_max !== undefined
      ? `${weather.temperature_min}-${weather.temperature_max}°C`
      : null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Badge
        variant="outline"
        className="gap-1 rounded-lg border-sky-300/20 bg-sky-400/10 text-sky-100"
      >
        <CloudSun className="h-3.5 w-3.5" aria-hidden="true" />
        {weather.condition}
        {temperature ? ` ${temperature}` : ""}
      </Badge>
      {weather.wind ? (
        <Badge
          variant="outline"
          className="gap-1 rounded-lg border-white/10 bg-white/[0.04] text-stone-300"
        >
          <Wind className="h-3.5 w-3.5" aria-hidden="true" />
          {weather.wind}
        </Badge>
      ) : null}
    </div>
  );
}
