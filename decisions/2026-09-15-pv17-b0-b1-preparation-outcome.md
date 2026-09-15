# PV17 current-method B0/B1 preparation outcome

Date: 15 September 2026

## Decision

Do not launch the 8,059-observation GPU fit yet.  The exact-data population,
static metric layer and complete SIDIS point-operator construction now exist,
but current-theory feasibility fails in one localized channel and the D0
Run-II normalized observable is not yet defined by a source-correct operator.

The next work is a targeted HERMES `K-` theory diagnostic plus an independent
D0 normalized numerator/denominator implementation.  More optimization of the
existing DNN is not a substitute for either requirement.

## What closed

- The pinned PV17 tables close 21,951 candidate rows to 8,283 selected raw rows
  and 8,059 scored observations after treating 224 COMPASS lowest-`PhT`
  denominators as constraints.
- Metric v2 builds the ordered static data/error layer, 224 shared COMPASS
  denominator responses and seven absolute DY/Z `t0` normalization patterns.
  All static population, marginal-variance and conditioning invariants pass.
- Current operator coverage reuses 285 DY/Z operators with explicit adapters.
- All 7,990 raw SIDIS point operators are constructed in 232 resumable shards.
  Direct Gaussian recovery is below `5.33e-15` and PyTorch replay below
  `1.25e-14`.  No optimizer or GPU was used for this construction.
- The point-operator pilot closes the observable convention and confirms that a
  fixed-order-only COMPASS numerator can remain DNN-coupled through its shared
  denominator; the directional AD/finite-difference error is `1.86e-11`.

The primary machine-readable records are the
[metric](../analysis/historical-closure-baseline-20260915/metric-contract-v2.json),
[coverage](../analysis/historical-closure-baseline-20260915/operator-coverage-v2.json),
[domain](../analysis/historical-closure-baseline-20260915/sidis-domain.json),
[pilot](../analysis/historical-closure-baseline-20260915/sidis-point-pilot-v2.json),
[SIDIS campaign](../analysis/historical-closure-baseline-20260915/sidis-point-operators.json),
and [endpoint feasibility](../analysis/historical-closure-baseline-20260915/sidis-endpoint-feasibility.json)
receipts.

## Blocker 1: HERMES negative-kaon feasibility

The Gaussian control produces 16 nonpositive HERMES `K-` multiplicities.  The
independently trained width-8 endpoint at 658 cumulative accepted updates also
produces 16: 15 rows overlap, one Gaussian failure is recovered and one new row
becomes negative.  The endpoint minimum is `-0.8069826550`.  The failures split
into seven full-additive and nine transition rows, eight proton and eight
deuteron.  All COMPASS raw predictions and all `K+`, `pi-` and `pi+` channels
are positive.

This is not an operator serialization error: Gaussian direct calculation and
operator replay agree at machine precision, and the failure persists under a
trained boundary.  Seventeen HERMES `K-` rows already have a nonpositive stored
matched fixed contribution (`FO - switched ASY`, including the longitudinal
piece); the W term can rescue some but not all and can change which marginal
row fails.  That pattern makes a component/flavor/matching audit mandatory
before data fitting.

The transferred endpoint was trained on the existing 2,290-observation
likelihood.  Its replay is a feasibility probe, not a PV17 fit or a statement
about the quality of the HERMES data.

## Blocker 2: D0 Run-II observable definition

The eight D0 Run-II rows are a published normalized shape.  They must be
predicted as a current-theory bin numerator divided by the current-theory full
fiducial normalization on `40 < Q < 200 GeV` support with inclusive rapidity.
The inherited prepared card uses `70 < Q < 110 GeV`, and PV17 converted the
shape with a theory-derived `255.8 pb` factor.  Neither is the required current
observable.  Metric v2 therefore keeps the raw normalized data and deliberately
leaves these rows blocked rather than manufacturing absolute operators.

## Required next gates

1. On every implicated HERMES `K-` point, expose `FO_T`, `FO_L`, switched
   `ASY`, Gaussian W and trained-endpoint W separately.  Independently check
   charged-kaon FF/flavor mapping, charge conjugation, target isospin,
   threshold selection and point-versus-shrunk-bin agreement.
2. Classify the sign failure as an implementation defect, an invalid use of the
   regional theory, or a limitation of the additive matching/collinear inputs.
   Require finite positive predictions under controlled theory-only probes.
3. Implement and review the D0 normalized numerator and fiducial denominator,
   then bind a feasible current-theory `t0`.
4. Only after 1--3 pass, assemble the ordered 8,059-row prediction and run
   transformed-observable, covariance-action, gradient, positivity and CPU/GPU
   replay checks.  A sequential single-RTX-4090 fit may then be preregistered
   with a time/convergence-controlled update policy, not the obsolete 192 cap.

Adding a theory-error response can be scientifically appropriate for supported
power-correction uncertainty.  It cannot turn a negative central multiplicity
into a physical prediction or supply the missing D0 normalization denominator.

## Scope

This decision does not reproduce PV17's NLL fit, alter any frozen 2,290-row
result, modify the read-only foundation, select a DNN architecture, or authorize
new GPU optimization.  The available SIDIS path is the conditional regional
unprimed-N3LL-W plus NLO-recoil/NLO-DIS implementation; it remains explicitly
heavy-threshold-incomplete and production-unauthorized.
