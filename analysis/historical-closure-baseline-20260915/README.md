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

No DNN fit starts from the row audit alone.  The next gate is to freeze and
validate a new operator for these exact observations using the project's current
theory and covariance contracts.  CPU or GPU may be used according to the work;
the dependency is scientific validation, not hardware policy.

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

## Required experiment sequence

### B0 — exact data population and QA (row accounting passed)

1. Freeze the arXiv source version and one upstream data commit.
2. Bind every source row, cut decision, observable, experimental uncertainty,
   and COMPASS normalization group.  **Passed:** 21,951 candidate numeric rows;
   8,283 survive cuts; all selected central values and primary errors are
   finite and positive.
3. Reproduce `1514 + 6252 + 203 + 90 = 8059` after excluding 224 fixed COMPASS
   denominators.  **Passed.**
4. Before operator production, freeze the ratio-covariance construction for
   each COMPASS spectrum and the correlated normalization treatment for DY/Z.
   The primary proposal is Jacobian propagation of the shared denominator,
   with the historical diagonal approximation retained only as a sensitivity.

The historical final fit configuration and replica predictions are not required.

### B1 — current-theory operator construction

Generate a new operator on the exact B0 population using the project's present
unprimed N3LL evolution/W, DY NNLO fixed order, implemented SIDIS positive-recoil
term, matching functions, collinear inputs, numerical accuracy, and uncertainty
response conventions.  Bind every input and generated array by hash.  Do not
reuse PV17's NLL kernels, PDFs/FFs, FF-error model, or MINUIT settings.

COMPASS predictions and data must undergo the same within-spectrum ratio map.
The 224 denominators define the transformation and covariance but are not
additional scored observations.

### B2 — operator and metric validation

Independently recompute a stratified set of DY, Z, HERMES, and COMPASS
predictions; close transformed observables, covariance solves, nuisance
decompositions, and gradients to preregistered tolerances.  Check row order,
finite values, covariance positive definiteness/conditioning, complete
observable positivity, and fixed-sigma prediction replay on CPU and the RTX
4090 before optimization.

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
