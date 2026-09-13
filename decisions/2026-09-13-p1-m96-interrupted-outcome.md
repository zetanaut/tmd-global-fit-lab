# P1 common96 attempt A01: useful progress, recoverable monitoring stops

All three jobs are terminal. There is no remaining allocation or scheduler
dependency for reviewing this round. Each passed the input, replay and
directional gates and produced a strictly feasible, audited endpoint.

| Width | q/N before this segment | q/N after this segment | New / cumulative accepted updates | Remaining to96 | Segment forwards / VJPs |
|---:|---:|---:|---:|---:|---:|
| 8 | 16.938637229 | 16.699705871 | 51 /81 | 15 | 323 /60 |
| 16 | 16.585009097 | 16.567795348 | 8 /46 | 50 | 62 /10 |
| 24 | 16.783958452 | 16.779529341 | 2 /30 | 66 | 33 /7 |

The corresponding immutable records are
[width8](../results/continuation-w8-p1-m96-a01/continuation-w8-p1-m96-a01-c4bba83de04a.json),
[width16](../results/continuation-w16-p1-m96-a01/continuation-w16-p1-m96-a01-a362528360f8.json), and
[width24](../results/continuation-w24-p1-m96-a01/continuation-w24-p1-m96-a01-d8f9323cdf43.json).
Their archives include the scheduler/preflight records and original complete
outputs. Each public archive was separately downloaded and compared byte for
byte with the retained copy. The saved-only
[review and cost ledger](../analysis/p1-m96-20260913-a01/review.json) and
[accepted-state curves](../analysis/p1-m96-20260913-a01/accepted-learning-curves.csv)
retain exact result identities, scores, calls, elapsed work and diagnostics.

## What these results support

Width8 gained0.238931358 in q/N, compared with0.017213749 and0.004429110
within the other two interrupted segments. These are progress measurements
from different starts and unequal update counts, not matched architecture
effects. In particular, continued optimization let width8 fall below the
current width24 endpoint; freezing an early ranking would have been misleading.
Width16 still has the lowest current q/N, but that does not establish it as the
best architecture.

All three remain far from the fixed convergence gate. Their final ten-update
q/N ranges are0.024970500,0.017506054 and0.006485054, versus the required1e-4;
terminal penalized-gradient maxima are0.171602,0.386682 and0.197163, versus1e-5.
The prediction-span tests also fail. The evidence supports continued progress,
not a plateau or a reason to discard any width. Raw endpoint gradients are
explicitly unavailable because monitoring stopped model work before that call.

All188 high-COMPASS diagnostic rows remain underpredicted, with raw residual
RMS approximately7.9795–7.9797 fixed sigma. This persistent pattern is worth
tracking through the later controlled comparisons. These unconverged fits do
not establish an irreducible residual floor or authorize a physics/data change.

## Why execution ended

Slurm jobs19818033/19818034/19818035 ended FAILED2:0 after36:18/9:03/8:02.
The result ledger classifies their scientific output as partial: valid saved
endpoints with interrupted execution. Each supervisor recorded
`FileNotFoundError` while reading that job's own `counters.json`.
Mandatory sampled memory remained within bounds; this was not a recorded
memory limit, scientific call limit, model-time limit or convergence event.

The code reads optional accepted-update progress through an `is_file()` check
followed by a separate open. The worker replaces the counter JSON before/after
dispatch. The final counter files exist, outputs are separate, and the wrapper
does not delete them. Replacement/filesystem visibility is strongly implicated,
but the exact filesystem cause is not proven: only the exception message,
not a supervisor traceback, was retained. Do not label that inference a proven
WekaFS defect.

## Recovery decision and next actions

1. Repair the progress reader before any successor uses this monitor. An
   unavailable optional progress sample must be explicitly marked and must not
   terminate otherwise fresh mandatory memory monitoring. Keep resource,
   stale-memory, deadline and authoritative worker call-budget checks intact.
   Validate missing-file/recovery cases and real resource failures in tests.
2. Retain unit backtracking, mu=1e-6, the original96-update target and the
   existing cumulative call/time ceilings. There is no result here that
   overturns the completed optimizer calibration.
3. Resume the verified accepted states with15/50/66 remaining updates, using
   new attempt IDs, isolated source revisions and claims. Preserve L-BFGS
   history and all21 states in each convergence window; perform the normal
   endpoint replay/directional gate and compute raw endpoint gradients within
   the reserved model allowance.
4. Complete the paired-start W03 feasibility specification in parallel with
   recovery preparation. Schedule it using the approved project concurrency
   and specialist review; the earlier PORT cap exceptions have ended. Its
   acceptance enables a separately specified paired-width matrix and does not
   itself compare optimized architectures.
5. Review all widths at the common96 milestone or the unchanged convergence
   gate. Further bounded optimization depends on the new progress and
   conditioning evidence; current endpoint rankings cannot select a winner.

Recovery imports are
[width8](../restarts/5669d2e34230e0a532becec9e57de1e5193789be75a260777ec69d99a5fd5779.json),
[width16](../restarts/9398025d32f8ffe89707faa0f7b0642b14d4ec1daceb4bcfb5013836a812954c.json), and
[width24](../restarts/6740c745e4fdba0129a3b1155b765dc64f3fb023ca8cd8f9c85ff4f134b931ba.json).
Each matches the audited theta/predictions/penalized gradient and validated
optimizer inventory. The terminal dispatch ledger adds6/6/2 forwards beyond
the committed states; width24 also adds1 VJP. These charges remain in the
imports even though the corresponding work did not produce an accepted update.
Remaining cumulative model time is17,104.400/19,316.117/19,397.547 seconds,
with3,451/3,801/3,864 forwards and412/452/472 VJPs remaining respectively.
No new scientific allowance or optimizer reset is granted by this recovery.

This decision records completed partial results and the recovery plan.
It does not assert that the repair or successor submissions have already run.
