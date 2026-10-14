# tests/checker-corpus — adversarial programs with pre-registered verdicts

27 pseudo-Hybrid (`.hy`) programs written BEFORE the Phase-1 checker exists,
per the human owner's 2026-10-12 ruling (QUESTIONS.md Q1): the adversarial
programs are written first and treated as the spec. Coverage: the named
tripwire cases (shared map across tasks; worker pool mutating a shared
struct — unguarded, mutex-guarded, managed shapes), the three G0-named
adversarial programs (shared-mutable-map, sender-keeps-using-after-send,
borrow-returned-from-function), rule exercises for A2/A3/A5/A6/A7, and
positive controls guarding against over-strictness (per-task fan-in, clean
`move` sends, atomic/channel/immutable sharing). VERDICTS.md has the table.

Pre-registration discipline: every verdict was hand-derived from the (c)+(b)
sendability ruling and the spike-6 A1–A8 strict readings before any checker
existed. Verdicts change only by logged amendment in VERDICTS.md — never
silently. A checker/corpus disagreement is a bug in one of them: decide
which, record it, never quietly re-run until green.

How the future checker consumes this: each `.hy` header carries one
machine-readable `// EXPECTED-VERDICT:` line (ACCEPT / ACCEPT-MANAGED /
REJECT <rule-id>) plus human-readable reasoning (value layers, check
sites, loan windows). The Phase-1 harness parses the line, runs the
checker, and diffs; for ACCEPT-MANAGED the managed LINT output is part of
the expected result. Contested programs say so in the line's trailing
note, so they can be pinned separately from settled ones.

Both harnesses fail with the file name when a `.hy` file has no valid
EXPECTED-VERDICT line. A REJECT rule must appear on that same line.
Unregistered files are errors, not skipped coverage.

Tripwire rule: more than ~25% of this corpus needing `managed` reopens G0
(QUESTIONS.md Q1 item 5). Baseline at pre-registration: 11.1%
verdict-level / 16.7% as-written — definitions and recompute rules in
VERDICTS.md §Tripwire baseline.
