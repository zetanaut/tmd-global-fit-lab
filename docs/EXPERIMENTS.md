# Experiment program and autonomous work queue

This program supersedes machine-specific launch instructions, not the frozen
scientific contract. Plans become executable only through a committed exact
trial JSON and implementation tests. Hardware permits parallel independent
cells; it does not remove dependencies between scientific phases.

## Work queue

| Task | Owner capability | Deliverable and completion gate |
|---|---|---|
| W00 portability | CPU and GPU agents | Six PORT whole-data replay trials. Each new backend/GPU/software family passes value, raw-gradient where saved, and two active-mu directional checks. Record timings/resources. |
| W01 import closed current endpoints | CPU agent | Import the latest completed local P0 endpoints as immutable checkpoint artifacts with hashes, exact source lineage, accepted counts and raw receipts. Coordinate with the existing local owner; do not rerun its live targets. |
| W02 checkpoint-overlay support | Coding/CPU agent | Add a content-addressed checkpoint registry for later run artifacts, verified parent hash/schema/q and source/metric/bundle binding. Keep the large operator bundle unchanged. Tests reject wrong-parent and stale-budget attempts. |
| W03 initialization factory | Coding/CPU agent | Port function-preserving width embedding and feasible seeded starts, with exact parameter inventories and before/after predictions. Preserve nonzero added features with initially zero output connections. All repair/model-call cost enters trial budget. |
| W04 P1 convergence | GPU agents | Comparable final-barrier continuation rounds for the three selected starts after PORT/W01/W02. Use saved-array reviews to decide bounded next rounds. |
| W05 original-family identity | Scientific/code agent | Identify the exact intended original implementation and revision; archive its computational source and prior contract. The inherited program did not pin this. If it cannot be resolved from supplied provenance, ask Dustin specifically rather than substituting a different network. |
| W06 family adapters | Coding/CPU agent | Implement the pinned original interface and verify mathematical/source equivalence. No silent changes to the observable contraction. Add source-bound family dispatch and tests before P2. |
| W07 depth and conditioning factories | Coding/CPU agent | Depth 1/2/3 and input/every/last conditioning with clear function definitions, parameter matching, initial prediction comparisons and derivative/positivity tests. No duplicate depth-1 placements. |
| W08 independent review | CPU agents | Validate all result archives and compare raw/adjusted residuals, nuisance penalties, stability and cost; publish decision records at each gate. |

W02/W03/W05/W06/W07 are explicit unfinished implementation tasks. Existing runtime
supports registered same-schema Nested-FiLM continuations and PORT, not every
future variant. An agent may implement these within scope and submit tested PRs;
do not claim a declared experiment has run before its artifacts exist.

## Phase matrices

| Phase | Fixed question | Matrix / allocation |
|---|---|---|
| PORT | Portable implementation fidelity | Width 8/16/24 x CPU/GPU; distinct GPU models/software changes get new attempt IDs. No optimizer updates. |
| P0 | Equalize initial continuation opportunity | w24/S00, w8/S01, w16/S02 at 160 total accepted updates each: 64 screening +96 refinement. Import existing results first. |
| P1 | Adequate optimization of selected trajectories | Same three starts at mu=1e-6, up to96 further updates each per justified round. Rotate first architecture or run independent cells concurrently. |
| P2 | Original versus Nested-FiLM | 2 families x2 parameter-count bands x3 paired seeds =12 cells. Choose bands from evidence; counts within10% where feasible. |
| P3 | Depth at matched capacity | Depth1/2/3 x3 paired seeds =9 cells in evidence-supported family. Adjust width, not physics. |
| P4 | Conditioning placement | Input-only/every-block/last-block x3 paired seeds =9 cells at supported depth>=2 and approximately matched count. |
| P5 | Targeted structural follow-up | One justified axis at a time; <=3 arms x3 paired seeds. Consider skip/residual, activation, boundary sharing or output-head prior. |

The historical P0 correction was w24 checkpoint064 +32 and w8 checkpoint083 +13,
both mu=1e-6; w16 was reference-only. The release retains those pinned historical
parents for replay. Their presence is not an instruction to duplicate the live
local continuation. A new trial ID must explain whether it is a reproduction,
an intended successor, or a diagnostic alternative branch.

The intended “original” family may have a different output/monotonicity prior.
Treat P2 as a family-package comparison unless that difference is independently
controlled. Do not describe Nested-FiLM as a strict superset without proof.

## Exact preregistration before execution

For each new trial freeze: hypothesis; phase; family implementation/version;
width/depth/placement/parameter inventory; paired seed; exact parent and starting
function; data/source/metric/bundle identities; code commit; barrier stages;
accepted/full/forward/wall limits; device/resource profile; prerequisites;
planned diagnostics; and decision rule. Give technical retries NEW attempt IDs
with parent attempt and already-spent costs. Commit this before claiming/running.

Extend `contracts.py` only through reviewed tests when adding a new factory or
initialization route. Passing a new arbitrary JSON family string must never
select unverified code. Use `decisions/YYYY-MM-DD-<slug>.md` to record supported
promotions; link result identities, counterevidence and remaining qualifications.

## Compute allocation and fairness

Initial portable per-trial window: <=1,800 seconds setup+model work and 1,800
seconds reserved saved-array QA, total3,600. This is inside the inherited7,200s
window and5,400s model-work maxima. Each trial <=240 full/VJP calls,600 forwards,
96 accepted updates; smaller phase allocations remain authoritative. Preserve
cost of infeasible starts/probes/rejections and interrupted calls.

Common schedule and accepted-update opportunities are necessary, not sufficient
for comparable convergence. Report objective against accepted steps, calls and
elapsed seconds. Different GPU types have different cost; calibrate timings and
retain hardware identity. Do not rank a time-censored slow-hardware cell as a
scientific loser. Parallel trials do not share optimizer state or random streams.

No automatic infinite continuation: at each completed matrix assess whether
another bounded round is scientifically informative. Inconclusive or negative
findings are valid outcomes. A genuine new physics/reference question is a
recorded escalation, not an in-scope optimization tweak.

