# Frontend Design

## Goals

The frontend is designed around a single high-value workflow: describe a trip, stream the planning response, inspect the itinerary, and continue refining it.

The UI should feel like an operational planning tool rather than a marketing page. Dense itinerary information, source status, quality hints, and map context are prioritized over decorative content.

## Routes

| Route | Purpose |
| --- | --- |
| `/` | Entry screen with a direct path into trip planning. |
| `/chat` | Main planning workspace with chat, itinerary, and map panels. |
| `/itinerary/[id]` | Shareable or reloadable itinerary detail route placeholder. |

## Main Chat Layout

| Region | Responsibility |
| --- | --- |
| Header | App identity, session controls, and navigation affordances. |
| Chat panel | User messages, streamed assistant output, thinking state, and input controls. |
| Itinerary panel | Trip summary, daily activities, source indicators, quality checks, and export actions. |
| Map panel | AMap canvas, POI markers, route overlays, and selected activity context. |
| History dialog | Recent session reload, new conversation, and deletion flows. |

## Data Flow

1. The user submits a message on `/chat`.
2. The frontend posts to `/api/v1/chat`.
3. The backend streams Server-Sent Events.
4. The frontend renders progressive text and structured itinerary events.
5. Session data is stored locally and synced through `/api/v1/session/{session_id}`.
6. Itinerary state drives both the itinerary card view and map overlays.

## State Boundaries

| State | Storage |
| --- | --- |
| Active chat messages | React/Zustand client state |
| Current itinerary | React/Zustand client state |
| Recent sessions | Local storage plus backend session API |
| Map overlays | AMap SDK objects owned by React components |
| Runtime API base URL | `NEXT_PUBLIC_API_URL` |

## Reliability Notes

- E2E tests mock backend SSE responses so frontend behavior can be verified without live LLM keys.
- Map components guard against invalid coordinates and detach overlays during cleanup.
- The frontend has lint, typecheck, build, and Playwright checks in CI.

