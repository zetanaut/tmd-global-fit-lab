# PV17 current-method B0/B1 preparation outcome

Date: 15 September 2026
Updated: 16 September 2026

## Decision

Do not launch the 8,059-observation GPU fit yet.  The exact-data population,
static metric layer and complete SIDIS point-operator construction now exist,
but current-theory feasibility fails in one localized channel and the D0
Run-II normalized observable cannot yet be physically evaluated with a
source-correct operator and exact likelihood.

The targeted HERMES `K-` diagnostic and independent D0 contract audit are now
complete.  They localize, rather than remove, both blockers: the kaon failure is
a stable central matching cancellation, while D0 has exact compile actions but
no bound physical denominator/provider or normalized covariance.  More
optimization of the existing DNN is not a substitute for either requirement.

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
and [endpoint feasibility](../analysis/historical-closure-baseline-20260915/sidis-endpoint-feasibility.json),
[K-minus sign diagnostic](../analysis/historical-closure-baseline-20260915/hermes-kminus-sign-diagnostic.json),
and [D0 contract audit](../analysis/historical-closure-baseline-20260915/d0-runii-contract-audit.json)
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
row fails.

The completed component audit covers the 19-row union implicated by the fixed,
Gaussian or endpoint results.  In 17, switched `ASY` exceeds `FO_T + FO_L`.
Direct component reconstruction closes to `4.45e-16`, the sign pattern is
unchanged under refined quadrature and a narrow-bin limit, and all 53,760 signed
channels follow the encoded charged-kaon/isospin map.  The union is eight
full-additive plus 11 transition rows and ten proton plus nine deuteron rows.
This excludes serialization, coarse integration and a simple map coding error;
the open review is the scientific validity of this point-observable matching
and kaon collinear input in the affected corner.

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

The completed contract audit matches all 23 source rows and maps the retained
eight to bins 0--7.  The exact-bin numerator actions, full-support denominator
dependency and no-subset-renormalization rule are already specified.  The gap
is physical execution and likelihood closure: the governed registry revision,
hash-bound numerator/inclusive-NNLO-denominator provider, QED convention and
normalized unfolding covariance are still missing.

## Required next gates

1. Compare the implicated HERMES `K-` corner with a qualified exact-bin
   implementation and challenge the kaon collinear input; require a
   source-backed positive central observable before fitting.
2. Revise the D0 registry to the source `40 < Q < 200 GeV` support, bind and
   converge the numerator/denominator provider with explicit QED conventions,
   and recover or approve an approximation to the normalized covariance.
3. Only after 1--2 pass, assemble the ordered 8,059-row prediction and run
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
