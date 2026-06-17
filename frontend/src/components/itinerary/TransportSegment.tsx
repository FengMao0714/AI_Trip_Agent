import {
  Bike,
  Bus,
  Car,
  Footprints,
  Navigation,
  Route,
  Train,
} from "lucide-react";

import type { Transport, TransportMode } from "@/types/itinerary";

interface TransportSegmentProps {
  transport?: Transport;
}

const transportIcon: Record<TransportMode, typeof Route> = {
  步行: Footprints,
  公交: Bus,
  地铁: Train,
  打车: Car,
  驾车: Car,
  自驾: Car,
  包车: Car,
  网约车: Car,
  接驳: Bus,
  飞机: Navigation,
  火车: Train,
  骑行: Bike,
  未知: Navigation,
};

function inferTransportMode(transport: Transport): TransportMode {
  if (transport.mode !== "未知") {
    return transport.mode;
  }

  const text = transport.description ?? "";
  if (/地铁|轨道交通/u.test(text)) {
    return "地铁";
  }
  if (/步行|徒步/u.test(text)) {
    return "步行";
  }
  if (/公交|巴士/u.test(text)) {
    return "公交";
  }
  if (/网约|打车|出租/u.test(text)) {
    return "打车";
  }
  if (/高铁|火车|动车|城际/u.test(text)) {
    return "火车";
  }
  if (/接驳|摆渡/u.test(text)) {
    return "接驳";
  }

  return "未知";
}

export function TransportSegment({ transport }: TransportSegmentProps) {
  if (!transport) {
    return null;
  }

  const inferredMode = inferTransportMode(transport);
  const Icon = transportIcon[inferredMode] ?? Route;
  const modeLabel = inferredMode === "未知" ? "交通方式待确认" : inferredMode;
  const distanceLabel =
    transport.distance_km > 0 ? `${transport.distance_km} km` : "距离待确认";
  const durationLabel =
    transport.duration_min > 0 ? `${transport.duration_min} 分钟` : "时间待确认";

  return (
    <div className="ml-[4.25rem] flex items-start gap-3 border-l border-dashed border-teal-300/25 py-3 pl-5 text-sm text-stone-500">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/[0.06] text-stone-300">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="font-medium text-stone-300">
          {modeLabel} · {distanceLabel} · {durationLabel}
        </p>
        {transport.description ? (
          <p className="mt-1 leading-6">{transport.description}</p>
        ) : null}
      </div>
    </div>
  );
}
