import chatResponse from "@/mock/chat-response.json";
import type { Itinerary } from "@/types/itinerary";

const DEFAULT_BASE_URL = "http://localhost:8000";
const PUBLIC_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_BASE_URL
).replace(/\/+$/, "");
const SERVER_BASE_URL = (
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  DEFAULT_BASE_URL
).replace(/\/+$/, "");
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";

function apiBaseUrl() {
  return typeof window === "undefined" ? SERVER_BASE_URL : PUBLIC_BASE_URL;
}

interface FetchChatOptions {
  currentItinerary?: Itinerary | null;
  message: string;
  sessionId: string;
}

export interface SessionResponse {
  session_id: string;
  user_profile: Record<string, unknown> | null;
  itinerary: Record<string, unknown> | null;
  message_count: number;
  messages: Array<{
    role: "user" | "assistant";
    content: string;
    created_at?: string | null;
  }>;
  updated_at?: string | null;
}

interface MockChatResponse {
  assistant_message: string;
  tool_calls: Array<{
    tool: string;
    args: Record<string, unknown>;
  }>;
  itinerary: Itinerary;
}

export class ChatApiError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ChatApiError";
  }
}

function getStatusMessage(status: number) {
  if (status === 400 || status === 422) {
    return "请求内容不完整，请补充目的地、天数、预算或偏好后再试。";
  }

  if (status === 429) {
    return "请求太频繁了，请稍等一下再试。";
  }

  if (status === 503) {
    return "AI 服务暂时不可用，请稍后重试。";
  }

  if (status >= 500) {
    return "后端服务暂时不可用，请稍后重试。";
  }

  return "服务暂时无法处理请求，请稍后重试。";
}

function formatSSE(event: string, data: unknown) {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function chunkText(text: string) {
  const sentences = text.split(/(?<=[。！？\n])/u).filter(Boolean);
  return sentences.length > 0 ? sentences : [text];
}

function createMockResponse(message: string) {
  const encoder = new TextEncoder();
  const mock = chatResponse as MockChatResponse;
  const events = [
    formatSSE("thinking", { step: "正在分析您的需求..." }),
    formatSSE("tool_call", mock.tool_calls[0]),
    formatSSE("tool_result", {
      tool: "poi_search",
      result: { count: 8, top_results: ["故宫博物院", "天坛公园", "颐和园"] },
    }),
    formatSSE("thinking", { step: "正在计算路线并结合天气..." }),
    ...chunkText(
      `收到，${message}\n\n${mock.assistant_message}\n\n## 行程亮点\n- 故宫、天坛、国博串联北京中轴线\n- 八达岭长城与颐和园放在第三天，节奏更清晰\n- 预算保留机动空间，方便临时调整`,
    ).map((text) => formatSSE("content", { text })),
    formatSSE("itinerary", { itinerary: mock.itinerary }),
    formatSSE("done", {}),
  ];

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(event));
        await new Promise((resolve) => setTimeout(resolve, 140));
      }

      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
    },
  });
}

export async function fetchChat({
  currentItinerary,
  message,
  sessionId,
}: FetchChatOptions): Promise<Response> {
  if (USE_MOCK) {
    return createMockResponse(message);
  }

  try {
    const response = await fetch(`${apiBaseUrl()}/api/v1/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({
        current_itinerary: currentItinerary ?? undefined,
        message,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      throw new ChatApiError(getStatusMessage(response.status), response.status);
    }

    return response;
  } catch (error) {
    if (error instanceof ChatApiError) {
      throw error;
    }

    throw new ChatApiError("网络连接失败，请检查后端服务是否已启动。");
  }
}

export async function fetchSession(sessionId: string): Promise<SessionResponse> {
  const response = await fetch(
    `${apiBaseUrl()}/api/v1/session/${encodeURIComponent(sessionId)}`,
    {
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new ChatApiError(getStatusMessage(response.status), response.status);
  }

  return (await response.json()) as SessionResponse;
}

export async function clearSession(sessionId: string): Promise<void> {
  if (USE_MOCK) {
    return;
  }

  const response = await fetch(
    `${apiBaseUrl()}/api/v1/session/${encodeURIComponent(sessionId)}`,
    {
      method: "DELETE",
    },
  );

  if (!response.ok && response.status !== 404) {
    throw new ChatApiError(getStatusMessage(response.status), response.status);
  }
}
