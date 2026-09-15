# Historical fit closure baseline audit — 15 September 2026

## Verdict

A historical closure benchmark is now a required part of the likelihood-v2
program.  Its purpose is different from the full-source census: it must show
that the data adapter, theory operator, likelihood, optimizer, and TMD readout
can recover an independently published result before the same fitting machinery
is trusted on a new data/theory construction.

The preferred target is the 2017 Pavia global fit (PV17),
[`arXiv:1703.10157`](https://arxiv.org/abs/1703.10157), because it is the
historical study that motivated the 8,059-versus-2,290 point-count concern.  It
is not yet an executable exact baseline.  The public legacy repository contains
the relevant Fortran source and data, but those files were deposited in 2019
and the checked-in input and output do not identify one self-consistent final
PV17 run.  Reconstructing the row manifest and final run identity is therefore
the first gate, not an implementation detail to infer silently.

No GPU fit is authorized by this audit.  The row, observable, nuisance,
collinear-input, and numerical identities must close on CPU before constructing
a new signed operator or spending the single local GPU.

## Published PV17 targets

The paper reports the following flavor-independent NLL fit:

| Block | Points |
|---|---:|
| HERMES SIDIS | 1,514 |
| COMPASS SIDIS | 6,252 |
| Fixed-target Drell--Yan | 203 |
| Tevatron Z production | 90 |
| Total | 8,059 |

There are 11 free parameters and therefore 8,048 nominal degrees of freedom.
The ensemble summary is `chi2 = 12,629 +/- 363` and
`chi2/d.o.f. = 1.55 +/- 0.05`; representative replica 105 is reported at
`chi2/d.o.f. = 1.51`.  The derived value from the rounded total is
`chi2/N = 1.5670678744 +/- 0.0450428093`.  The rounded total divided by 8,048
is 1.5692 rather than exactly 1.55, so the paper's ensemble summaries are not a
machine-precision numerical receipt.  The benchmark must always report both
`q/N` and the paper's historical `chi2/d.o.f.` convention rather than treating
them as interchangeable.

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

Those choices are part of the historical metric.  They are not endorsed as the
likelihood-v2 prescription and must not leak into the current frozen likelihood.

## Public-artifact audit

The public
[`MapCollaboration/NangaParbat-Legacy`](https://github.com/MapCollaboration/NangaParbat-Legacy)
history adds `resources/fortran_fitcode` at commit
`7df66f4801151ce2384ca211422bdbfc70058832` on 2 April 2019.  That commit has
152 paths under the directory, including 48 data paths, the original-style fit
source, PDF/FF grids, and the row counts needed to reach 8,059.

It is not a final-run receipt:

- `input_choices.h` selects MMHT2014, disables SIDIS and Drell--Yan, and enables
  Z-only execution, contrary to the published global GJR08 configuration;
- `ref.txt` prints the correct final population counts but ends at
  `chi2/d.o.f. = 477.976...`, not the published result; and
- `fit.input` contains a later/local parameter state and no immutable binding
  proving that it generated the paper's final ensemble.

Later `FitResults/PV17_NLL` files preserve official replica parameter vectors,
including replica 105, but the inspected report evaluates only 353 Drell--Yan/Z
points and reports `Global chi2 = 35.965434`; it is not the full 8,059-point
PV17 prediction receipt.  Thus the public material is valuable and may be
sufficient for a careful reconstruction, but its exact final configuration must
be demonstrated rather than assumed.

The machine-readable [summary](summary.json) pins the audited commits and
content hashes.  No upstream raw data are redistributed here.

## Required experiment sequence

### H0 — provenance and row closure

1. Freeze the arXiv source version and a single upstream source/data commit.
2. Build an ordered manifest containing every retained row ID, observable,
   transformation, cut decision, central value, uncertainty term, and
   normalization group.
3. Reproduce exactly `1514 + 6252 + 203 + 90 = 8059` after all transformations.
4. Recover the exact final compile-time choices, 11-parameter definitions,
   collinear-grid versions, electroweak constants, quadrature settings, replica
   seeds, and MINUIT controls.  Search public history and archived releases
   before requesting missing material from the authors.
5. Locate a full-data prediction or score receipt for replica 105 or another
   explicitly identified published replica.  Rounded paper tables alone do not
   pass this gate.

Any unresolved row-count, normalization-denominator, covariance, or final-card
ambiguity keeps PV17 at `provisional`, not `exact`.

### H1 — historical-model replay

Run the historical 11-parameter form on the exact manifest before introducing a
DNN.  Recompute the score independently from saved predictions and report every
process and experiment block.  An archived prediction receipt must close to
relative `1e-8` under its own stored arithmetic.  The independent operator must
agree with it to fixed-sigma prediction RMS at most `1e-3`, maximum at most
`1e-2`, global absolute `q/N` difference at most `0.01`, and per-process
absolute `q/N_block` difference at most `0.02`.

If only rounded publication values can be recovered, matching the quoted
interval is a smoke test, not H1 passage.

### H2 — DNN representation closure

Without using experimental residuals, distill the exact PV17 nonperturbative
PDF, FF, and evolution functions into the current DNN on a preregistered
`(x,z,b,Q,flavor,hadron)` grid.  Evaluate the distilled state through the same
8,059-row operator.  It must pass the H1 prediction and score tolerances.  This
separates DNN representational/adapter correctness from optimization against
data.

### H3 — same-data paired fit

Only after H0--H2 pass, fit the DNN to the exact PV17 likelihood.  Keep every
historical data, theory, cut, transformation, and uncertainty choice fixed;
change only the nonperturbative parametrization and the documented optimizer.
Run sequentially on the one local GPU from the distilled start and at least two
independent feasible starts.  The update ceiling must be generous enough for
the time/convergence condition to govern, and all prior convergence,
positivity, call-accounting, and endpoint-audit rules remain applicable.

For the narrow sanity claim, require global `q/N` no worse than the reproduced
PV17 reference by more than `0.02`, and no process block worse by more than
`0.10` in `q/N_block`.  A lower training score alone is not evidence of a better
extraction: the DNN has far more effective flexibility than the 11-parameter
historical form.

### H4 — TMD and predictive comparison

Freeze a function grid before H3.  Compare the DNN with the historical 200-replica
median and 68% envelope for TMDPDFs, TMDFFs, the nonperturbative evolution
kernel, and the published transverse-momentum moments.  The closure claim
requires at least 90% of supported grid cells inside the historical 68% envelope
and an envelope-standardized RMS at most one.  Report unsupported/extrapolation
cells separately.

Also refit both the historical form and DNN on the same grouped folds, holding
out whole spectra/normalization groups rather than neighboring rows.  This
paired predictive comparison, not the in-sample `q/N` advantage, decides whether
the more flexible fit is genuinely at least as good.  A DNN outside the
historical envelope with better held-out performance is a follow-up scientific
result, not a baseline-closure pass or an automatic failure of the method.

## Fallback rule

If H0 cannot establish a full PV17 final-run identity after public-history and
author-material checks, use MAPTMD22 (`arXiv:2206.07598`) as the primary exact
software baseline and retain PV17 as a provenance-limited heritage challenge.
The public MAPTMD22 report records 2,031 rows, a central-replica `chi2/N` of
1.1051, 260 retained replicas, per-experiment scores, central parameters, and
TMD plots.  Its exact code, data, table, and report revisions must still be
bound before execution; having a richer report does not waive H0.

The fallback is selected by reproducibility, not by whichever target is easier
to outperform.
