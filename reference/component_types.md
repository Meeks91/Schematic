# Component Types

When designing new components in Phase 2 (Topology), classify each class as one of these types. The class suffix MUST come from the CLAUDE.md fixed vocabulary.

## Canonical types

| Type | Role |
|---|---|
| **Service** | Top-level public API of a feature. Orchestrates other components. Entry point for a capability. Always named `<Domain>Service`. |
| **PipelineService** | Networking/orchestration. Coordinates a multi-step flow across services. Entry point for a pipeline (typically batch or data-flow, not bound to a single HTTP request). |
| **RequestPipelineService** | Per-HTTP-request **domain** orchestrator. Sits between a Controller/Router and the Services / Repositories / Validators that fulfill the request. Owns the *domain* request flow — sequencing of lookup → validation → mutation, ETag concurrency, idempotency-key dedupe, locale precedence — but **NOT** HTTP concerns: no header parsing, no status-code mapping, **no authentication** (the controller authenticates and passes a resolved `user_id`). Constructor never depends on `SessionService` for the purpose of authenticating tokens — if it needs session ops (revoke, list, current-session detection), those are the *domain action* itself, not auth. **One per Controller** (or per endpoint group within a controller). Distinct from `PipelineService` (data/batch flows) and from `Service` (capability-level, not request-level). |
| **Controller** | Networking entry point. Receives inbound requests (HTTP, event, message), parses input headers/body, **authenticates** the request via `SessionService` to obtain a `user_id`, delegates to its RequestPipelineService passing already-resolved domain inputs, translates pipeline/service exceptions to wire-format envelopes, sends response. Zero business logic. Constructor depends on exactly one RequestPipelineService + `SessionService` (for auth) + an exception/envelope serializer. |
| **Router** | Networking routing. Maps inbound requests to the correct controller or handler based on path, method, or message type. |
| **Factory** | Produces models, or joins data from multiple sources into a single model. Method verb is `create_<thing>`. |
| **Repository** (`Repo`) | Data source. Fetches from external systems, caches, or stores. Returns domain objects, hides storage. |
| **Validator** | Validates state. Returns the validated state or throws. **Never produces new models** — a Validator is never a Factory. |
| **Resolver** | Resolves inputs together, or resolves ambiguity in data. |
| **Client** | Interacts with external APIs where a full Service would be overkill. |
| **Manager** | Internal to a service. Coordinates between an external client and internal state (e.g. billing provider ↔ user record). E.g. `SubscriptionManager`. |
| **`<Noun><Verb>er`** | Named after the noun it operates on + the verb it performs. E.g. `ReelEnricher`, `EffectsLinker`, `DeviceLabelParser`. |

## Banned suffixes

These suffixes are explicitly **forbidden** per CLAUDE.md:

- `Loader` — use `Resolver` (a class that resolves a name to data) or absorb into a `Service`
- `Reader` — same
- `Writer` — same
- `Helper` — split into the actual verb-er per concern
- `Handler` — pick a real verb (`Processor`? Usually a NounVerber)

## Stacked-suffix anti-pattern

Never stack two suffixes from the vocabulary. Example:

- ❌ `ReelRetrieverClient` — stacks Verb-er + Client.
- ✅ `ReelRetrievalClient` — if it's a Client (external HTTP integration), say so. The verb is encoded in the noun.
- ✅ `ReelRetriever` — if it's the verb-er that fits, drop "Client" and name it after the verb.

## Layering rule — auth lives at the wire boundary

```
Router/Controller (HTTP-aware)
  ├─ parses request body, headers, query params
  ├─ AUTHENTICATES via SessionService.authenticate_session_token(token) → user_id
  ├─ catches typed domain errors → maps to wire envelopes (HTTP status, error codes)
  └─> RequestPipelineService.method(user_id=..., payload=...)   ← already-authed inputs

RequestPipelineService (HTTP-naive, per-request domain orchestration)
  ├─ coordinates domain Services / Repos / Validators
  ├─ owns cross-cutting domain concerns: ETag concurrency, idempotency dedupe, locale precedence
  └─> Service.method(...)

Service (deep domain logic)
```

**Why**: a RequestPipelineService should be replaceable behind a gRPC handler or CLI without changing its interface. Auth, header parsing, and status-code mapping are transport concerns and belong in the Controller/Router. The pipeline is "shape an inbound request into a domain call"; it is not "wrap a domain call with auth."

**Exception**: login. The login flow IS the authentication — it receives an unauthenticated raw credential (Google ID token, password) and produces a session. The Router cannot pre-authenticate a login request. Login methods stay on the pipeline; everything post-login takes `user_id`.

**Signature shape consequences:**
- Pipelines take `user_id`, never `SessionToken` — unless the operation itself is a session op (`logout`, `revoke_session_by_id`) in which case the token is the *resource being acted on*, not the auth credential.
- Pipelines do not depend on `SessionService` to authenticate. They may depend on `SessionService` when the *domain action* is session management (logout, list sessions, revoke).

## Design Smells Requiring Sign-Off

- ⚠️ **Optional types**: Any nullable/optional return type or model field must be explicitly signed off with justification.
- ⚠️ **Exception swallowing**: Any swallowed exception, silent empty-return, or defensive fallback MUST be flagged to the user for explicit sign-off.
- ⚠️ **Pipeline takes `SessionToken` for auth**: indicates a layering violation — auth belongs in the Controller/Router. Flag.
