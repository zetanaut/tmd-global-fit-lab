# PV17 exact-data baseline audit — 15 September 2026

## Verdict

PV17 supplies a historical exact-data baseline for the likelihood-v2 program.
Per Dustin's scope clarification, this is not a reproduction of the historical
NLL fit.  The purpose is to establish a larger, independently published starting
dataset and then fit it with this project's present N3LL matched theory,
likelihood machinery, and DNN.

The preferred target is the 2017 Pavia global fit (PV17),
[`arXiv:1703.10157`](https://arxiv.org/abs/1703.10157), because it is the
historical study that motivated the 8,059-versus-2,290 point-count concern.  It
now has an executable, hash-bound row population.  The public legacy repository
contains the relevant source tables.  Its checked-in historical fit
configuration does not identify one self-consistent final PV17 run, but that is
no longer a blocker because the old fit implementation and perturbative setup
are deliberately not being rerun.

The operator-preparation phase is now substantially complete, but it exposes
two real feasibility blockers rather than authorizing a DNN fit.  All 7,990 raw
SIDIS point operators have been constructed and CPU-replayed, and 285 of the
293 DY/Z rows reuse current operators with explicit unit adapters.  The eight
D0 Run-II rows map exactly to the first eight bins of a corrected 23-row
normalized-observable compile plan, but its physical full-support denominator,
provider binding and covariance remain open.  Separately, the transferred
width-8 endpoint predicts 16 nonpositive HERMES `K-` multiplicities.  A
completed component audit reproduces that sign failure under refined
quadrature and a narrow-bin limit.  The next action is theory/provider closure,
not GPU optimization.

## Published PV17 targets and row accounting

The paper reports the following flavor-independent NLL fit:

| Block | Points |
|---|---:|
| HERMES SIDIS | 1,514 |
| COMPASS SIDIS | 6,252 |
| Fixed-target Drell--Yan | 203 |
| Tevatron Z production | 90 |
| Total | 8,059 |

The `8,059` is not the number of source-table rows that survive the kinematic
cuts.  Executable reconstruction of the pinned public tables gives 7,990 raw
SIDIS rows, 203 DY rows and 90 Z rows, or 8,283 selected raw rows.  The 6,476
selected COMPASS rows comprise 224 `(x,z,Q2)` spectra.  PV17 divides each
spectrum by its lowest-`PhT` row and treats that denominator as a fixed
constraint, so those 224 rows are excluded from the point/d.o.f. count:

```text
8,283 selected raw rows - 224 COMPASS fixed denominators = 8,059 points
```

This reproduces 1,514 HERMES points, 6,252 COMPASS points, 203 fixed-target DY
points and 90 Tevatron Z points exactly.  The distinction is essential for the
new likelihood: treating 8,059 as an ordinary independent-row manifest would
reproduce the headline total for the wrong statistical reason.

There are 11 free parameters and therefore 8,048 nominal degrees of freedom.
The ensemble summary is `chi2 = 12,629 +/- 363` and
`chi2/d.o.f. = 1.55 +/- 0.05`; representative replica 105 is reported at
`chi2/d.o.f. = 1.51`.  The derived value from the rounded total is
`chi2/N = 1.5670678744 +/- 0.0450428093`.  The rounded total divided by 8,048
is 1.5692 rather than exactly 1.55.  These values are descriptive historical
context only.  They are not acceptance targets for a fit using different
theory and likelihood definitions.  The new fit reports its own `q/N`; it must
not relabel the paper's `chi2/d.o.f.` as the same quantity.

The published construction also fixes material details that differ from the
current 2,290-row study:

- NLL evolution with the leading-order hard contribution and no high-recoil
  matching;
- SIDIS cuts `Q2 > 1.4 GeV2`, `0.2 < z < 0.7`, and
  `PhT < min(0.2 Q, 0.7 Q z) + 0.5 GeV`;
- Drell--Yan and Z cut `qT < 0.2 Q + 0.5 GeV`;
- GJR08FFnloE collinear PDFs, DSEHS NLO pion FFs, and DSS07 kaon FFs;
- COMPASS multiplicities normalized within each `(x,z,Q2)` spectrum to its
  lowest-`PhT2` datum;
- diagonal experimental errors augmented by the study's FF uncertainty, with
  no covariance among kinematic bins; and
- 200 data replicas with randomized minimizer starts.

Those choices explain the published comparison but are not gates or inputs to
the new baseline.  The new operator retains only the identified experimental
observations, published cuts, and COMPASS ratio definition; it uses the current
project theory and a separately frozen modern covariance treatment.

## Public-artifact audit

The public
[`MapCollaboration/NangaParbat-Legacy`](https://github.com/MapCollaboration/NangaParbat-Legacy)
history adds `resources/fortran_fitcode` at commit
`7df66f4801151ce2384ca211422bdbfc70058832` on 2 April 2019.  That commit has
152 paths under the directory, including 48 data paths, the original-style fit
source, PDF/FF grids, and the row counts needed to reach 8,059.

It is not a self-contained receipt for the old fit:

- `input_choices.h` selects MMHT2014, disables SIDIS and Drell--Yan, and enables
  Z-only execution, contrary to the published global GJR08 configuration;
- `ref.txt` prints the correct final population counts but ends at
  `chi2/d.o.f. = 477.976...`, not the published result; and
- `fit.input` contains a later/local parameter state and no immutable binding
  proving that it generated the paper's final ensemble.

Later `FitResults/PV17_NLL` files preserve official replica parameter vectors,
including replica 105, but the inspected report evaluates only 353 Drell--Yan/Z
points and reports `Global chi2 = 35.965434`; it is not the full 8,059-point
PV17 prediction receipt.  These facts prevent an exact reproduction claim about
the historical NLL fit.  They do not prevent use of the pinned source tables as
the data baseline for a new fit.

The executable [row-closure receipt](row-closure.json) pins all 18 source data
files, reconstructs every cut and COMPASS normalization group, and records the
hash of a local 21,951-candidate JSONL manifest.  The manifest is generated only
under the ignored `run-output/` tree because it contains third-party
measurements; it is not committed or redistributed.  The broader
machine-readable [summary](summary.json) pins the audited commits and content
hashes.

Reproduce the receipt from a local clone containing the pinned commit:

```bash
python scripts/audit_pv17_row_closure.py \
  --legacy-repo /ABS/NangaParbat-Legacy \
  --summary-out analysis/historical-closure-baseline-20260915/row-closure.json \
  --manifest-out run-output/historical-closure-baseline-20260915/pv17-row-manifest.jsonl
```

The current manifest SHA-256 is
`3b40402fc42e3a7c85a0c3842e97cce3dbdbbb872de7478649dbe8c60e4a83c4`.

## Current-method preparation outcome

The [metric-v2 receipt](metric-contract-v2.json) builds the ordered 8,059-row
static data/error layer and closes all row, marginal-variance and Woodbury
checks.  It retains 224 COMPASS shared-denominator responses and seven
absolute-spectrum DY/Z normalization patterns.  Its production covariance is

```text
C_eff(t0) = diag(D) + U_COMPASS U_COMPASS^T
            + (F_norm t0) (F_norm t0)^T .
```

The named current-theory `t0` and theory/numerical responses remain B2 inputs.
D0 Run-II is deliberately kept in its published normalized form: PV17's
theory-derived `255.8 pb` conversion is excluded.

The [coverage receipt](operator-coverage-v2.json) identifies 285 reusable
current DY/Z operators, 7,990 new SIDIS point operators and eight D0 Run-II
rows with a distinct blocked contract.  Those eight are not ordinary missing
absolute operators.  The inherited current card covers `70 < Q < 110 GeV`,
whereas the published normalized observable requires a fiducial numerator and
normalization denominator on `40 < Q < 200 GeV` support with inclusive
rapidity.  Reusing either the narrow card or the PV17 normalization factor
would silently change the observable.

All selected SIDIS averages are within the declared current regional domain;
see the [domain receipt](sidis-domain.json).  The older fixed-`n_f` shortcut
would reject 2,505 rows and is not used.  The
[point pilot](sidis-point-pilot-v2.json) then closes a HERMES point and a
complete 22-row COMPASS spectrum, including a nonzero DNN gradient for a
fixed-order-only numerator through its trainable COMPASS denominator.

The completed [SIDIS campaign receipt](sidis-point-operators.json) binds 232
resumable shards containing all 7,990 raw SIDIS rows (7,766 scored rows plus
224 COMPASS denominators).  Direct Gaussian recovery closes to `5.33e-15`;
PyTorch operator replay closes to `1.25e-14`.  Of the raw rows, 7,049 are
fixed-order-only and 941 have an active W-term operator.  After the COMPASS
ratio map, 6,364 scored observations are DNN-coupled either directly or through
a denominator.  These are operator checks, not a fit.

The complete-population feasibility result is negative.  The Gaussian control
has 16 nonpositive rows, all HERMES `K-`.  Replaying the independently trained
width-8 update-658 endpoint over the new operators also gives exactly 16
nonpositive HERMES `K-` rows: 15 are shared, Gaussian-failing row 156 becomes
positive, and previously positive row 840 becomes negative.  The endpoint
minimum improves from `-1.94357` to `-0.806983`, but positivity is still
violated.  The failures split into seven full-additive and nine transition
rows, evenly between proton and deuteron targets.  COMPASS and the other three
hadron channels remain positive.  See the hash-bound
[endpoint-feasibility receipt](sidis-endpoint-feasibility.json).

The follow-up [K-minus sign diagnostic](hermes-kminus-sign-diagnostic.json)
finds 19 rows in the union implicated by the fixed contribution, Gaussian
control or transferred endpoint.  In 17 rows, the switched `ASY` contribution
is larger than `FO_T + FO_L`, so the matched fixed contribution is negative.
The direct component sum reproduces the stored operators to `4.45e-16`; all
signs survive doubled quadrature order, a wider Fourier range and a shrunk-bin
limit whose largest prediction shift is `5.46e-5` relative.  All 53,760 signed
channels obey the implemented `K-` charge-conjugation and proton/deuteron
isospin maps, although that algebraic check does not validate the physical FF
choice.  The implicated union contains eight full-additive and 11 transition
rows, with ten proton and nine deuteron targets.  This rules out serialization,
coarse quadrature and a simple flavor-map coding error; it localizes the open
question to the point-observable regional matching and kaon collinear-input
validity in this corner.

There is a promising conditional resolution already in the read-only
foundation.  Its independent NNLO central-input benchmark replaced NNFF10 by
HAPS-KaFF10 consistently in W, ASY and FO.  In three predeclared problematic
K⁻ bins (foundation source rows 188, 203 and 204), both declared matching
branches and both Gaussian/frozen-NP controls became positive; the PDF, DIS
denominator, geometry and DNN state were unchanged.  This proves the sign is
input-dependent and therefore potentially resolvable.  It does not select HAPS:
the benchmark covered only five source rows, did not refit the model, did not
recompute a global score, and HAPS is SIDIS-informed, so its independence from
our HERMES data is not established.  See the foundation's
`reports/ALTERNATIVE_KAON_FF_BENCHMARK_2026-09-10.md` and
`config/alternative_kaon_ff_status_v1.json`.

The [D0 Run-II contract audit](d0-runii-contract-audit.json) independently
matches all 23 PV17 source rows to the corrected compile plan and maps the eight
retained rows to bins 0--7.  Each numerator is an exact bin integral and uses
the same 23-row dependency set for the published `N_i/(Delta qT_i D)`
observable; the low-`qT` fit subset is never renormalized.  This is therefore
not an eight-point quotient-coding gap.  Evaluation remains blocked by the
governed `40 < Q < 200 GeV` registry revision, a hash-bound numerator/inclusive
NNLO-denominator provider with settled QED conventions, and the unreleased or
explicitly approximated normalized unfolding covariance.

This local executable SIDIS path is the conditional regional implementation:
unprimed N3LL W plus NLO positive recoil and an NLO inclusive-DIS denominator.
It is marked heavy-threshold-incomplete and `production_authorized=false`; the
combined observable must not be advertised as uniformly N3LL+NNLO.  The sign
failure is therefore a theory/feasibility diagnostic, not evidence against the
PV17 measurements and not something an added covariance term can repair.

## Required experiment sequence

### B0 — exact data population and QA (static contract passed; t0/D0 open)

1. Freeze the arXiv source version and one upstream data commit.
2. Bind every source row, cut decision, observable, experimental uncertainty,
   and COMPASS normalization group.  **Passed:** 21,951 candidate numeric rows;
   8,283 survive cuts; all selected central values and primary errors are
   finite and positive.
3. Reproduce `1514 + 6252 + 203 + 90 = 8059` after excluding 224 fixed COMPASS
   denominators.  **Passed.**
4. Freeze the ratio-covariance construction for each COMPASS spectrum and the
   correlated normalization treatment for DY/Z.  **Static layer passed:**
   Jacobian propagation of each shared COMPASS denominator and seven DY/Z `t0`
   patterns are built.  A feasible current-theory `t0` and the D0 normalized
   prediction contract remain open.

The historical final fit configuration and replica predictions are not required.

### B1 — current-theory operator construction (SIDIS complete; D0 blocked)

Generate a new operator on the exact B0 population using the project's present
unprimed N3LL evolution/W, DY NNLO fixed order, implemented SIDIS positive-recoil
term, matching functions, collinear inputs, numerical accuracy, and uncertainty
response conventions.  Bind every input and generated array by hash.  Do not
reuse PV17's NLL kernels, PDFs/FFs, FF-error model, or MINUIT settings.

COMPASS predictions and data must undergo the same within-spectrum ratio map.
The 224 denominators define the transformation and covariance but are not
additional scored observations.

**Current result:** all 7,990 SIDIS operators are built and replayed; 285 DY/Z
operators are reusable.  The D0 source crosswalk and ratio-of-integrals compile
actions close, but the eight retained observations cannot be evaluated until
the registry, physical provider/QED and covariance gates close.  No fabricated
absolute or display-point D0 operator is permitted.

### B2 — operator and metric validation (blocked before GPU replay)

Independently recompute a stratified set of DY, Z, HERMES, and COMPASS
predictions; close transformed observables, covariance solves, nuisance
decompositions, and gradients to preregistered tolerances.  Check row order,
finite values, covariance positive definiteness/conditioning, complete
observable positivity, and fixed-sigma prediction replay on CPU and the RTX
4090 before optimization.

**Current result:** CPU replay finds 16 nonpositive HERMES `K-` predictions at
the transferred width-8 endpoint.  Positivity therefore fails before an ordered
8,059-row score, gradient, or GPU replay would be meaningful.

### B3 — baseline DNN fit

Fit the current DNN on the validated 8,059-observation metric using the single
RTX 4090.  Use at least the registered transferred start and two independent
feasible starts, run sequentially, and retain all failed feasibility work.  The
update ceiling must be high enough for the time/convergence rule to control the
run; it must not inherit the obsolete 192-update limit.

Report `q/N`, every experiment/process contribution, raw and adjusted
residuals, normalization pulls, positivity, convergence, calls, elapsed time,
and the complete endpoint audit.  PV17's reported `chi2/d.o.f.` is context, not
a pass threshold, because the theory and metric intentionally differ.

**Not authorized:** more optimizer time cannot cure an unreviewed central-theory
sign failure or define the missing D0 normalized observable.

### B4 — baseline assessment

Compare the new 8,059-point fit with the current 2,290-point fit on overlapping
observations and on a frozen supported TMD grid.  Run grouped holdouts that keep
entire COMPASS normalization spectra together.  Decide whether this is a sound
starting dataset from data integrity, covariance behavior, fit convergence,
process balance, held-out prediction, and TMD stability—not from whether the
new score numerically matches 1.55.

## Scope boundary

MAPTMD22 is no longer a fallback requirement for this baseline: PV17 already
provides the intended historical data population.  Reproducing either paper's
old fit would be a separate optional software-reproduction study.  This baseline
does not modify the existing frozen 2,290-row likelihood; its new operator and
metric require their own versioned contracts before fitting.

## Scientifically sound next move

The all-19-row family diagnostic is now complete and is recorded in
`hermes-kminus-ff-family-diagnostic.json`: NNFF10 is negative in 16/19 rows
(minimum −1.944), while HAPS-KaFF10 is positive in all 19 (minimum +0.0159)
under the current Gaussian NP control.  This is a conditional theory-input
result only; no fit, operator replacement, uncertainty calibration, or
production selection was performed.  HAPS still requires an independence and
data-overlap review before any global-fit use.

The production-readiness gate is documented in `haps-production-readiness.md`.
Because HAPS was fitted using HERMES and COMPASS SIDIS data, its current tables
cannot be promoted into the same HERMES likelihood without a leave-one-out
refit, explicit cross-covariance treatment, and license clearance.

1. Extend the demonstrated HAPS-vs-NNFF comparison coherently to all 19
   implicated PV17 K⁻ rows, retaining NNFF10 as a sensitivity reference.  If
   positivity closes, compare the average-point result with a qualified
   exact-bin implementation.  Do not tune the DNN to compensate for the
   `ASY > FO_T + FO_L` cancellation.
2. Complete the governed D0 registry revision to `40 < Q < 200 GeV`, then bind
   and converge the same-family N3LL+NNLO numerator and inclusive NNLO
   denominator with explicit QED conventions.  Recover the normalized
   unfolding covariance or approve a clearly labeled approximation likelihood;
   diagonal published errors are not the exact likelihood.
3. Only after both central-theory gates close, bind a feasible `t0`, assemble
   the ordered 8,059-observation operator, and run the preregistered CPU/GPU
   metric, gradient and positivity checks before optimization.

An out-of-domain/theory-error response may still be added as a labeled
covariance component where justified.  It does not make a negative central
multiplicity physical and does not substitute for the D0 normalization
denominator.
