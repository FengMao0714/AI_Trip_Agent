# API Reference

Base URL: `http://localhost:8000`

## Health

```http
GET /api/v1/health
```

Returns overall service state and the backend view of database, Redis, and LLM configuration.

```json
{
  "status": "ok",
  "services": {
    "database": "connected",
    "redis": "connected",
    "llm": "configured"
  }
}
```

## Chat Planning Stream

```http
POST /api/v1/chat
Accept: text/event-stream
Content-Type: application/json
```

Request body:

```json
{
  "message": "Plan a 3 day Beijing trip with a 3000 RMB budget",
  "session_id": "demo-session",
  "current_itinerary": null
}
```

SSE event types:

| Event | Purpose |
| --- | --- |
| `thinking` | Current planning step. |
| `tool_call` | Tool invocation metadata. |
| `tool_result` | Tool result summary. |
| `source` | Generation source metadata. |
| `content` | Assistant answer text chunk. |
| `itinerary` | Structured itinerary payload. |
| `error` | Recoverable user-facing error. |
| `done` | End of stream. |

## Session

```http
GET /api/v1/session/{session_id}
```

Returns saved session context, recent messages, and the latest itinerary when present.

```http
DELETE /api/v1/session/{session_id}
```

Clears saved Redis session context for the given session ID.
