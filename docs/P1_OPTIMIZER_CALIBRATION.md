# Paired P1 line-search calibration — preregistered design

## Question and fixed comparison

Can reusing the previous successful line-search scale reduce rejected model
calls without materially reducing optimization progress? This tests an optimizer
policy, not an architecture winner. It precedes longer width comparisons.

Both arms use the exact width8/depth1 state, 15 retained curvature pairs,
convergence history and fixed mu=1e-6 from the published
`continuation-w8-p1-a02-38d1bf1023dc` result. Restart identity:
`22f93b2263cf2494d1fc5e40a70f15f82ffed173c0f0bec76e86e97735972dff`.
The parent has 18 accepted updates, 201 charged forwards, 21 charged VJPs and
1,187.385 seconds of supervisor model-window elapsed work. Exact unrounded
elapsed time is read from its hashed result, not this rounded description.
Both arms use seed2026091208, all2,290 observations, the same metric/operators,
float64 deterministic RTX A6000 execution, and unchanged replay/positivity gates.

| Arm | Initial alpha on each accepted-update attempt | Remaining line search |
|---|---|---|
| Unit control | 1 | halve at rejection, up to32 candidates |
| Adaptive scale | min(1,2*previous successful alpha) | identical halving/Armijo rule |

The first adaptive alpha uses the imported last successful alpha. L-BFGS
curvature filtering, descent fallback and Armijo coefficient1e-4 are unchanged.
Each arm branches independently from the common parent; neither consumes the
other arm's state or treats its cost as free historical work.

## Bounds and interruption handling

Target12 new accepted updates, giving30 cumulative portable P1 accepted updates.
Each initial segment permits at most512 additional forwards and128 additional
VJPs. Absolute per-branch ceilings are713 forwards,149 VJPs,30 accepted updates
and6,000 model-window seconds including the parent. These are ceilings, not
instructions to spend unused allowance. Preflight and endpoint calls count.

Each GPU allocation requests one A6000,2CPUs,16GiB and75minutes under
`spinquest_standard`. Two distinct claims may run concurrently. The model window
is3,600seconds INCLUDING a180second endpoint reserve; saved-only audit/cleanup
gets600seconds, leaving300seconds before Slurm walltime. Queue wait is separate.
Memory ceilings remain12GiB process RSS,20GiB owned GPU memory and8GiB minimum
allocation memory headroom. The mandatory one-second telemetry watchdog remains.

An interruption creates a new claim/output directory and resumes the atomic
state within the SAME remaining cumulative allowance. No comparison is made
from unequal censored endpoints. Exhaustion without comparable endpoints requires
a public bounded-budget decision for both arms, not unilateral extra allowance.
The unchanged convergence gate may stop work early; if that prevents a common
30-step comparison, report it and explicitly review that case before selection.

## Frozen decision rule

Evaluate both arms at30 cumulative accepted steps, after their saved-array,
positivity, replay and endpoint-gradient checks pass. Prefer adaptive scaling
only if ALL of the following hold:

- Its endpoint q/N is no more than1e-4 above control.
- Its penalized objective is no more than5e-5 above control.
- Its charged new forwards (including replay, rejected and interrupted calls,
  and endpoint VJP) are at least25% fewer than control.

Otherwise retain unit backtracking for the next common width milestone. Report
gradient progress, feasibility rejections, per-update/call/time learning curves,
raw and adjusted residuals, DY nuisance strain and actual hardware alongside
the decision; do not hide an unfavorable diagnostic in an aggregate score.
Walltime is secondary to charged calls for this calibration because the jobs
may share a node or start at different times. This two-arm single-parent test
does not establish general optimizer superiority across seeds or architectures.

The selected policy must be applied consistently to widths8/16/24 for the next
96-step milestone. If the width8 calibration endpoint is reused, carry its
policy-specific history and all costs forward; keep the alternative branch
as diagnostic evidence. Continue only after full CPU tests, real-device UUID/
telemetry qualification, independent restart review and exact committed trial
specifications. No production model or scientific uncertainty claim is selected.
