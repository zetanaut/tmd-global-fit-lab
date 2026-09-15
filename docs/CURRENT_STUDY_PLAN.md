# Current study plan — 14 September 2026

This is the public coordination entry point for the fixed-physics architecture
study. It supersedes the short-window scheduling strategy, while retaining all
historical trial specifications and results. The study remains active until
adequate optimization and controlled architecture comparisons support a choice.
Completing a job batch or publishing partial results does not complete the study.

## Required historical exact-data closure baseline

The [historical closure plan](../decisions/2026-09-15-historical-closure-baseline-plan.md)
adds an independent data-and-fit sanity gate before a likelihood-v2 production
fit.  PV17 (`arXiv:1703.10157`) is the preferred target because it used 8,059
points and directly addresses the present data-coverage concern.  The controlled
sequence first reproduces the historical 11-parameter model on its exact rows,
then distills those functions into the DNN without looking at data residuals,
and only then fits the DNN with every historical data/theory/likelihood choice
held fixed.  Paired grouped holdouts and a preregistered TMD-grid comparison are
required because a lower in-sample score from a much more flexible model does
not by itself establish a better extraction.

The [artifact audit](../analysis/historical-closure-baseline-20260915/README.md)
finds that public PV17 source, data, grids and official replica parameters are
available, but not yet as a self-identifying exact final-run bundle.  Its
executable row subgate now closes 21,951 candidate rows to 8,283 cut-selected
rows and then to the published 8,059 effective points after excluding 224 fixed
COMPASS normalization denominators.  The checked-in public input/output remain
inconsistent with the published global run, so the final card and full-data
prediction receipt are still required before historical-model replay.  No
historical DNN fit is currently authorized; H1 itself may use the GPU if the
theory replay benefits.  MAPTMD22 is the fallback only
if an exact PV17 identity cannot be recovered and only after its own artifact
binding closes.  Neither historical prescription changes the frozen 2,290-row
study or preselects the likelihood-v2 theory/error model.

## Data-scope and theory-validity diagnostic

The [full COMPASS source reevaluation](../analysis/full-dataset-reevaluation-20260915/README.md)
audits all 4,664 primary rows in the official 162-table release and saved-only
rescoring of the width-8 update-658 endpoint.  Under conservative rectangular
support bounds, the current 1,203-row likelihood already contains every public
COMPASS bin wholly at or below `qT/Q=0.30`; the 3,461 additions comprise 171
mixed-support and 3,290 wholly fixed-order-role rows, with no pure-core rows.

The fixed endpoint's COMPASS quadratic form is dominated by its 278
fixed-order-role rows.  A direct transfer of the factorization-error law in
arXiv:2608.27907 collapses COMPASS's independent variance weight rather than
validating the central theory, and correlated versus diagonal constructions
give materially different results.  Therefore the proposed scientific next
step is a separately versioned likelihood study with exact constrained support
and preregistered theory-response covariance, not an automatic continuation or
a blind 4,664-row expansion.  This diagnostic changes no frozen input, metric,
trial, result, or production selection; likelihood-v2 remains unapproved until
its source, operator, covariance, and decision contracts are reviewed.

## Latest local outcome: width-8 second window stops at 658

The [A04 outcome](../decisions/2026-09-15-local-w8-a04-outcome.md) records 235
new / 658 cumulative accepted updates, q/N 15.91920723937984 and a valid
finite-positive endpoint. The second two-hour opportunity stopped at a genuine
32-trial line-search exhaustion while proposing update 659; it did not crash or
hit a resource limit. Both convergence criteria remain unmet, and the terminal
raw gradient is explicitly missing because line-search exhaustion preceded the
reserved raw-gradient call.

The unchanged trajectory was informative but its gain rate deteriorated and its
last accepted step was below 1e-9. The next default action is a preregistered
equal-budget optimizer/feasibility comparison from update 658, retaining this
unit-backtracking state as control. No unchanged automatic continuation is
authorized.

## Previous local outcome: width-8 repaired continuation reaches 423

The [A03 outcome and saved-only review](../decisions/2026-09-14-local-w8-a03-outcome.md)
records 171 new / 423 cumulative accepted updates, q/N 16.11080233178303 and an
audited finite, positive endpoint. The segment ended for its endpoint time
reserve; there was no new crash and neither convergence window passed. Late
progress per evaluation improved. The original A01 plus repaired A03 used
7013.4294 seconds of the 7200-second opportunity, including setup/replay.

The immutable archive has been downloaded and verified. Saved high-COMPASS
decomposition shows small current trainable contributions alongside persistent
residuals, not an irreducible floor or a derivative measurement. Dustin approved
one further two-hour continuation from 423 with unchanged optimizer/history,
plus this targeted saved-only analysis. The
[second-window A04 plan](../decisions/2026-09-14-local-w8-second-window-plan.md)
registers a fresh 7200-second opportunity, preserving all earlier charged work.
Its generous count ceilings permit 4096 new updates rather than inheriting the
historical 192-update cap. Exact claims and launch receipts, not the ready trial
specification, establish whether it is running. No automatic successor is granted.

## Earlier local candidate-domain failure and repair

The local two-hour instrumented attempt is now terminal: 75 new accepted
updates, 252 cumulative, q/N 16.411446133424036, and an audited positive endpoint
without convergence. It consumed 2206.108 model-window seconds, then a full-size
candidate underflowed the boundary damping and the exception aborted the run.
See the [failure outcome and repair scope](../decisions/2026-09-14-local-w8-domain-failure-outcome.md).
The owner requested a tested numerical-domain rejection remedy; any successor
must preserve the original attempt and charge only the remaining opportunity.
The [A03 technical recovery](../decisions/2026-09-14-local-w8-domain-repair-a03-plan.md)
preregisters typed candidate-domain rejection and the remaining 4993-second
model window from the exact 252-update restart. It changes neither the original
cumulative grant nor the physics/optimizer/convergence equations. Claim and
launch receipts, not this preregistration, establish execution state.
A02 was held before any worker launch when CI exposed a cross-BLAS curvature
validation issue. Its spec and claim remain; A03 adds a roundoff certificate
without changing the saved optimizer state or remaining compute allowance.

## Latest UVA outcome and bounded width-16 recovery

The [width-16 A02 result](../decisions/2026-09-14-uva-w16-domain-failure-outcome.md)
records 137 new / 183 cumulative updates, q/N 16.364263303504803 and a valid
unconverged endpoint. Its first candidate for update 184 failed at the incoming
boundary guard after 8930.176 model seconds; this was a numerical exception,
not exhaustion of the seven-hour opportunity. The immutable archive and exact
restart retain the final failed forward and all optimizer history.

The [A03 recovery plan](../decisions/2026-09-14-uva-w16-domain-recovery-plan.md)
applies the independently reviewed shared candidate-domain repair and curvature
certificate on UVA. It uses only 16269 remaining model seconds, on one A6000
with five-hour walltime, and requires actual typed candidate diagnostics and an
accepted update beyond 183 before claiming recovery. Claim and scheduler
receipts establish execution state; neither repair nor recovery proves convergence.

## Earlier local result and complementary UVA plan

The complementary UVA action is a
[seven-hour instrumented width-16 continuation](../decisions/2026-09-14-uva-w16-long-training-plan.md)
from its verified 46-update state on one A6000. It reuses the local diagnostic
implementation and unit optimizer, preserves all prior costs and state, and
provides a long time-based opportunity with unchanged convergence tests. Its
versioned policy retains historical limits. The local agent owns width 8;
this separate trial supersedes the unclaimed width-16 common96 A02 draft.
Exact claims and scheduler receipts establish whether it has been submitted.
Its first launch stopped before any model work because of an inherited launcher
provenance guard. The [A02 launch correction](../decisions/2026-09-14-uva-w16-long-training-a02-plan.md)
preserves that failed attempt and the identical scientific opportunity under a
new trial and claim; it adds shared static validation before submission.

The next owner-authorized local action is one
[two-hour instrumented width-8 continuation](../decisions/2026-09-14-local-w8-feasibility-2h-plan.md)
from the 177-update endpoint on the single RTX 4090. It preserves unit
backtracking and records failed rows, step/gradient/curvature diagnostics, and
progress every 32 accepted updates. Its immutable trial defines the bounded
time opportunity; the reports themselves do not stop optimization. Claim and
launch receipts, rather than this plan, establish execution state.

The [local P1B outcome](../decisions/2026-09-14-local-w8-p1b-outcome.md) is now
recorded: 96 additional accepted updates from the verified 81-update restart,
reaching 177 cumulative portable P1 updates. q/N improved from 16.699705871 to
16.448895619. Execution completed normally after 2,061.045 seconds; the saved
endpoint audit passes and both unchanged convergence windows fail. Raw endpoint
gradients, all accepted checkpoints and the cumulative call/time ledger are
retained in the verified archive and immutable result record.

This completes the one opportunity specified in the
[local P1B plan](../decisions/2026-09-13-local-w8-p1b-plan.md). Its next action is
the planned review of progress, feasibility and conditioning before any new
allocation. Width 24 still has its earlier interrupted endpoint; the latest
width-16 outcome is recorded above. Unequal optimization opportunities do not
support an architecture ranking.

The common96 chronology below is retained as historical context. Its width-8
15-update recovery instruction predates this completed local extension and must
not be treated as a request to duplicate the old trajectory.

## Earlier common96 outcome and recovery decision

The three common96 A01 jobs have now ended with recoverable monitoring stops;
see the [result review and recovery decision](../decisions/2026-09-13-p1-m96-interrupted-outcome.md).
Width8 advanced from30 to81 cumulative updates (q/N16.699705871), width16 from38
to46 (16.567795348), and width24 from28 to30 (16.779529341). All saved endpoint
audits pass; all convergence tests fail. The common supervisor failure was a
missing optional `counters.json` progress read. There is no remaining queue wait
for these three completed attempts.

The next executable step is a tested progress-monitor repair followed by
state-preserving successors for the remaining15/50/66 updates to96, within the
unchanged cumulative budgets. Three new immutable restart imports retain all
interrupted-call costs. The complete archives, accepted-state CSV and saved
diagnostics accompany the decision. Successor specifications/claims are not yet
published. The chronology below records the earlier scheduling decisions;
its references to queued A01 jobs are superseded by this terminal outcome.

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
preregistered B200 width16 replay only; width24 remained conditional on that
new cell. The completed width16 result subsequently permitted the separately
reviewed width24 check reported below; none of these steps migrates active
A6000 P1 continuations or constitutes an architecture comparison.

That separately scoped [B200 width16 A01 PORT plan](../decisions/2026-09-13-b200-w16-a01-plan.md)
completed cleanly; its independently reviewed [outcome](../decisions/2026-09-13-b200-w16-a01-outcome.md)
and immutable result preserve the claim, source, archive, numerical and monitor
evidence. It is the first B200 width16 cell, eight forwards/three VJPs/zero
updates, and establishes B200 execution for that fixed replay only. The
temporary fourth-GPU exception ended at terminal state. Its separately
preregistered and reviewed width24 successor is reported below. No B200
optimization or architecture conclusion is authorized; the three A6000 P1
continuations remain independent.

That final [B200 width24 A01 PORT plan](../decisions/2026-09-13-b200-w24-a01-plan.md)
completed cleanly; its independently reviewed [outcome](../decisions/2026-09-13-b200-w24-a01-outcome.md)
and immutable result preserve the archive, retained CPU/A6000 reference
endpoints, saved-only raw-gradient comparison, numerical and monitor evidence.
This completes the authorized B200 PORT sequence. It establishes only bounded
execution portability for the fixed replay anchors; no B200 optimizer,
throughput or architecture claim follows. The normal project cap is three and
the independently queued A6000 P1 continuations remain the next scientific
source of optimization evidence.

## Parallel non-duplicate initialization evidence (W03)

The next proposed work that can inform the architecture study without
duplicating the queued P1 continuations is **W03 paired-width feasibility**.
It is a bounded, zero-update test of whether three distinct small perturbations
of the exact width8 anchor can each be transported to width16 and width24 while
retaining all2,290 fixed-physics predictions and satisfying feasibility,
penalized/raw-VJP replay, and two directional checks on the actual backend.
Candidate generation itself makes zero model calls.

The required order is deliberate: evaluate all three width8 candidates first,
measure their preregistered all-observable fixed-sigma diversity, and only then
evaluate the six widened partners. Thus an infeasible or insufficiently diverse
start set terminates before it wastes wide-model compute. A passing complete
set has nine cells and needs at least63 forwards and18 VJPs; all calls,
interrupted dispatches, failed values/probes, transport receipts and endpoints
are retained. It is evidence that a controlled paired-width matrix can start
fairly—not evidence of optimizer convergence, independent attraction basins,
or an architecture winner.

The evaluator/supervisor and exact trial protocol are under independent review;
there is **no W03 claim or submitted job yet**. Subject to that review and an
explicit temporary fourth-GPU exception, the resource plan is one sequential
B200 allocation (one GPU, two CPUs,16GiB), not three concurrent allocations.
It will coexist with, but never modify or duplicate, the three queued A6000 P1
cells. If the feasibility gate passes, the registered immutable paired starts
become the input to a separately preregistered multi-seed architecture matrix.

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
exceptions for completed B200 A03, width16 A01 and width24 A01 have all ended;
the normal cap is three and the B200 PORT sequence is closed. Any future
resource exception requires a new scientific plan and UVA HPC specialist review.
Never mutate the
checkout mounted by an active job; each executable revision has an isolated
pinned checkout. Credentials remain on the transfer host.

Before new scientific trials: pass restart-equivalence tests, counter/lineage
tests, termination tests, and real allocated-device telemetry qualification;
commit exact cell specifications, parent hashes, total budgets and decision
rules, then create distinct atomic claims. Publish substantive outcomes and
plan decisions promptly. Routine submission lessons stay in local operations
notes. Preserve all published archives and historical results.
