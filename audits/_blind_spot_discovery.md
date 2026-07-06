# Blind-Spot Discovery (shared — the two blind-spot passes)

A blind-spot pass is a background agent that hunts **unknown knowns** — facts the
codebase or domain already holds that our plan is blind to. It is NOT a conformance
audit: it does not check the artifact against rules, and it does not gate the lock.
It surfaces **candidates**; the user dispositions each.

**Blast radius (working definition):** what might break, change, or be impacted by
our decisions and plan that we didn't know about. Assessing it IS the pass.

## When the two passes run

| Pass | Rides | Fires when | "Affected element" means | Promotes to |
|---|---|---|---|---|
| Post-grill | Phase 1 `ac_audit` dispatch | ACs drafted, nothing built | domain areas / existing consumers the ACs touch | candidate Feature ACs / Key Findings / Decision Log |
| Post-sequence | Phase 6 `sequence_audit` dispatch | full runtime call-flow drawn | concrete call-flow, entry points, callers, touched state | candidate tasks / deferrals (via Change Propagation Guide) |

Only these two moments — P1 solidifies WHAT we build (concept), P6 solidifies the
IMPL we're about to do. No pass at P2/P4/post-7: blind spots there are conformance
issues the existing audits already catch, at real token cost for marginal yield.

## The charter (injected into every pass)

The blind-spot agent is a SEPARATE agent from the conformance audit, dispatched on
the same gate, injected with the phase context + the full schematic + the
change-set/task and codebase access:

> Given the constraints locked in <P_N>, take each affected element or domain and
> assess the BLAST RADIUS — what might break, change, or be impacted by this plan
> that we didn't know about.
>
> Once the blast radius on code AND domain impact is ascertained, assess whether we
> missed any of:
>   · integration points          · unintended consequences
>   · performance concerns         · points of correctness
>   · potential bugs               · system effects in general
>   · missed consumers
>
> Adapt "affected element" to the phase: at P1, domain areas and existing consumers
> the ACs touch; at P6, concrete call-flow, entry points, callers, and touched state.

## Output contract (evidence-gated — distinct from `_format.md`)

Candidates only, one line each:

```
C<n>: <candidate> | <evidence: file:line / existing pattern / arch-doc / named consumer> | <proposed home: AC | Note | Decision | Task | Defer>
```

- **Evidence rule (hard):** every candidate MUST cite concrete evidence. No
  `file:line`, pattern, arch-doc, or named consumer → do not surface it. This is what
  separates an unknown known (a real, citable fact we missed) from speculation.
- **≤ 8 candidates, ≤ 400 words.** Same caps as `_format.md`.
- **No gating.** The pass never blocks the lock. It returns candidates; the user
  dispositions each into its proposed home or dismisses it.
- **Clean case:** return `✓ No blind spots` and nothing else.

## Disposition (requires sign-off, stateless)

Surface the candidate list above the phase's `Confirm: y/comment` sigil. Each
candidate is signed off — promoted to its home or explicitly dismissed — as part of
that phase sign-off. Nothing is silently dropped; nothing is auto-applied.
Disposition rides the phase's existing sign-off: no separate gate, no CLI state.

**P6 promotions route through the Change Propagation Guide (`SKILL.md`).** A
candidate found after sequence lock (new consumer → new task, or a new AC) is a
post-lock change: walk the propagation table (tasks.md / `_overview.md` / dag.mmd /
sequence.mmd) so the schematic stays in sync. Never bolt a promoted finding onto one
file.

## Relationship to the Phase 8 blast-radius touchpoints

The P6 pass is the PLANNING-time analogue of two existing IMPL-time lenses — they are
complementary altitudes, not duplicates. Do not delete one as redundant:

```
P6 blind-spot pass    → "did the DESIGN account for blast radius?"   before impl → tasks/deferrals
P8 per-task trigger   → "did the CODE we just wrote respect it?"     during impl (phase_8 §Blast-radius trigger)
P8 e2e lens           → same, whole-feature sweep                    after impl (phase_8 §Pass 2 check 6)
```
