# P1 common96-update milestone: exact bounded successors

The completed [paired calibration](2026-09-13-p1-calibration-outcome.md)
retains unit backtracking under its frozen rule. Apply it to all three existing
width trajectories, with exact state/history/call/time inheritance. This round
is optimization-maturity work on the existing starts, not a paired-seed
architecture comparison and not an authorization to select a production model.

| Trial | Width | Inherited updates | Requested new updates | Inherited forwards / VJPs |
|---|---:|---:|---:|---:|
| continuation-w8-p1-m96-a01 | 8 | 30 | 66 | 322 / 40 |
| continuation-w16-p1-m96-a01 | 16 | 38 | 58 | 233 / 50 |
| continuation-w24-p1-m96-a01 | 24 | 28 | 68 | 199 / 33 |

Width8 imports the completed unit branch's native optimizer state, all15
curvature pairs and21-state window. Its final raw-gradient call is charged:
the parent ledger is322/40, not the pre-endpoint atomic snapshot321/39.
The exact new restart manifest is
`b8334fe75060f5d5f634352a0fd26939a33f750be69456fd49b7c934db0a938b`.
Widths16/24 use the already independently verified legacy reconstructions
`784cdadf69891e6d86bb3b59b1c04f4ca4ac05b1c086f640ea481464f4096f3d`
and `816df711a366dba3a344a173779f874971cc95244a521882710499b1a90cfd64`.
Each spec binds the parent run, state SHA and remaining accepted count.
No curvature reset, barrier reset or discarded convergence history is allowed.

## Shared allowance and interruption policy

Each width has the same cumulative ceilings:96 portable P1 accepted updates,
4096 charged forwards,512 VJPs and21600 model-window seconds, INCLUDING all
ancestors on that trajectory. The runtime recursively verifies inherited elapsed
time from published parent records. Local call limits equal those ceilings minus
the inherited ledger; a new segment cannot regenerate allowance. Calibration's
diagnostic adaptive branch is separately retained and is not part of the unit
trajectory. Historical P0 and PORT costs stay separately reported, not relabeled
as portable P1 calls.

This is a new explicitly bounded optimization round after the30-step calibration,
not a retroactive enlargement of that comparison. Ceilings are not instructions
to consume all available calls. An unchanged convergence pass may end a width
early; report its maturity and do not force unnecessary optimization solely to
match a step count. An infrastructure interruption resumes the exact last
accepted state under a new attempt/claim within the SAME remaining allowance.
If any width is censored below the common milestone, publish its partial result
and restore its remaining allowance before making milestone comparisons. A
binding common ceiling triggers a new explicit evidence-based budget decision,
not unilateral extra work for a favored width.

Each first segment has13200 model seconds including a180-second endpoint
reserve, then600 seconds for saved-only audit/cleanup. Reviewed Slurm request:
one A6000, two CPUs,16GiB, one node/task, four hours, account
`spinquest_standard`, public partition `gpu`, `gpu:a6000:1`. Ten minutes remain
outside the13800-second application/audit bound. Memory ceilings remain12GiB
worker RSS,20GiB owned GPU and8GiB host allocation headroom. Mandatory telemetry
remains bounded by the one-second freshness requirement. Use up to three
independent jobs/GPUs, preserving the total study GPU cap of three.

At the observed pair cost,66 updates cost roughly several thousand model
seconds; the13200-second segment is deliberately longer than that estimate to
absorb line-search variation and width-dependent cost. It is not a guaranteed
runtime or evidence of a plateau. Save every accepted state and costs so that
slower arms remain recoverable. Queue estimates do not establish throughput.

## Qualification and decision output

All three retain the qualified A6000 backend, exact float64/no-TF32/determinism,
fixed physics/operators/metric and all2,290 rows. Full CPU tests and bundle
hash verification precede each model launch. Each saved parent must pass the
unchanged full-data prediction/q/gradient/directional replay before resumption.
Keep the reviewed terminal-monitor fix; do not loosen numerical or live-memory
gates. B200 qualification is separate and cannot migrate these cells mid-run.

Before claim, require independent review of the native width8 state/terminal
ledger and all three exact specs, passing CPU CI, clean immutable source and
the UVA specialist's resource review. Each distinct claim is read back before
its single submission. Archive terminal accounting separately from optional
expired scheduler detail queries. Preserve all outcomes and publish substantive
results promptly.

At the common milestone publish full accepted q/objective/gradient curves versus
updates, charged calls and elapsed work; raw/adjusted process residuals; all DY
nuisances and separate penalties; feasibility rejection rates; positivity; and
both21-state convergence windows. Fixed mu=1e-6 convergence requires q/N
range<=1e-4, prediction-span RMS<=1e-3 and max<=1e-2 in fixed sigma, plus
penalized-gradient max<=1e-5, in two consecutive ten-update intervals.
Raw gradients must also be reported. Neither a96-step schedule nor the lowest
endpoint score selects an architecture from these unmatched starts.

If material progress continues without plateau, review another bounded round;
if it stalls, diagnose feasibility/conditioning before testing a larger matrix.
The next architecture evidence still requires at least three paired seeds and
verified function-preserving width starts. Do not replace that experiment with
the existing single trajectory per width. The study remains active.
