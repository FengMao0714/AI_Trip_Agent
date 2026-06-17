import type { DayPlan } from "@/types/itinerary";

const WEEKDAYS = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
const CHINESE_WEEKDAY_INDEX: Record<string, number> = {
  日: 0,
  天: 0,
  一: 1,
  二: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
};

function localDate(year: number, monthIndex: number, day: number) {
  return new Date(year, monthIndex, day);
}

function isValidDate(date: Date) {
  return !Number.isNaN(date.getTime());
}

function addDays(date: Date, days: number) {
  return localDate(date.getFullYear(), date.getMonth(), date.getDate() + days);
}

function parseConcreteDate(value: string, baseDate = new Date()) {
  const normalized = value.trim();

  const isoMatch = normalized.match(/(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})/);
  if (isoMatch) {
    const date = localDate(
      Number(isoMatch[1]),
      Number(isoMatch[2]) - 1,
      Number(isoMatch[3]),
    );
    return isValidDate(date) ? date : null;
  }

  const monthDayMatch = normalized.match(/(\d{1,2})\s*月\s*(\d{1,2})\s*(?:日|号)?/);
  if (monthDayMatch) {
    const month = Number(monthDayMatch[1]);
    const day = Number(monthDayMatch[2]);
    const candidate = localDate(baseDate.getFullYear(), month - 1, day);
    return isValidDate(candidate) ? candidate : null;
  }

  return null;
}

function nextMonday(baseDate: Date) {
  const day = baseDate.getDay();
  const daysUntilNextMonday = ((8 - day) % 7) || 7;
  return addDays(baseDate, daysUntilNextMonday);
}

function parseRelativeDate(value: string, baseDate = new Date()) {
  const normalized = value.replace(/\s+/g, "");
  if (!normalized) {
    return null;
  }

  if (normalized.includes("今天")) {
    return localDate(baseDate.getFullYear(), baseDate.getMonth(), baseDate.getDate());
  }

  if (normalized.includes("明天")) {
    return addDays(baseDate, 1);
  }

  if (normalized.includes("后天")) {
    return addDays(baseDate, 2);
  }

  const nextWeekdayMatch = normalized.match(/下(?:周|星期|礼拜)([一二三四五六日天])/);
  if (nextWeekdayMatch) {
    const monday = nextMonday(baseDate);
    const weekday = CHINESE_WEEKDAY_INDEX[nextWeekdayMatch[1]];
    return addDays(monday, weekday === 0 ? 6 : weekday - 1);
  }

  if (normalized.includes("下周")) {
    return nextMonday(baseDate);
  }

  if (normalized.includes("周末") || normalized.includes("星期末")) {
    const daysUntilSaturday = (6 - baseDate.getDay() + 7) % 7 || 7;
    return addDays(baseDate, daysUntilSaturday);
  }

  return null;
}

function resolveDate(value?: string | null) {
  if (!value) {
    return null;
  }

  return parseConcreteDate(value) ?? parseRelativeDate(value);
}

function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dateLooksRelative(value: string) {
  return /^第\s*\d+\s*天$/.test(value.trim()) || /^Day\s*\d+$/i.test(value.trim());
}

export function formatCalendarDate(date: Date) {
  return `${date.getMonth() + 1}月${date.getDate()}日 ${WEEKDAYS[date.getDay()]}`;
}

export function inferTripStartDateFromText(text: string) {
  const normalized = text.replace(/\s+/g, "");
  const patterns = [
    /\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}(?:日|号)?/,
    /\d{1,2}月\d{1,2}(?:日|号)?/,
    /下(?:周|星期|礼拜)[一二三四五六日天]?/,
    /今天|明天|后天|周末|星期末/,
  ];

  for (const pattern of patterns) {
    const match = normalized.match(pattern);
    if (!match) {
      continue;
    }

    const date = resolveDate(match[0]);
    if (date) {
      return toDateInputValue(date);
    }
  }

  return null;
}

export function getDayCalendarDate(day: DayPlan, tripStartDate?: string) {
  const directDate = resolveDate(day.date);
  if (directDate) {
    return directDate;
  }

  const startDate = resolveDate(tripStartDate);
  if (!startDate) {
    return null;
  }

  return addDays(startDate, Math.max(0, day.day - 1));
}

export function getDayCalendarLabel(day: DayPlan, tripStartDate?: string) {
  const date = getDayCalendarDate(day, tripStartDate);
  return date ? formatCalendarDate(date) : null;
}

export function getDayTitle(day: DayPlan) {
  return dateLooksRelative(day.date) ? day.date : `第${day.day}天`;
}
