import type { SSEEventType } from "@/types/message";

export interface ParsedSSEEvent {
  event: SSEEventType;
  data: unknown;
}

const knownEvents: SSEEventType[] = [
  "thinking",
  "tool_call",
  "tool_result",
  "source",
  "content",
  "itinerary",
  "error",
  "done",
];

function parseEventName(value: string): SSEEventType {
  return knownEvents.includes(value as SSEEventType)
    ? (value as SSEEventType)
    : "content";
}

function parseFieldValue(line: string, field: "event" | "data") {
  const prefix = `${field}:`;
  const value = line.slice(prefix.length);
  return value.startsWith(" ") ? value.slice(1) : value;
}

function parseBlock(block: string): ParsedSSEEvent | null {
  if (!block.trim()) {
    return null;
  }

  const lines = block.split(/\r?\n/);
  let event: SSEEventType = "content";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }

    if (line.startsWith("event:")) {
      event = parseEventName(parseFieldValue(line, "event").trim());
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(parseFieldValue(line, "data"));
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  const rawData = dataLines.join("\n");
  let data: unknown = rawData;

  try {
    data = JSON.parse(rawData);
  } catch {
    data = { text: rawData };
  }

  return { event, data };
}

export async function* parseSSEStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<ParsedSSEEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split(/\r?\n\r?\n/);
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const event = parseBlock(block);
        if (event) {
          yield event;
        }
      }
    }

    buffer += decoder.decode();
    const lastEvent = parseBlock(buffer);
    if (lastEvent) {
      yield lastEvent;
    }
  } finally {
    reader.releaseLock();
  }
}

export async function* streamSSE(
  response: Response,
): AsyncGenerator<ParsedSSEEvent> {
  if (!response.body) {
    throw new Error("响应中没有可读取的 SSE 流。");
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType && !contentType.includes("text/event-stream")) {
    throw new Error("后端响应不是 SSE 流，请检查 API 服务配置。");
  }

  yield* parseSSEStream(response.body);
}
