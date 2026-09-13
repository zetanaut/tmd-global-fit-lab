# Current study plan — 13 September 2026

This is the public coordination entry point for the fixed-physics architecture
study. It supersedes the short-window scheduling strategy, while retaining all
historical trial specifications and results. The study remains active until
adequate optimization and controlled architecture comparisons support a choice.
Completing a job batch or publishing partial results does not complete the study.

## Latest completed decision

The [paired optimizer calibration](../decisions/2026-09-13-p1-calibration-outcome.md)
completed both arms at30 cumulative accepted steps with valid endpoint/raw
gradients and no execution censoring. Unit q/N=16.938637229 versus adaptive
16.949877882. Adaptive saved40.5% charged new forwards but failed the frozen
progress criteria, so **retain unit backtracking** for all next width arms.
Published records, full archives, learning curves, residual/nuisance diagnostics
and the executable decision accompany that outcome. Neither arm converged.

Next: preserve unit width8 at30 steps and widths16/24 at38/28, then complete
the [preregistered common96-step milestone](../decisions/2026-09-13-p1-milestone96-plan.md)
under reviewed longer, resumable allocations.
These are three independent one-GPU jobs, not a distributed single-model fit.
The [B200 width8 numerical result](../decisions/2026-09-13-b200-w8-a01-outcome.md)
matched the references but had partial execution; the
[A02 technical retry](../decisions/2026-09-13-b200-w8-a02-outcome.md) reproduced
that numerical pass and shutdown-monitor failure. B200 promotion and automatic
retries are paused. The exact A6000 width specs are reviewed; claims briefly
awaited a robust allocation-lifecycle monitor review applicable to both GPU types.
That execution gate has now passed: the reviewed fix passed the full CPU suite
and an allocated A6000 natural-exit check that observed the actual transition
with fresh memory accounting. The three A6000 width trials are released for
independent claims and were submitted in parallel at source`21844e1`:
width8job19818033, width16job19818034 and width24job19818035. Their initial
pending state is scheduler queueing, not an experimental result. No historical
B200 partial result is reclassified or promoted by that A6000 proof.

One separately reviewed, bounded [B200 A03 requalification](../decisions/2026-09-13-b200-w8-a03-plan.md)
was also claimed and submitted asjob19819069. It uses the same all-row width8
anchor, zero updates and the durable monitor; it preserves A01/A02 costs and
can only establish clean B200 width8 execution. It temporarily permits one
extra B200 allocation alongside the three A6000 cells, then returns to the
three-GPU project cap at terminal state. A03 cannot promote widths16/24,
migrate active fits or select an architecture. A clean A03 only permits
separately preregistered sequential width16/24 PORT checks; it cannot authorize
any further attempt automatically.

A03 subsequently completed every numerical, audit and execution gate; see its
[outcome](../decisions/2026-09-13-b200-w8-a03-outcome.md) and immutable result.
The temporary fourth-GPU exception has ended. A03 permits a separately
preregistered B200 width16 replay only; width24 remains conditional on that
new cell, and none of this migrates the active A6000 P1 continuations or
constitutes an architecture comparison.

That separately scoped [B200 width16 A01 PORT plan](../decisions/2026-09-13-b200-w16-a01-plan.md)
completed cleanly; its independently reviewed [outcome](../decisions/2026-09-13-b200-w16-a01-outcome.md)
and immutable result preserve the claim, source, archive, numerical and monitor
evidence. It is the first B200 width16 cell, eight forwards/three VJPs/zero
updates, and establishes B200 execution for that fixed replay only. The
temporary fourth-GPU exception ended at terminal state. A separately
preregistered and reviewed B200 width24 PORT plan may now be prepared, but is
not yet claimed or submitted; no B200 optimization or architecture conclusion
is authorized. The three A6000 P1 continuations remain independent.

That final [B200 width24 A01 PORT plan](../decisions/2026-09-13-b200-w24-a01-plan.md)
is now preregistered and awaiting independent review, exact-source CI, a fresh
claim and launch. It fixes the original width24 anchor, preserves completed
B200 execution lineage, and requires a saved raw gradient plus a hash-pinned
saved-only comparison to the retained CPU and A6000 width24 endpoints. It is
not submitted, is the last B200 PORT cell, and cannot support optimizer,
throughput or architecture claims.

## What has actually been tested

Six full-data PORT cells (widths 8, 16 and 24 on CPU and RTX A6000) passed the
fixed numerical checks. The first portable P1 round produced these audited
endpoints, with publicly downloadable evidence in [RESULTS.md](../RESULTS.md):

| Width | Starting q/N | Endpoint q/N | New accepted updates | Limiting event |
|---:|---:|---:|---:|---|
| 8 | 16.955715679 | 16.951369143 | 18 | telemetry freshness stop |
| 16 | 16.661796605 | 16.585009097 | 38 | 1,800-second model limit |
| 24 | 16.807363794 | 16.783958452 | 28 | 1,800-second model limit |

The saved residual/positivity/DY-closure audits pass. Raw endpoint gradients
were not completed. Width 8 did not reach 21 states; the eligible windows of
the other widths did not establish convergence. All three require more work.
The earlier width-8/24 A01 attempts stopped before a model evaluation because
the GPU telemetry selector addressed an unavailable device; A02 corrected
that execution failure. Their claims and evidence are retained.

The prior study-complete disposition was premature. The width-16 endpoint was
already lowest at the start; its lead alone cannot establish an architecture
effect. Equal update counts will improve comparability but cannot replace
paired starting functions, repeat seeds and convergence checks.

## Why the next round will be different

1. **Preserve completed optimization.** Resume from verified saved states.
   Save L-BFGS curvature pairs, the 21-state convergence window, accepted step,
   barriers, and cumulative call/time ledger atomically. The old archives have
   all accepted parameter and penalized-gradient vectors; deterministic
   reconstruction of their actual history must be verified against the pinned
   algorithm before use. No history is inferred from parameters alone.
2. **Size jobs from measured cost.** The 30-minute window proved insufficient.
   Use reviewed longer model windows and separate endpoint-gradient/finalization
   reserve. Every segment is bounded; job boundaries preserve optimization
   state and do not silently give one architecture a new scientific allowance.
3. **Track a common milestone.** First complete the existing P1 trajectories to
   96 cumulative portable accepted steps (or the unchanged convergence gate),
   retaining the selected parents' spent30/38/28 steps after calibration. Report checkpoints at common cumulative
   steps, model calls and elapsed work. A job interrupted by infrastructure is
   resumed with a new claim and remaining allowance, rather than ranked lower.
4. **Calibrate the optimizer before expanding the matrix.** Many calls went to
   infeasible line-search candidates. Preserve this cost, examine accepted step
   sizes and gradient progress, and qualify any step-selection change on equal
   short budgets from identical saved states. Apply a selected policy to all
   comparison arms; preserve original and changed trajectories separately.
   The completed exact comparison is the [paired width8 line-search calibration](P1_OPTIMIZER_CALIBRATION.md):
   two policies from the same saved state,12 new accepted steps each, frozen
   progress/call-saving criteria and cumulative bounds that survive job changes.
   Its outcome retained unit backtracking; do not rerun this completed pair.
5. **Fix monitoring and termination at the source.** Establish GPU identity by
   UUID within the actual allocation, including concurrent nonzero GPU indices.
   Timestamp completed measurements and separate prompt mandatory memory
   checks from optional utilization queries. Diagnose the one-second freshness
   event from evidence; retain memory limits and explicit bounded failure
   behavior. Graceful shutdown must leave the last complete optimizer state,
   counters and endpoint audit usable.

## Preregistered evidence and decision gates

The fixed convergence test is two consecutive ten-update intervals at unchanged
mu=1e-6 (21 states): q/N range <=1e-4, fixed-sigma prediction-span RMS <=1e-3,
maximum <=1e-2, and terminal penalized-gradient maximum <=1e-5. Record raw
gradients as well. Do not relax these criteria after seeing a preferred arm.

At every common milestone, publish the full learning curves, calls, elapsed
work, feasibility rejection rates, residuals, nuisance penalties and convergence
windows. Another bounded round is justified by continuing progress or a tested
optimizer remedy. If progress stalls, diagnose conditioning or feasibility and
test a remedy before allocating a larger topology matrix. A partial outcome
triggers that decision process; it is not a stopping point for the study.

After optimization is reliable, execute the existing controlled sequence:

| Question | Comparison design | Promotion requirement |
|---|---|---|
| Width/capacity | widths 8/16/24, at least three paired seeds; function-preserving embeddings where possible | repeatable gain at comparable maturity; costs and nuisance strain reported |
| Original family versus Nested-FiLM | two families, two matched parameter bands, three paired seeds | exact original source identity resolved and both adapters verified |
| Depth | depths 1/2/3, three paired seeds, approximately matched parameters | baseline optimizer and initialization gates passed |
| Conditioning placement | input/every/last block at depth >=2, three paired seeds | function definitions and parameter inventories frozen; no duplicate depth-1 arms |

Use within-pair differences and across-seed spread, not a single best run, to
support a choice. A practically indistinguishable result favors the smaller or
cheaper tested model. Freeze the practical-effect threshold in the exact matrix
specification before running that comparison. Keep fit-score, residual and
cost tradeoffs explicit; a mathematical global optimum is not implied.

The supplied provenance identifies Nested-FiLM and a historical FiLM source,
but the originally intended comparison family still needs identity resolution.
That dependency does not hold up P1 convergence or initialization work.

## Execution and public coordination

Use independent one-GPU cells, initially up to three qualified A6000 allocations
under `spinquest_standard`. The separately scoped temporary fourth-GPU
exceptions for completed B200 A03 and width16 A01 have both ended; the normal
cap is three. Any future exception, including a separately reviewed width24
PORT cell, requires a fresh UVA HPC specialist review. Afton or another
accelerator family is useful only after an exact full-data PORT check and
measured throughput benefit. Never mutate the
checkout mounted by an active job; each executable revision has an isolated
pinned checkout. Credentials remain on the transfer host.

Before new scientific trials: pass restart-equivalence tests, counter/lineage
tests, termination tests, and real allocated-device telemetry qualification;
commit exact cell specifications, parent hashes, total budgets and decision
rules, then create distinct atomic claims. Publish substantive outcomes and
plan decisions promptly. Routine submission lessons stay in local operations
notes. Preserve all published archives and historical results.
