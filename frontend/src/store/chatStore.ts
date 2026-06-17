import { create } from "zustand";
import {
  createJSONStorage,
  persist,
  type StateStorage,
} from "zustand/middleware";

import { inferTripStartDateFromText } from "@/lib/dateDisplay";
import type { Itinerary } from "@/types/itinerary";
import type {
  AssistantMessage,
  ChatMessage,
  MessageRole,
  ReasoningEvent,
} from "@/types/message";

const MAX_RECENT_SESSIONS = 8;

export interface ChatSessionSnapshot {
  id: string;
  title: string;
  updatedAt: string;
  messages: ChatMessage[];
  itinerary: Itinerary | null;
  messageCount: number;
}

interface ChatState {
  messages: ChatMessage[];
  itinerary: Itinerary | null;
  isLoading: boolean;
  error: string | null;
  sessionId: string;
  sessions: ChatSessionSnapshot[];
  thinkingStep: string | null;
  reasoningEvents: ReasoningEvent[];
  isReasoningCollapsed: boolean;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  startAssistantMessage: (id: string) => void;
  appendAssistantContent: (id: string, text: string) => void;
  setAssistantStreaming: (id: string, isStreaming: boolean) => void;
  addReasoningEvent: (event: ReasoningEvent) => void;
  clearReasoningEvents: () => void;
  setReasoningCollapsed: (isCollapsed: boolean) => void;
  setItinerary: (itinerary: Itinerary | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  setThinkingStep: (step: string | null) => void;
  reset: () => void;
  switchSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
}

type PersistedChatState = Pick<
  ChatState,
  "itinerary" | "messages" | "sessionId" | "sessions"
>;

const noopStorage: StateStorage = {
  getItem: () => null,
  removeItem: () => undefined,
  setItem: () => undefined,
};

function createSessionId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function createWelcomeMessage(): AssistantMessage {
  return {
    id: "assistant-welcome",
    role: "assistant",
    created_at: new Date().toISOString(),
    content:
      "你好，我是你的旅行规划 Agent。告诉我**目的地、天数、预算和偏好**，我会帮你生成可执行的行程，并在右侧同步展示行程摘要和地图视图。",
  };
}

function getBrowserStorage() {
  return typeof window === "undefined" ? noopStorage : window.localStorage;
}

function isMessageRole(value: unknown): value is MessageRole {
  return value === "user" || value === "assistant" || value === "system";
}

function isStoredMessage(value: unknown): value is ChatMessage {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    isMessageRole(record.role) &&
    typeof record.content === "string" &&
    typeof record.created_at === "string"
  );
}

function normalizeStoredMessages(messages: ChatMessage[]) {
  return messages.map((message) => {
    if (message.role !== "assistant") {
      return message;
    }

    return {
      ...message,
      is_streaming: false,
    };
  });
}

function readStoredMessages(value: unknown): ChatMessage[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return normalizeStoredMessages(value.filter(isStoredMessage));
}

function truncateTitle(value: string) {
  const normalized = value.replace(/\s+/g, " ").trim();
  return normalized.length > 28 ? `${normalized.slice(0, 28)}...` : normalized;
}

function hasSessionContent(messages: ChatMessage[], itinerary: Itinerary | null) {
  return (
    itinerary !== null ||
    messages.some(
      (message) => message.role === "user" && message.content.trim().length > 0,
    )
  );
}

function createSessionTitle(
  messages: ChatMessage[],
  itinerary: Itinerary | null,
) {
  const destination = itinerary?.destination?.trim();
  if (destination) {
    return `${destination}行程`;
  }

  const firstUserMessage = messages.find(
    (message) => message.role === "user" && message.content.trim().length > 0,
  );
  if (firstUserMessage) {
    return truncateTitle(firstUserMessage.content);
  }

  return "新会话";
}

function inferTripStartDateFromMessages(messages: ChatMessage[]) {
  for (const message of [...messages].reverse()) {
    if (message.role !== "user") {
      continue;
    }

    const startDate = inferTripStartDateFromText(message.content);
    if (startDate) {
      return startDate;
    }
  }

  return null;
}

function enrichItineraryWithMessages(
  itinerary: Itinerary | null,
  messages: ChatMessage[],
) {
  if (!itinerary || itinerary.start_date) {
    return itinerary;
  }

  const startDate = inferTripStartDateFromMessages(messages);
  return startDate ? { ...itinerary, start_date: startDate } : itinerary;
}

function countUserMessages(messages: ChatMessage[]) {
  return messages.filter((message) => message.role === "user").length;
}

function createSessionSnapshot(
  sessionId: string,
  messages: ChatMessage[],
  itinerary: Itinerary | null,
  updatedAt = new Date().toISOString(),
): ChatSessionSnapshot | null {
  const enrichedItinerary = enrichItineraryWithMessages(itinerary, messages);

  if (!hasSessionContent(messages, enrichedItinerary)) {
    return null;
  }

  return {
    id: sessionId,
    title: createSessionTitle(messages, enrichedItinerary),
    updatedAt,
    messages: normalizeStoredMessages(messages),
    itinerary: enrichedItinerary,
    messageCount: countUserMessages(messages),
  };
}

function upsertSessionSnapshot(
  sessions: ChatSessionSnapshot[],
  sessionId: string,
  messages: ChatMessage[],
  itinerary: Itinerary | null,
) {
  const snapshot = createSessionSnapshot(sessionId, messages, itinerary);
  const otherSessions = sessions.filter((session) => session.id !== sessionId);

  if (!snapshot) {
    return otherSessions;
  }

  return [snapshot, ...otherSessions].slice(0, MAX_RECENT_SESSIONS);
}

function normalizeStoredSession(value: unknown): ChatSessionSnapshot | null {
  if (typeof value !== "object" || value === null) {
    return null;
  }

  const record = value as Record<string, unknown>;
  if (typeof record.id !== "string" || typeof record.updatedAt !== "string") {
    return null;
  }

  const messages = readStoredMessages(record.messages);
  const itinerary =
    typeof record.itinerary === "object" && record.itinerary !== null
      ? (record.itinerary as Itinerary)
      : null;
  const enrichedItinerary = enrichItineraryWithMessages(itinerary, messages);
  const snapshot = createSessionSnapshot(
    record.id,
    messages,
    enrichedItinerary,
    record.updatedAt,
  );

  if (!snapshot) {
    return null;
  }

  return {
    ...snapshot,
    title:
      typeof record.title === "string" && record.title.trim().length > 0
        ? truncateTitle(record.title)
        : snapshot.title,
    messageCount:
      typeof record.messageCount === "number"
        ? record.messageCount
        : snapshot.messageCount,
  };
}

function normalizeStoredSessions(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map(normalizeStoredSession)
    .filter((session): session is ChatSessionSnapshot => session !== null)
    .sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    )
    .slice(0, MAX_RECENT_SESSIONS);
}

const initialState = () => ({
  messages: [createWelcomeMessage()] as ChatMessage[],
  itinerary: null,
  isLoading: false,
  error: null,
  sessionId: createSessionId(),
  sessions: [] as ChatSessionSnapshot[],
  thinkingStep: null,
  reasoningEvents: [],
  isReasoningCollapsed: false,
});

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      ...initialState(),

      addMessage: (message) =>
        set((state) => {
          const messages = [...state.messages, message];
          return {
            messages,
            sessions: upsertSessionSnapshot(
              state.sessions,
              state.sessionId,
              messages,
              state.itinerary,
            ),
          };
        }),

      updateMessage: (id, patch) =>
        set((state) => {
          const messages = state.messages.map((message) =>
            message.id === id
              ? ({ ...message, ...patch } as ChatMessage)
              : message,
          );
          return {
            messages,
            sessions: upsertSessionSnapshot(
              state.sessions,
              state.sessionId,
              messages,
              state.itinerary,
            ),
          };
        }),

      startAssistantMessage: (id) =>
        set((state) => {
          const messages: ChatMessage[] = [
            ...state.messages,
            {
              id,
              role: "assistant",
              content: "",
              created_at: new Date().toISOString(),
              is_streaming: true,
            },
          ];
          return {
            messages,
            sessions: upsertSessionSnapshot(
              state.sessions,
              state.sessionId,
              messages,
              state.itinerary,
            ),
          };
        }),

      appendAssistantContent: (id, text) =>
        set((state) => {
          const messages = state.messages.map((message) => {
            if (message.id !== id || message.role !== "assistant") {
              return message;
            }

            return {
              ...message,
              content: `${message.content}${text}`,
              is_streaming: true,
            };
          });
          return {
            messages,
            sessions: upsertSessionSnapshot(
              state.sessions,
              state.sessionId,
              messages,
              state.itinerary,
            ),
          };
        }),

      setAssistantStreaming: (id, isStreaming) =>
        set((state) => {
          const messages = state.messages.map((message) =>
            message.id === id && message.role === "assistant"
              ? { ...message, is_streaming: isStreaming }
              : message,
          );
          return {
            messages,
            sessions: upsertSessionSnapshot(
              state.sessions,
              state.sessionId,
              messages,
              state.itinerary,
            ),
          };
        }),

      addReasoningEvent: (event) =>
        set((state) => ({
          reasoningEvents: [...state.reasoningEvents, event],
        })),

      clearReasoningEvents: () =>
        set({
          reasoningEvents: [],
          isReasoningCollapsed: false,
          thinkingStep: null,
        }),

      setReasoningCollapsed: (isReasoningCollapsed) =>
        set({ isReasoningCollapsed }),

      setItinerary: (itinerary) =>
        set((state) => ({
          itinerary,
          sessions: upsertSessionSnapshot(
            state.sessions,
            state.sessionId,
            state.messages,
            itinerary,
          ),
        })),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      setThinkingStep: (thinkingStep) => set({ thinkingStep }),

      reset: () =>
        set((state) => ({
          ...initialState(),
          sessions: upsertSessionSnapshot(
            state.sessions,
            state.sessionId,
            state.messages,
            state.itinerary,
          ),
        })),

      switchSession: (targetSessionId) =>
        set((state) => {
          const sessions = upsertSessionSnapshot(
            state.sessions,
            state.sessionId,
            state.messages,
            state.itinerary,
          );
          const targetSession = sessions.find(
            (session) => session.id === targetSessionId,
          );

          if (!targetSession) {
            return { sessions };
          }

          return {
            ...initialState(),
            messages: normalizeStoredMessages(targetSession.messages),
            itinerary: targetSession.itinerary,
            sessionId: targetSession.id,
            sessions,
          };
        }),

      deleteSession: (targetSessionId) =>
        set((state) => {
          const sessions = state.sessions.filter(
            (session) => session.id !== targetSessionId,
          );

          if (targetSessionId !== state.sessionId) {
            return { sessions };
          }

          return {
            ...initialState(),
            sessions,
          };
        }),
    }),
    {
      merge: (persistedState, currentState) => {
        const storedState = persistedState as Partial<PersistedChatState> | null;

        if (!storedState) {
          return currentState;
        }

        const messages =
          Array.isArray(storedState.messages) && storedState.messages.length > 0
            ? readStoredMessages(storedState.messages)
            : currentState.messages;
        const itinerary =
          "itinerary" in storedState
            ? (storedState.itinerary ?? null)
            : currentState.itinerary;
        const enrichedItinerary = enrichItineraryWithMessages(itinerary, messages);
        const sessionId =
          typeof storedState.sessionId === "string" &&
          storedState.sessionId.length > 0
            ? storedState.sessionId
            : currentState.sessionId;
        const sessions = upsertSessionSnapshot(
          normalizeStoredSessions(storedState.sessions),
          sessionId,
          messages,
          enrichedItinerary,
        );

        return {
          ...currentState,
          itinerary: enrichedItinerary,
          messages,
          sessionId,
          sessions,
        };
      },
      name: "trip-planner-chat",
      partialize: (state) => ({
        itinerary: state.itinerary,
        messages: normalizeStoredMessages(state.messages),
        sessionId: state.sessionId,
        sessions: upsertSessionSnapshot(
          state.sessions,
          state.sessionId,
          state.messages,
          state.itinerary,
        ),
      }),
      skipHydration: true,
      storage: createJSONStorage(getBrowserStorage),
    },
  ),
);
