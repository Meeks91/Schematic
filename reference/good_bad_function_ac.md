# Good Function AC Examples

Reference examples for Phase 4 (Contracts). Two patterns shown: one with a swallowed-empty case requiring sign-off, one with a clean exception propagation.

## Example 1: Method with a swallowed empty case (requires sign-off)

```
Function ACs:
  AC-3.1: link_conviction_effects — link effects to brinson container
    Functionality: Given a set of linkable effects containing conviction data,
    returns a LinkedResult where followed/notFollowed brinson containers are
    populated with the conviction-split allocation and selection values.

    Failure modes: If linkables contain no conviction-enabled partitions,
    return empty brinson containers (do not throw).
    Propagation: Caller (CoordinatorPipeline) treats empty containers as
    valid — no further error handling needed upstream.
    ⚠️ USER SIGN-OFF REQUIRED — this is a swallowed empty case.
```

Why this is good:
- `Functionality:` names the inputs, the transformation, and the output type concretely.
- `Failure modes:` names the specific input that triggers the "empty return" behaviour AND the caller's interpretation.
- `Propagation:` makes the contract two-sided — both producer and consumer understand the empty case.
- `⚠️ USER SIGN-OFF REQUIRED` flag is mandatory whenever the contract describes returning an empty / no-op / silent-fallback path. Per `SKILL.md` Rules, the user must explicitly approve.

## Example 2: Method with clean exception propagation

```
  AC-3.2: reject_overlapping_date_ranges — validate timeline
    Functionality: Given timeline entries with overlapping date ranges,
    throws IllegalArgumentException with a message identifying the
    conflicting entries by their start/end dates.

    Failure modes: Exception propagates to CoordinatorPipeline which
    surfaces it as a 400 response. Not caught internally.
```

Why this is good:
- `Functionality:` describes the validator's job in one sentence.
- The exception type, message contents, and propagation path are all stated.
- The contract is honest about not catching the exception internally — no silent fallback hiding bugs.
- No `Performance:` line because there's no performance constraint — omitted, not blank.

## Function AC format checklist

For every public method, the Function AC block has:
- **Functionality:** required, present, non-empty, non-boilerplate.
- **Failure modes:** required unless N/A (then omit, do NOT leave blank).
- **Performance:** present only when constraints exist (omit otherwise).
- ⚠️ sign-off markers wherever the failure path swallows or returns-empty.
