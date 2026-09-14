# Second local width-8 two-hour opportunity from update 423

## Decision and fixed question

On 14 September 2026 Dustin approved one further two-hour continuation and the
targeted saved-only high-COMPASS review following the
[audited A03 outcome](2026-09-14-local-w8-a03-outcome.md). This is a NEW bounded
allocation, not a technical retry against the nearly spent original allowance.
The executable trial is
[`continuation-w8-feasibility-2h-local-a04`](../trials/continuation-w8-feasibility-2h-local-a04.json).

A03 reached 423 cumulative updates at q/N 16.11080233178303. Its late complete
32-update blocks improved q/N by 0.07325484 and 0.07603311, versus only 0.00688354
in its first block. Both convergence windows still failed. Continued progress
supports testing whether the same trajectory remains productive before changing
architecture or optimizer. This allocation cannot establish an architecture winner.

## Exact restart and unchanged implementation

Import `35bc1bfc9c7a1c31189c292bba718495e33c53f60422f3c3d27ad3ee290a1819`
is bound to published run `continuation-w8-feasibility-2h-local-a03-52265fbd3eb9`.
Object SHA256 is
`7b2b2d6a7341bf35a1f8c07844dda5307c47c7c4542b077ec1d054cd15c4df37`.
Preserve theta, predictions, penalized gradient, all 15 curvature pairs, the
21-state convergence window, mu=1e-6 and the saved step scale. Reconcile all
terminal dispatches, including the raw-gradient forward/VJP, without replaying
accepted work or resetting history.

The input bundle, metric, all 2290 rows, width 8/depth 1/1570 parameters, seed,
float64, unit backtracking, Armijo, curvature filtering, positivity floor and
convergence gates are unchanged. The candidate-domain repair and roundoff-aware
restart validator are exactly those qualified by A03 source `0dd9154` and merged
in PR #41. No optimizer/model/evaluator implementation change is part of A04.
Before optimization require exact-parent whole-data replay and two active-mu
directional checks on the already qualified local RTX 4090, within the budget.

## Explicit counts, time and one-GPU safeguards

| Resource | Already charged | Maximum new work | Cumulative ceiling |
|---|---:|---:|---:|
| Accepted updates | 423 | 4096 | 4519 |
| Forwards | 4315 | 16384 | 20699 |
| Full/VJP calls | 485 | 8192 | 8677 |
| Model-window seconds | 13570.07446063764 | 7200 | 20771 |

The cumulative model ceiling rounds prior time plus 7200 upward by less than one
second. The independent segment limit remains exactly 7200 seconds, so the
rounding grants no extra segment work. All ceilings fit `p1-time-window-v1`;
neither historical 192 nor A03's 4273-update ceiling silently truncates this
new opportunity. Count caps are generous safeguards, not expected update counts.

The model window includes setup, replay/probes, diagnostics and a 180-second
terminal-gradient reserve. Optimization normally ends shortly before 117 minutes
if not stopped earlier. Saved-array QA/cleanup have another 600 seconds; the
outer systemd limit is 8100 seconds. All rejected, infeasible and interrupted
calls remain charged. Stop on unchanged convergence, endpoint reserve, explicit
resources/counts, exhausted 32-attempt line search or fatal error. Reviews do not
pause or terminate the run. No automatic restart, successor or optimizer switch.

Use only the single local RTX 4090, UUID
`8a52c480-835f-a522-42bd-cc144e59e44e`, logical CUDA device 0. Check for existing
fit ownership and hold the same nonblocking physical-GPU lock through supervisor
exit. Durable service `tmd-w8-feasibility-2h-a04` uses a finite 16-GiB memory
cgroup, no swap, no automatic restart and an isolated clean pinned checkout.
Worker limits remain 20 GiB owned GPU, 12 GiB RSS, 8 GiB available headroom and
one computational CPU thread. Never alter another site's job, claim or environment.

Before claim: pass full CPU tests, structural/restart validation under default
and NEHALEM BLAS, immutable ancestor hashes and budget reconciliation; require
green CI on this exact source. Claim atomically, verify remote readback, and
launch only the claimed revision through the external supervisor.

## Residual investigation and next review

The [saved-only review](../analysis/w8-a03-saved-review-20260914/review.json)
has already separated complete fixed matched and trainable endpoint contributions
for all 188 high-COMPASS rows using immutable metadata, with zero model calls.
In 160 rows the current trainable amplitude is below 0.01 fixed sigma, while
the subset residual RMS is 7.978963. This is not a sensitivity/feasible-response
bound or an irreducible floor. Apply the same saved-only analysis to A04's
endpoint and inspect per-block q, normalized prediction changes and DY nuisance
strain. Do not cut/downweight observations, inflate errors or change physics.

Keep the existing all-row feasibility, step/gradient/curvature and 32-update
reports. Compare gains per forward/VJP and model time, not step count alone.
For a prospective diagnostic flag, mark two consecutive COMPLETE 32-update
blocks with gain per 100 forwards below 0.01174495625419294 while terminal
gradient maximum remains above 1e-5. That threshold is half the mean rate in
A03's last two complete blocks; it is a review aid, not a statistical test or
new stopping/convergence criterion. A shorter final block is not a full block.

If progress persistently deteriorates or severe direction/domain problems
recur, propose a separately preregistered, equal-budget optimizer comparison
from the same checkpoint. No competing arm is launched during this opportunity.
If high-COMPASS remains almost static, specify targeted derivative/sensitivity
work with explicit call/time bounds before any such model evaluations. Preserve
and publish every outcome, including failures and time-censored evidence.
