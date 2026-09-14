# Local width-8 domain-aware backtracking repair

The owner requested investigation and resolution of the
[preserved A01 failure](2026-09-14-local-w8-domain-failure-outcome.md).
The immediate defect is failure routing: an invalid proposed forward candidate
aborts the worker instead of being rejected by bounded backtracking. The
full-size update-253 direction causes representational zero damping, whereas
the accepted state is valid. This plan does not claim to have solved the wider
conditioning problem or established a fit floor.

## Minimal, explicit policy change

`optimizer.candidate_errors = reject-forward-domain-errors-v1` is opt-in and
restricted to registered instrumented time-window trials. Historical specs
retain fatal error handling. The new code commit and this policy identify the
changed runtime; immutable source/metric identities still bind the same frozen
physics and likelihood, not a relabeled implementation.

The model/evaluator report typed numerical-domain exceptions for nonfinite
boundaries/kernels/products/observables and representational zero damping.
Fixed-metric overflow is likewise typed before an invalid cotangent can be
dispatched. The worker catches these ONLY in a proposed candidate's forward
evaluation and fixed-metric scoring. It logs a numerical-domain rejection and
continues the existing alpha-halving sequence. It does not compute a candidate
VJP for a rejected forward. Candidate-domain failures that return from an engine
dispatch are explicitly marked no longer in flight, and all calls/time stay
charged. The existing `infeasible_trials` counter retains its narrower meaning
of completed full-observable positivity failures; numerical-domain failures
contribute to `line_search_rejections` and their own diagnostic verdict count.

No forward vector means row minima/violation fields are unavailable, not zero.
Preflight, directional probes, accepted/endpoint evaluations and VJP failures
remain fatal. Unrelated ValueError, memory/device/runtime errors and deadlines
remain fatal. The 32-attempt exhaustion guard is unchanged.

The finite computation, parameter schema, L-BFGS direction/curvature algorithm,
initial alpha=1, Armijo coefficient, mu=1e-6, all 2290 rows, full-observable
positivity floor, covariance, normalization reference, and convergence gate
are unchanged. There is no clipping, damping floor, history reset, gradient
rescaling, or alternative optimizer arm.

## Exact state and remaining allowance

A02 uses restart `f286d60f6e62ae825ef007b4a6638deed379313da1a80b0ed03a369a9550b978`,
with object SHA256 `fe93b70d67541a02b3236f8cd2bc1b3869d516717a9c76e7627aa20dbcd2e284`.
It preserves accepted update 252, q/N 16.411446133424036, all 15 curvature pairs,
the 21-state window, and cumulative 2349 forwards/283 VJPs. The last failed
forward remains charged. Starting model-window time is 8762.75273999467 seconds.

The new model window is 4993 seconds, rounded down from
7200 - 2206.107684707269. This is the remainder of A01's opportunity, not a fresh
two-hour allocation. Setup, replay, probes and diagnostics count inside it;
180 seconds plus a measured-call buffer are reserved for the final raw gradient.
Saved-only QA has 600 seconds; the outer service limit is 5893 seconds.

Remaining caps are 4021 accepted updates, 15473 forwards and 8114 VJPs. The
cumulative caps remain exactly 4273/17822/8397 and 13757 model seconds. A02
cannot be truncated at 192 updates or receive extra work through a counter reset.
One RTX 4090, one exclusive lock, 16 GiB cgroup, no swap, two-CPU quota, no
automatic restart. No UVA or other architecture job is changed.

## Validation and decision rule

Before claim: pass CPU regressions for actual softplus underflow and product/
metric overflow; candidate rejection and charged calls; unchanged finite
trajectories; fatal preflight/probe/VJP/endpoint/unrelated errors; and bounded
32-attempt exhaustion retaining exact optimizer state. Validate the exact new
specification, input hashes and remaining ledger. A bounded five-alpha CPU
boundary-only probe of the archived direction is engineering evidence, not a
full-observable trial or optimizer update.

After clean committed claim and supervised launch, require the unchanged
full-data parent value/penalized-gradient replay and two directional checks
before optimization. The early success criterion is logged rejection of the
previously fatal full-size candidate followed by at least one accepted update
beyond 252, with full positivity and Armijo unchanged. Smaller-alpha boundary
validity alone is insufficient. This criterion establishes recovery of the
specific failure, not conditioning or convergence. Continue only within the
remaining window, reporting every 32 accepted steps; preserve any new failure
as a distinct outcome rather than escalating limits or silently retrying.
