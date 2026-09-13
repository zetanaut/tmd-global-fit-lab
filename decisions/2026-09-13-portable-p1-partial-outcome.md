# Portable P1 partial-outcome assessment

## Evidence assessed

This assessment covers the three independently claimed, fixed-physics portable
P1 continuations on Rivanna RTX A6000.  Each retained archive was separately
downloaded from its immutable GitHub release and hash-checked before its result
record was added.

| Width | Attempt | Accepted updates | Start q/N | Endpoint q/N | Change | Stop | Endpoint audit |
|---:|---|---:|---:|---:|---:|---|---|
| 8 | A02 | 18 | 16.955715679 | 16.951369143 | -0.004346536 | telemetry stale >1 s | passed |
| 16 | A01 | 38 | 16.661796605 | 16.585009097 | -0.076787507 | declared 1,800 s model deadline | passed |
| 24 | A02 | 28 | 16.807363794 | 16.783958452 | -0.023405342 | declared 1,800 s model deadline | passed |

All endpoint audits are finite, have no negative or zero values, and retain
their full signed endpoint/telemetry/checkpoint evidence.  The width-8 A02
stop was the configured fail-safe after a 2.85-second interval without a fresh
telemetry sample; its sampled RSS, allocated-memory headroom, and GPU memory
were within the declared bounds.  Widths 16 and 24 reached their declared
model-work deadlines, likewise without a resource-limit or numerical gate
failure.

## Scientific interpretation

These are bounded **partial** continuations, not convergence results.  No cell
established the required plateau, raw endpoint gradients are correctly absent
where the deadline preceded their evaluation, and no production architecture is
selected.  The endpoint values are not a valid architecture ranking: the cells
began at different sealed P0 endpoints and received unequal numbers of accepted
updates before their independent censoring events.

The evidence does establish that the qualified portable evaluator, fixed input
bundle, and endpoint audit operate through real A6000 P1 work for all three
widths.  It does not establish that any width has converged, nor that a lower
endpoint from this unequal, censored round predicts the final architecture
choice.

## Disposition

All three preregistered P1 allocations are terminal and preserved.  Do not
extend or silently retry them.  Any subsequent equal-opportunity continuation
or monitoring-policy change requires a new preregistered allocation, a fresh
atomic claim, and an explicit scientific decision.
