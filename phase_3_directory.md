# Phase 3: Directory Structure

> **CLI gate commands** (no audit hook on Phase 3):
> - `schematic phase sign-off --schematic <name> 3` — on user `y`.
> - `schematic phase complete --schematic <name> 3` — immediately after sign-off.

Open your gate message with the Frame Header (SKILL.md → Structural Rules → Frame Header).

After topology is signed off, define the file placement for every new class and model. This gives the user a visual map of the feature's footprint before diving into contract detail. Write to `<schematic_dir>/objective.md` §3.

> **Gate enforcement:** `schematic phase complete` will reject if `objective.md` does not contain `## Directory Structure`. Write to disk before locking.

For each new file:
- Full path from project root
- What it contains (class name or model names)
- Annotation: `(NEW | MODIFIED | DELETED)`
- **Driving AC ref** — every NEW/MODIFIED file carries the Feature AC that necessitated it (e.g. `← <driving AC>`), so the tree keeps the *why* present, not just the *where*.

Group by feature area / package. Follow existing project conventions. Test directory mirrors implementation directory exactly.

## Reference: Directory Structure Example

```
src/services/attribution/linking/
├── EffectsLinker.py                    (NEW)       ← <driving AC>
├── ConvictionPartitionResolver.py      (NEW)       ← <driving AC>
├── AllocationSplitCalculator.py        (NEW)       ← <driving AC>
└── models.py                           (NEW)       ← <driving AC>

tests/services/attribution/linking/
├── test_effects_linker.py              (NEW)
├── test_conviction_partition_resolver.py (NEW)
└── test_allocation_split_calculator.py  (NEW)
```

Phase 3 has no audit hook — drift is caught by topology / contract audits.

**Confirm: y/comment**

---

**Next:** `phase_4_contracts_and_tests.md`
