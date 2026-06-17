import type { Itinerary } from './itinerary';

export type MessageRole = 'user' | 'assistant' | 'system';

export type ReasoningEventType =
  | 'thinking'
  | 'tool_call'
  | 'tool_result'
  | 'source';

export interface ReasoningEvent {
  id: string;
  type: ReasoningEventType;
  title: string;
  detail?: string;
  tool?: string;
  created_at: string;
}

export interface BaseMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface UserMessage extends BaseMessage {
  role: 'user';
}

export interface AssistantMessage extends BaseMessage {
  role: 'assistant';
  is_streaming?: boolean;
  itinerary?: Itinerary;
}

export interface SystemMessage extends BaseMessage {
  role: 'system';
}

export type ChatMessage = UserMessage | AssistantMessage | SystemMessage;

export interface ThinkingEventData {
  step: string;
}

export interface ToolCallEventData {
  tool: string;
  args: Record<string, unknown>;
}

export interface ToolResultEventData {
  tool: string;
  result: unknown;
}

export interface SourceEventData {
  kind: string;
  label: string;
  detail?: string;
  tools?: string[];
  is_fallback?: boolean;
}

export interface ContentEventData {
  text: string;
}

export interface ItineraryEventData {
  itinerary: Itinerary;
}

export interface ErrorEventData {
  message: string;
}

export type DoneEventData = Record<string, never>;

export type SSEEvent =
  | { event: 'thinking'; data: ThinkingEventData }
  | { event: 'tool_call'; data: ToolCallEventData }
  | { event: 'tool_result'; data: ToolResultEventData }
  | { event: 'source'; data: SourceEventData }
  | { event: 'content'; data: ContentEventData }
  | { event: 'itinerary'; data: ItineraryEventData }
  | { event: 'error'; data: ErrorEventData }
  | { event: 'done'; data: DoneEventData };

export type SSEEventType = SSEEvent['event'];
