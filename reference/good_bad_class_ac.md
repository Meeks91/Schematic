# Good vs Bad Class AC — `UserRepository`

Reference example for Phase 2 (Topology). Used to teach the difference between a leaky/sloppy class AC and a tight, ownership-only one.

## ❌ BAD

Violates layout (no fence), bare ref list, prose bullets, conjunctions, Phase 4 leakage, no `Never:`:

````
### 2.3 UserRepository

Type: Repository

Necessitated by: 1.A, 1.E, 2.D, 3.A, 4.E

Responsibility (Class AC):
  - Owns user persistence including methods like find_by_id, find_by_google_sub,
    create, update_preferences, and tombstone, exposed so AuthController AND
    OnboardingController AND SettingsController can read AND write rows.
  - Returns User dataclass; raises UserNotFoundError on miss.
````

Issues:
- No code fence around Type/Necessitated by/Responsibility — violates layout rule.
- `Necessitated by: 1.A, 1.E, …` is a bare ref list — must be one bullet per ref with terse dependency name.
- "including methods like find_by_id, …, create, …" leaks Phase 4 method names.
- "raises UserNotFoundError" leaks Phase 4 exception class name.
- "AuthController AND OnboardingController AND SettingsController" — conjunctions joining unrelated concerns.
- No `Never:` bullet pinning scope.

## ✅ GOOD

Single fence, terse dependency-named bullets, ownership-only Responsibility, `Never:` pinning scope, zero Phase 4 leakage:

````
### 2.3 `UserRepository` (NEW)
```
Type: Repository
Necessitated by:
  - 1.A — login requires user persistence
  - 1.E — enforces email/name immutability at storage boundary
  - 2.D — onboarding persists language/timezone/currency on user
  - 3.A — settings response needs user-row preferences
  - 4.E — deletion needs user-row tombstoning
Responsibility (Class AC):
  - User persistence and retrieval
  - Identity-field immutability enforcement (email, name)
  - User-preference storage (language, timezone, currency, region, category)
  - Lifecycle flag storage (onboarded, tier, trial, subscription validity, tombstone)
  - Never: owns sessions, settings rows, or subscription billing state
```
````

Why it works:
- Single code fence contains all three sub-blocks.
- Each `Necessitated by:` bullet names *why the feature needs this class* in 5-10 words.
- Each Responsibility bullet names a domain/concern, not an interface.
- The `Never:` bullet pins what `UserRepository` does NOT own — pre-empts scope creep into sessions or settings.
- Zero method names, zero return types, zero exception class names.
