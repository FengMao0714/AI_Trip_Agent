export type ActivityType = '景点' | '餐厅' | '住宿' | '交通' | '其他';

export type TransportMode =
  | '步行'
  | '公交'
  | '地铁'
  | '打车'
  | '驾车'
  | '自驾'
  | '包车'
  | '网约车'
  | '接驳'
  | '飞机'
  | '火车'
  | '骑行'
  | '未知';

export interface UserProfile {
  destination: string;
  days: number;
  budget: number;
  style: string;
  diet_preference: string;
}

export interface GenerationSource {
  kind: string;
  label: string;
  detail?: string;
  tools?: string[];
  is_fallback?: boolean;
}

export interface Transport {
  mode: TransportMode;
  distance_km: number;
  duration_min: number;
  description?: string;
}

export interface Weather {
  condition: string;
  temperature_min?: number;
  temperature_max?: number;
  wind?: string;
  advice?: string;
}

export interface Activity {
  time_slot: string;
  place_name: string;
  place_type: ActivityType;
  lng: number;
  lat: number;
  description: string;
  cost: number;
  address?: string;
  rating?: number;
  source?: string;
  source_refs?: string[];
  is_verified?: boolean;
  warnings?: string[];
  transport?: Transport;
}

export interface DayPlan {
  day: number;
  date: string;
  weather?: Weather;
  activities: Activity[];
}

export interface Itinerary {
  destination: string;
  days: DayPlan[];
  total_cost: number;
  budget?: number;
  start_date?: string;
  summary?: string;
  generation_source?: GenerationSource;
}
