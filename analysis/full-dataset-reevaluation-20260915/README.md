# Full COMPASS source and theory-validity reevaluation — 15 September 2026

## Verdict

The concern about using only 2,290 points was scientifically justified, but a
raw point-count expansion is not the remedy.  In the official COMPASS release
audited here, the current 1,203-row selection already contains **every row whose
entire conservative rectangular bin envelope lies at or below
`qT/Q = 0.30`**.  The 3,461 additional rows contain no pure-TMD-core bins and no
bins wholly below 0.30.

At the saved width-8 update-658 endpoint, the current COMPASS score is instead
dominated by rows that the candidate role policy calls fixed-order validation:
278 such rows contribute 17,408.25 to the COMPASS quadratic form, or 60.2% of
the entire COMPASS contribution.  The 188-row high-COMPASS diagnostic is wholly
inside that group and contributes 11,967.97.  This makes continued optimization
of the unchanged likelihood a poor next scientific use of the GPU: much of the
objective pressure is outside the intended primary DNN-information region.

The next sound move is a new, explicitly versioned likelihood study.  It should
retain the existing 2,290-row result as the control; build exact constrained-bin
operators; derive correlated SIDIS theory responses from matching, scale,
PDF/FF, and numerical variations; and only then compare a core, a matched
extension, and a fixed-order validation tail.  A transferred scalar error law
may be included as a stress test, but must not be adopted merely because it
lowers `q/N`.

## Source census

This audit reads all 162 YAML tables in HEPData record
[`ins1624692` version 1](https://www.hepdata.net/record/ins1624692?version=1),
DOI `10.17182/hepdata.83542.v1`.  The 4,664 primary multiplicity rows split
evenly into 2,332 positive- and 2,332 negative-hadron rows.

The support diagnostic uses

`qT/Q = sqrt(PhT2) / (z sqrt(Q2))`.

Minima and maxima are computed over the Cartesian box formed by the published
`PhT2`, `z`, and `Q2` edges.  These are conservative bounding-box extrema, not
an event-level reconstruction of the correlated physical support.  The exact
constrained support still requires the experiment's `y` and `W` selection,
beam/target convention, and boundary handling inside each operator.

| Population | Rows | Pure TMD (`rmax <= 0.15`) | Matched/mixed | Pure fixed-order validation (`rmin >= 0.30`) |
|---|---:|---:|---:|---:|
| Full official COMPASS release | 4,664 | 12 | 1,084 | 3,568 |
| Current likelihood selection | 1,203 | 12 | 913 | 278 |
| Additional public rows | 3,461 | 0 | 171 | 3,290 |

Full-support coverage of the current selection is:

| Maximum `qT/Q` | All public rows | Currently selected | Additional |
|---:|---:|---:|---:|
| 0.15 | 12 | 12 | 0 |
| 0.20 | 68 | 68 | 0 |
| 0.25 | 118 | 118 | 0 |
| 0.30 | 202 | 202 | 0 |
| 0.34 | 282 | 272 | 10 |

Thus, the 1,203-row legacy selection is not a clean TMD-core selection—it
contains a large transition and fixed-order tail—but it is also not omitting a
large reservoir of bins wholly inside the candidate `r <= 0.30` matched domain.

The 8,059-point count in
[`arXiv:1703.10157`](https://arxiv.org/abs/1703.10157) is not directly
comparable.  It used a different data construction and observable treatment;
this audit is specifically of the later 4,664-row official COMPASS release and
does not reconstruct the paper's 6,252-point COMPASS input or its 1,514-point
HERMES input.  A corresponding HERMES source census remains necessary before
calling a future likelihood globally complete.

## What controls the current score

The frozen metric and saved endpoint reproduce `q/N = 15.91920723937985`.
COMPASS is a diagonal `stat^2 + sys^2` block with no cross-process covariance.

| Candidate support role | Rows | Quadratic contribution | Contribution/row |
|---|---:|---:|---:|
| Pure TMD core | 12 | 35.36 | 2.95 |
| Matched/mixed | 913 | 11,470.32 | 12.56 |
| Pure fixed-order validation | 278 | 17,408.25 | 62.62 |
| All COMPASS | 1,203 | 28,913.93 | 24.03 |

These are decompositions of the fixed historical metric.  The role labels come
from the candidate `0.15/0.30` support policy; they do not retroactively change
the frozen central matching prescription.

## Direct error-envelope stress test

For comparison only, the audit transfers equations (52)–(56) of
[`arXiv:2608.27907`](https://arxiv.org/abs/2608.27907):

`sigma_fact = abs(data) * 0.50 * S((r - 0.10)/0.05) * (r/0.10)^2`,

where `S` is the cubic smoothstep.  That paper calibrated this phenomenological
law for a leading-power DY `W`-term stability study through representative
`qT/Q <= 0.20`; it is not a calibrated uncertainty for bin-integrated SIDIS or
for this matched central prediction.  The paper itself treats `delta > 3` as an
exclusion trigger in its staged test.

Applied mechanically at the representative value to all 4,664 COMPASS rows,
4,351 rows exceed `delta = 3`.  The median relative theory error is 43.93
(4,393%).  Under a diagonal independent-error interpretation, the sum of the
experimental-to-effective variance weights is only 33.46 across all 4,664
rows.  The 3,461 newly considered rows add just 0.097 to that sum.  Using the
conservative support maximum is still more extreme: the full-release weight sum
is 1.96.

That calculation demonstrates why “keep every point and add this error” is not
automatically more informative than a cut.  Far outside the calibrated range it
retains rows nominally while giving them essentially no statistical leverage.

The saved endpoint sensitivity is:

| Theory covariance stress test on selected COMPASS | `q/N` | COMPASS signed contribution | High-188 signed contribution | Independent variance-weight sum |
|---|---:|---:|---:|---:|
| Frozen experimental covariance | 15.919 | 28,913.93 | 11,967.97 | — |
| Paper law at representative `r`, diagonal | 3.333 | 92.52 | 0.37 | 33.36 |
| Paper law at representative `r`, one correlated mode/table | 4.950 | 3,794.95 | -493.67 | not applicable |
| Paper law at support maximum, diagonal | 3.295 | 4.76 | 0.09 | 1.93 |
| Paper law at support maximum, one correlated mode/table | 5.005 | 3,919.33 | -415.07 | not applicable |

The negative high-188 entries in the fully correlated cases are signed
subset contributions `sum_i residual_i (C^-1 residual)_i`; a correlated subset
is not a standalone chi-squared and need not be positive.  The full quadratic
forms remain positive.

The apparent fall to `q/N ~= 3.3` in the diagonal cases is not evidence that the
model suddenly fits COMPASS.  It occurs because the transferred uncertainties
nearly remove COMPASS from the score; DY plus HERMES alone already contribute
`q/N = 3.293` when still divided by all 2,290 rows.  Comparing `q/N` across
different covariances also omits the covariance normalization and rests on an
uncalibrated theory-error model.  The machine-readable result records the
log-determinant sensitivity as well.

## Recommended likelihood-v2 sequence

1. Reconstruct the constrained support for all 4,664 rows and validate it
   against the source selection.  The bounding-box census is the conservative
   screening result, not the final event-support classification.
2. Keep the 12 bounding-box pure-core rows as the strictest anchor and test
   center-based and constrained-support core definitions without changing them
   after viewing fit quality.
3. Prioritize exact operators for the 171 additional mixed-support rows.  They
   are the only new rows with any conservative support below 0.30.  Do not spend
   initial GPU time fitting the 3,290 wholly high-recoil additions.
4. For the matched sector, generate fixed response vectors from preregistered
   matching-boundary, renormalization/factorization-scale, perturbative-order,
   PDF, FF, and numerical variations.  Construct and test both correlated and
   residual diagonal components.  Do not tune their magnitude to force
   `q/N ~= 1`.
5. Treat the pure fixed-order sector as validation-only until its central
   fixed-order prediction and uncertainty are independently validated.  It must
   not masquerade as thousands of independent DNN-shape constraints.
6. Compare three likelihoods from common starts: strict core, core plus matched
   response covariance, and the same fit evaluated on the fixed-order tail.
   Report parameter/function shifts and predictive stability, not only `q/N`.
7. Only after the likelihood-v2 CPU closure and derivative gates pass should a
   new one-GPU fit be preregistered.  Continuing the unchanged update-658
   trajectory is retained as a control, not the default next run.

No new-row prediction, fit, covariance promotion, or modification of the frozen
2,290-row likelihood is authorized by this diagnostic.

## Reproducibility

[`summary.json`](summary.json) contains the complete aggregate census, input
hashes, selected-source/support closure, endpoint scores, covariance definitions,
and interpretation guards.  It was generated by
[`scripts/reevaluate_full_compass.py`](../../scripts/reevaluate_full_compass.py)
from the official HEPData v1 YAML archive, the frozen public input bundle, the
selected COMPASS adapter-plan rows, and the saved A04 endpoint.  No raw HEPData
rows are redistributed in this repository.
