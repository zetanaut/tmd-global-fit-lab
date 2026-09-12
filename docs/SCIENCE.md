# Scientific contract

## Objective and scope

Fit direct unpolarized transverse-momentum-dependent boundaries in b space:
incoming TMDPDFs, outgoing TMDFFs, and one universal Collins–Soper (CS) kernel.
DY uses two incoming legs; SIDIS uses an incoming and an outgoing leg. Boundaries
depend on b, the relevant longitudinal fraction, flavor and (outgoing) hadron,
not Q. Two-leg nonperturbative evolution is `exp(2*K_NP(b)*log(Q/3 GeV))`.
Conventions retained by the source analysis include `a_s=alpha_s/(4*pi)` and
`K=-2D`. b is in GeV^-1; Q is in GeV.

All 2,290 observations remain, in their exact saved order: 743 DY, 344 HERMES,
1,203 COMPASS. Numerical nodes and alternative quadratures are not additional
experimental observations. No synthetic predictions are added as measurements.

## Frozen prescription

- DY: `T = FO + f_DY*(W-ASY)`, retained quintic switching from qT/Q 0.15 to 0.30.
- SIDIS: `T = f*W + X*(FO-f*ASY)`, with
  `f=exp[-(qT/(0.34*Q))^8]` and `X=1-exp[-(qT/(2/3 GeV))^4]`.
- Retained b-star maximum 0.7 GeV^-1 and p=16 small-b treatment on the DY branch.
- Unprimed N3LL evolution/W; DY retains NNLO fixed order. SIDIS's implemented
  positive-recoil O(alpha_s) term is LO at positive recoil. Do not label the
  complete joint observable uniformly N3LL+NNLO.

These are definitions of this controlled study, not new evaluations of the
perturbative prescription. The released signed operators already contain the
fixed inputs, matching/recoil terms, flavor maps, measures, normalization and
bin integration. Do not add a second Y term, change switches, rebuild PDFs/FFs,
or alter W/ASY inconsistently. Physics sensitivity is a separately approved branch.

For each measured row the exact portable contraction is
`(sum_e signed_weight_e*exp(log_F_in+log_F_leg2+2*K_NP*log(Q/3))
  + fixed_numerator)/denominator/density_volume`.
The signed weights must retain signs and all channels; they are not a positive
probability sample. Input lookup/grouping can reuse identical integer
point/species keys without merging merely equal floating coordinates.

## Model baseline

Nested-FiLM has 10 incoming and 30 outgoing species, shared flavor embeddings
and an outgoing hadron embedding. Conditional width and shape heads act on a
Gaussian-damped boundary:
`log_F=-softplus(raw_width_species+delta_width(condition))*b^2
       + u*shape_head(FiLM(radial_features,condition))`, `u=b^2/(1+b^2)`.
This gives `F(0)=1`; the shared saturating CS module gives `K_NP(0)=0`.
It has no universal shape/CS amplitude cap or required boundary monotonicity.
Positive b-space factors do not guarantee positive Fourier-Bessel observables.

Widths 8/16/24 at depth 1 have 1,570/2,882/4,706 trainable parameters; the shared
CS module has 73 in every case. The parameter order/schema is part of checkpoint
identity. Initializations must preserve or report functional differences and
feasibility-search cost; paired seeds are not replicas or posterior samples.

## Likelihood and admissibility

Fixed `C_eff=C+U*U^T`. C retains full accepted experimental covariance; U is the
separate numerical response. Data, C, U, and the old t0 normalization reference
are immutable within this study. No prediction-dependent covariance, clipping,
row removal, diagonal approximation, error inflation or in-loop t0 refresh.

`q=(d-T)^T*C_eff^-1*(d-T)`; report `q/N`, N=2290. This is NOT chi-square per
effective degree of freedom and supplies no calibrated goodness-of-fit p-value.
Raw residuals are `(d-T)/sqrt(diag(C_eff))`; they remain correlated.

Optimize `q/(2N)-(mu/N)*sum(log(T/sigma-1e-8))`, only if every raw complete
measured prediction satisfies `T/sigma>1e-8`. Do not confuse the optimization
objective (including the barrier and factor 1/2) with the reported q/N. A finite
barrier endpoint is not an exact constrained optimum or continuum positivity.

For DY use `A=[S,U_DY]` and `C_DY,eff=diag(D)+A*A^T`. Solve
`eta=(I+A^T*D^-1*A)^-1*A^T*D^-1*(d-T)`. The shift A*eta is ADDED to predictions.
Adjusted quadratic plus nuisance penalty must close to the fixed metric within
1e-7 absolute. Keep experimental/numerical penalties separate. E605/E772 pulls
are in existing conditional prior units tied to old t0, not multiplicative
changes to the current endpoint. Do not invent an analogous SIDIS decomposition.

The 188-row high-COMPASS diagnostic uses the saved conservative outer-support
group entirely at qT/Q >=0.34. It is neither a data cut nor a quadrature-weight
fraction. Parent prediction changes and raw residual RMS are different fields.

## Comparison and conclusions

An architecture advantage needs repeatable gains at comparable optimization
maturity, with understood feasibility, residuals, nuisance strain and cost.
Require two consecutive ten-update intervals at unchanged mu (21 states):
q/N range <=1e-4, fixed-sigma prediction span RMS <=1e-3 and max <=1e-2, and
terminal penalized-gradient max <=1e-5. Record raw gradients too; their norm is
parameterization-dependent and not comparable as an invariant capacity measure.

Separate optimization nonuniqueness, architecture effects, experimental replicas,
theory/PDF/FF variation, and numerical/surrogate error. This study does not yet
calibrate any uncertainty decomposition. Persistent deficits support targeted
future questions, not an irreducible floor, dataset invalidation or a proof
against universal CS. No production selection, replicas, BNN or public-science
release is authorized by completing one matrix.

