# Product Requirements

## Positioning

AI Trip Agent is a conversational travel planning application. It turns free-form travel requests into structured itineraries with itinerary cards, source indicators, quality checks, and map-based route context.

The project focuses on planning support, not booking. It does not handle payments, tickets, hotels, or order management.

## Target Users

| User | Need |
| --- | --- |
| Independent travelers | Generate a practical itinerary without searching many travel sites manually. |
| Users with partial plans | Refine a destination, duration, budget, or style through conversation. |
| Users who care about reliability | See source hints, route context, weather context, and fallback status. |

## Core Jobs

| Priority | Job | Acceptance Signal |
| --- | --- | --- |
| P0 | Understand destination, days, budget, and preferences from natural language. | Missing required fields trigger clarification instead of a low-quality plan. |
| P0 | Generate a day-by-day itinerary. | Response includes activities, time slots, cost estimates, and travel context. |
| P0 | Stream progress to the frontend. | The chat UI receives SSE events for thinking, source, content, itinerary, and completion. |
| P0 | Preserve session context. | Recent sessions can be reloaded, continued, cleared, or deleted. |
| P1 | Use travel tools for grounded context. | POI, route, weather, or RAG-derived context appears in source metadata when available. |
| P1 | Support lightweight plan adjustment. | Follow-up requests can change parts of an itinerary without starting from scratch. |
| P1 | Present the itinerary visually. | The frontend shows itinerary cards, quality hints, and a map tab. |
| P2 | Evaluate answer quality. | Offline RAGAS scripts can be run when live credentials are available. |

## Out Of Scope

- Ticket, hotel, restaurant, or activity booking.
- User accounts and long-term cross-device profile sync.
- Payment, refund, or order workflows.
- Commercial production SLA.

## Public Demo Expectations

- The repository should run locally with placeholder configuration.
- Live LLM and map features require user-provided API keys.
- Demo fallback mode may be used to show the UI when live services are unavailable.
- Public screenshots should not include private keys, private locations, or school defense material.

