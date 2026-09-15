# PV17 exact-data baseline scope correction

## Human clarification

Dustin clarified that the purpose of the historical baseline is not to rerun
or reproduce the PV17 fit.  PV17 supplies an independently published, much
larger data population on which to apply this project's own fitting method.  In
particular, the baseline must use the current N3LL (NNNLL) matched-theory
construction rather than reverting to PV17's NLL calculation.

This decision supersedes the historical-model replay, PV17-function
distillation, final-run-configuration requirement, and historical TMD-envelope
closure gates in the earlier historical closure plan.  The completed source
data audit remains valid and becomes the B0 input gate.

## Scientific question

Can the present matched theory, likelihood machinery, and DNN produce a stable,
well-diagnosed fit on the exact PV17 experimental population?  The experiment is
a data and current-method sanity baseline.  It is not a claim that the old and
new theory definitions are numerically interchangeable.

PV17's reported `chi2/d.o.f. = 1.55 +/- 0.05` and published TMDs remain useful
historical context.  They are not pass thresholds: the new calculation changes
the perturbative treatment, collinear inputs, matching, covariance construction,
and parametrization.  The new fit reports its own `q/N` and does not infer an
effective DNN degree of freedom or p-value.

## Data identity already established

The executable row audit binds 18 source tables at legacy commit
`7df66f4801151ce2384ca211422bdbfc70058832`.  It reconstructs 21,951 candidate
numeric rows, 8,283 rows after the published cuts, and 224 COMPASS spectra.  The
lowest-`PhT` row in each COMPASS spectrum fixes its ratio normalization and is
excluded from the effective count:

```text
8,283 selected raw rows - 224 COMPASS constraints = 8,059 observations
```

All selected central values and primary errors are finite and positive.  The
value-bearing local manifest remains ignored because it contains third-party
measurements; its SHA-256 is
`3b40402fc42e3a7c85a0c3842e97cce3dbdbbb872de7478649dbe8c60e4a83c4`.

## Revised gates

1. **B0 data/metric contract:** finish the modern covariance decision.  Preserve
   the published rows, cuts, and COMPASS ratio observable.  Propagate the common
   COMPASS denominator through a within-spectrum covariance as the primary
   proposal; retain PV17's diagonalized approximation only as a labeled
   sensitivity.  Freeze DY/Z normalization correlations and numerical/theory
   response terms explicitly.
2. **B1 current-theory operator:** generate all observable operators using this
   project's current unprimed N3LL evolution/W, DY NNLO fixed order, implemented
   SIDIS positive-recoil term, matching, collinear inputs, and numerical settings.
   No PV17 kernels or fit configuration are required.
3. **B2 validation:** independently validate stratified predictions, ratio
   transformations, covariance solves, gradients, positivity, row order, CPU/GPU
   replay, and content hashes before optimization.
4. **B3 DNN baseline fit:** run the current model sequentially on the one RTX
   4090 from a transferred start and at least two independent feasible starts.
   Use a time/convergence-governed opportunity with generous count ceilings and
   no inherited 192-update cap.
5. **B4 assessment:** report per-process `q/N`, residuals, nuisance strain,
   convergence and grouped held-out predictions.  Compare the resulting TMDs
   with the current 2,290-point extraction on a fixed supported grid; compare
   with PV17 curves only descriptively.

## Boundary

The new 8,059-observation operator and covariance are separately versioned and
do not alter the frozen 2,290-row study.  Building them is authorized as baseline
infrastructure.  A GPU fit still waits for the B0--B2 data/operator validation
gates, but it does not wait for recovery of the historical PV17 final-run
configuration or predictions.  MAPTMD22 is not needed as a fallback for this
data-baseline question.
