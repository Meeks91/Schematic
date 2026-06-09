# Audit Precedence — DO NOT FLAG list (shared across all audits)

Every audit prompt MUST read this file first. The findings below have been raised repeatedly across phases and confirmed as **non-issues** by the user. Re-flagging them wastes a review cycle and erodes trust in the audit channel.

## Hard "do NOT flag" list

1. **Missing `*,` in signatures.** The styling standards explicitly ban `*,` because call sites already use kwargs. Schematic signatures show `def f(param: Type, ...) -> R` without the keyword-only marker.

2. **Missing `self` in method signatures.** Schematic signatures show the caller-facing API. Implicit `self` is correct. Do NOT flag.

3. **"Emits audit event then raises" is propagation, not swallowed exception.** A method that records an audit event then re-raises has *not* swallowed the error — the raise propagates to the caller. Only flag if the method catches and returns a normal value, or catches and re-raises a *different* error type without preserving context.

4. **MODIFIED contracts are delta-only.** A `[MODIFIED]` contract intentionally omits pre-existing methods, fields, and dependencies. Do NOT flag absent pre-existing surface area. Only flag if a *new* dependency is named in the constructor without a Function AC describing how it is used.

5. **Agentive nouns as class suffixes are valid.** "Judge", "Analyser", "Generator", "Renderer" are agentive nouns that match the `<Verb>er` rule. Do NOT flag for not literally ending in "-er" if the suffix is an agentive noun that names what the class does. (Cross-check against existing production class names in `src/` — if there's a precedent, it's locked.)

## Soft "verify before flagging" list

6. **Param naming `<vendor>_client` vs `llm_client`.** Sometimes the vendor name carries useful disambiguation (multiple LLM providers in the same constructor). Flag only if (a) there's a single LLM client AND (b) production code already uses the role-name pattern.

7. **Naming inconsistencies between matrix and contract file.** Treat as a real BLOCKER — these are the only real wins audits surface that humans miss.

8. **AC pyramid gaps.** Real BLOCKER — every Feature AC must trace to ≥1 Class AC to ≥1 Function AC to ≥1 AC Test.

**Severity tag definitions, gate questions, and sort order:** see `_format.md`.

## When in doubt — omit

A clean audit on a real issue is more valuable than a noisy audit that buries real issues under trivia. If a finding doesn't clear the Severity gates in `_format.md`, drop it. Audits are graded on signal density, not finding count.
