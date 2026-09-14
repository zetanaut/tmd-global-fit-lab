# One-GPU width-8 feasibility diagnostics and two-hour continuation

## Authorization and question

On 14 September 2026, Dustin requested implementation of the recommended
instrumentation and longer continuation on this machine's one GPU. This records
that new bounded allocation after the completed, unconverged P1B opportunity.
The exact trial is
[`continuation-w8-feasibility-2h-local-a01`](../trials/continuation-w8-feasibility-2h-local-a01.json).

The parent is the published 177-update P1B endpoint at q/N = 16.448895619388466.
Its last 96 updates improved q/N by 0.250810251495615 but incurred 579 infeasible
candidates among 585 rejections. Continued progress justifies a longer baseline
opportunity while logging the rows that actually invalidate trial steps.

## Identity and preserved computation

The new restart import `97d880cdeedcb180e4015fffb8f3827355cf300f10e50bbc6adf18e6e03f4245`
preserves the parent's theta, predictions, penalized gradient, 15 L-BFGS
curvature pairs, 21-state convergence window, mu and accepted step scale.
Its counter reconciliation retains the final endpoint VJP, for 177 accepted
updates, 1,438 forwards, 205 VJPs and 6,556.645055287401 prior model seconds.
The source archive and all run files were verified against the immutable result.

Unit backtracking, Armijo acceptance, curvature filtering, all 2,290 rows,
float64, physics, fixed covariance and full-observable positivity stay fixed.
The evaluator/model arithmetic is unchanged. Full-data parent replay and two
active-mu directional checks precede optimization on the previously qualified
RTX 4090. Passive-instrumentation tests must reproduce the same accepted
trajectory, restart arrays and call counters as the existing worker.

## Single-GPU budget and stopping

Use one RTX 4090, CUDA logical device 0, physical UUID
`8a52c480-835f-a522-42bd-cc144e59e44e`. Check for an existing fit process before
launch and hold the trial's physical-GPU file lock until its supervisor exits.
Run as a durable user service with a finite 16 GiB memory cgroup, no restart,
and an 8,100-second outer runtime limit. Worker limits remain 20 GiB owned GPU
memory, 12 GiB RSS and at least 8 GiB cgroup memory headroom.

The model window is at most 7,200 seconds INCLUDING setup, replay, diagnostics
and a 180-second endpoint-gradient reserve. Thus optimization normally ends
shortly before 117 minutes if it does not converge sooner. Saved-only audit and
cleanup have a further 600 seconds. Maximum new work is 4,096 accepted updates,
16,384 charged forwards and 8,192 VJPs; these generous guardrails are intended
to let the time/convergence condition govern rather than an early 96-step cap.
All calls, including infeasible/rejected and interrupted dispatches, are charged.

Cumulative ceilings are 4,273 accepted updates, 17,822 forwards, 8,397 VJPs and
13,757 model seconds. The latter rounds prior elapsed time plus 7,200 seconds
upward by less than one second; the independent segment ceiling remains exactly
7,200 seconds. The separate `p1-time-window-v1` contract leaves historical V1/V2
limits intact. A time/reserve stop remains partial, unconverged evidence unless
the unchanged convergence gate actually passes.

Stop early on the unchanged convergence test or an existing resource, numerical,
non-descent or exhausted-line-search failure. Save each accepted state atomically.
There is no automatic retry, successor, optimizer switch or subjective new
stagnation threshold. The 32-update reports do not pause or terminate execution.

## Diagnostics using already computed values

- `diagnostic-rows.json`: exact zero-based row IDs, fixed sigma and positivity floor.
- `line-search.ndjson`: every candidate's alpha, feasibility/Armijo verdict,
  minimum prediction and margin, every violating row index with its T/sigma and
  margin, and charged forward/VJP counters. An Armijo pass is a candidate test;
  the accepted checkpoint establishes whether the update was committed.
- `optimization-steps.ndjson`: proposed direction norm, directional derivative,
  descent angle, any steepest-descent fallback, retained curvature pairs and
  L-BFGS initial inverse-Hessian scale.
- `optimization-accepted.ndjson`: actual parameter-step size, achieved/predicted
  improvement, parameter-block penalized-gradient norms, curvature update and
  the unchanged plateau checks.
- `diagnostic-review-0032.json`, `...0064.json`, etc.: 32-update progress versus
  calls/time, failing-row frequencies, full saved residual/nuisance diagnostics
  including high-COMPASS, and convergence evidence. `diagnostic-summary.json`
  records the terminal state and final charged calls.

Instrumentation dispatches no additional model evaluations. Its CPU/file work
is included in elapsed time. Raw gradients are retained at preflight and at
the terminal endpoint within the reserve; intermediate block norms are explicitly
penalized gradients. Failure to finish the final diagnostic summary is retained
separately while preserving the worker and restart receipts.

## Review after the outcome

Publish the complete archive and immutable result with saved-array checks and
separate download verification. Evaluate progress per forward/VJP and elapsed
work, whether a small persistent set of constraints blocks trial steps, and
whether those events correlate with step sizes and gradient/curvature behavior.
These observations guide a later, separately controlled optimizer comparison.
They do not by themselves prove poor conditioning or establish an architecture
winner. No second GPU or alternative optimizer arm is part of this allocation.
