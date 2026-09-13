# Current study plan — 13 September 2026

This is the public coordination entry point for the fixed-physics architecture
study. It supersedes the short-window scheduling strategy, while retaining all
historical trial specifications and results. The study remains active until
adequate optimization and controlled architecture comparisons support a choice.
Completing a job batch or publishing partial results does not complete the study.

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
   retaining their spent 18/38/28 steps. Report checkpoints at common cumulative
   steps, model calls and elapsed work. A job interrupted by infrastructure is
   resumed with a new claim and remaining allowance, rather than ranked lower.
4. **Calibrate the optimizer before expanding the matrix.** Many calls went to
   infeasible line-search candidates. Preserve this cost, examine accepted step
   sizes and gradient progress, and qualify any step-selection change on equal
   short budgets from identical saved states. Apply a selected policy to all
   comparison arms; preserve original and changed trajectories separately.
   The next exact comparison is the [paired width8 line-search calibration](P1_OPTIMIZER_CALIBRATION.md):
   two policies from the same saved state,12 new accepted steps each, frozen
   progress/call-saving criteria and cumulative bounds that survive job changes.
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
under `spinquest_standard`. Resource selection and changes require the UVA HPC
specialist's review. Afton or another accelerator family is useful only after
an exact full-data PORT check and measured throughput benefit. Never mutate the
checkout mounted by an active job; each executable revision has an isolated
pinned checkout. Credentials remain on the transfer host.

Before new scientific trials: pass restart-equivalence tests, counter/lineage
tests, termination tests, and real allocated-device telemetry qualification;
commit exact cell specifications, parent hashes, total budgets and decision
rules, then create distinct atomic claims. Publish substantive outcomes and
plan decisions promptly. Routine submission lessons stay in local operations
notes. Preserve all published archives and historical results.
