# Experiment program and autonomous work queue

Current results, changed scheduling strategy and promotion gates are maintained
in [CURRENT_STUDY_PLAN.md](CURRENT_STUDY_PLAN.md). The first portable P1 round
is terminal; the broader architecture study is active. Historical specifications
remain immutable. New continuation budgets must explicitly account for prior
steps and preserve verified optimizer state.

This program supersedes machine-specific launch instructions, not the frozen
scientific contract. Plans become executable only through a committed exact
trial JSON and implementation tests. Hardware permits parallel independent
cells; it does not remove dependencies between scientific phases.

## Work queue

| Task | Owner capability | Deliverable and completion gate |
|---|---|---|
| W00 portability | CPU and GPU agents | Six PORT whole-data replay trials. Each new backend/GPU/software family passes value, raw-gradient where saved, and two active-mu directional checks. Record timings/resources. |
| W01 import closed current endpoints | CPU agent | V7 w8/w24 exact finals imported with immutable scientific evidence and explicitly redacted receipt derivatives/original hashes; w16 unchanged. See `evidence/p0-v7-2026-09-13/index.json`. P0 complete/unconverged. |
| W02 checkpoint-overlay support | Coding/CPU agent | V1 supports imported V7 endpoints with exact baseline parents, verified hashes/schema/q and source/metric/bundle binding. See `docs/CHECKPOINT_OVERLAYS.md`. New artifact formats/parent chains require reviewed adapters; no implicit execution clearance. |
| W03 initialization factory | Coding/GPU agent | The width factory is complete; the next bounded paired feasibility plan evaluates three narrow width8 candidates first, then only if their all-observable diversity gate passes evaluates their width16/24 transports (9 cells; >=63 forwards/18 VJPs; zero updates). Persist all failed/passing evidence and register immutable starts only after pass. The executable protocol is under independent review; no W03 claim or run exists. |
| W04 P1 convergence | GPU agents | Comparable final-barrier continuation rounds for the three selected starts after PORT/W01/W02. Use saved-array reviews to decide bounded next rounds. |
| W05 original-family identity | Scientific/code agent | Identify the exact intended original implementation and revision; archive its computational source and prior contract. The inherited program did not pin this. If it cannot be resolved from supplied provenance, ask Dustin specifically rather than substituting a different network. |
| W06 family adapters | Coding/CPU agent | Implement the pinned original interface and verify mathematical/source equivalence. No silent changes to the observable contraction. Add source-bound family dispatch and tests before P2. |
| W07 depth and conditioning factories | Coding/CPU agent | Depth 1/2/3 and input/every/last conditioning with clear function definitions, parameter matching, initial prediction comparisons and derivative/positivity tests. No duplicate depth-1 placements. |
| W08 independent review | CPU agents | Validate all result archives and compare raw/adjusted residuals, nuisance penalties, stability and cost; publish decision records at each gate. |
| W09 PV17 exact-data baseline | Scientific/code agent; GPU held | Row accounting and the static metric pass: 21,951 candidates -> 8,283 selected rows -> 8,059 effective observations after 224 COMPASS constraints. All 7,990 SIDIS point operators are built/replayed and 285 DY/Z operators are reusable, but 16 transferred-endpoint HERMES `K-` predictions are nonpositive and eight normalized D0 Run-II rows need the corrected `40<Q<200` numerator/denominator contract. Diagnose those blockers before ordered metric/GPU validation or fitting. The historical NLL fit is not rerun, MAPTMD22 is not a required fallback, and no 192-update cap applies to any eventual fit. |

The same-depth [width-transport helper](INITIALIZATION.md) and a candidate-only
distinct narrow-seed factory are implemented and CPU-tested. W03 still needs
registered full-observable-verified starts and a bounded paired feasibility
search; it is not ready for scientific execution.
W03/W05/W06/W07 remain explicit unfinished implementation tasks. Existing runtime
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

Native P1 is separately assigned to the Manager and does not wait for PORT or
this portable implementation. W04's PORT dependency applies to portable runners,
not to the independently owned native program. No GPU PORT/UVA launch is granted
by W01/W02 evidence integration.

The historical P0 correction was w24 checkpoint064 +32 and w8 checkpoint083 +13,
both mu=1e-6; w16 was reference-only. The release retains those pinned historical
parents for replay. V7 has now consumed that exact correction; their presence is
not an instruction to repeat it. A new trial ID must explain whether it is a reproduction,
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
