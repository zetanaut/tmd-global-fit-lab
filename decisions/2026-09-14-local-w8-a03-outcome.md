# Width-8 repaired continuation: valid, time-censored, still improving

## Immutable evidence and three verdicts

Run `continuation-w8-feasibility-2h-local-a03-52265fbd3eb9`, source
`0dd91545de6d53acf0777b9eceabd2d768d8cf5d`, advanced from 252 to 423 cumulative
accepted updates on the single local RTX 4090. Its
[result record](../results/continuation-w8-feasibility-2h-local-a03/continuation-w8-feasibility-2h-local-a03-52265fbd3eb9.json)
binds the full archive, claim, endpoint and dispatch ledger.

- Execution: partial because `endpoint_time_reserve` ended the optimization
  segment, not because of a crash, the historical 192-update cap or convergence.
  Worker exit 2 is the partial-status convention; supervisor stop reason is null,
  the worker was reaped, and saved-array audit exited 0.
- Endpoint: all 2290 finite and positive; minimum T/sigma
  0.00018796783676773874; q/N 16.11080233178303. Raw and penalized gradients are
  present. Endpoint SHA256 is
  `b5446bbc8598bdb73c5d079df101c9eef9ba76846bbe098801e361b5759b4910`.
- Interpretation: both unchanged convergence windows fail. Terminal penalized
  gradient maximum is 0.09609654877983605 versus 1e-5; the last window's q/N
  range is 0.04471156492413897 versus 1e-4, prediction-span RMS 0.21719953823553442
  versus 1e-3, and maximum 2.066315558311967 versus 1e-2. No production selection,
  architecture advantage, calibrated goodness-of-fit or irreducible floor follows.

The new segment charged 1966 forwards, 202 VJPs, 171 accepted updates and
4807.321720642969 model-window seconds. The cumulative ledger is 4315 forwards,
485 VJPs, 423 accepted updates and 13570.07446063764 model seconds. This includes
the final raw-gradient call and the earlier failed dispatch. A01 plus A03 used
7013.429405350238 seconds of the original 7200-second opportunity, including
setup/replay. The residual reserve is not an automatic new grant.

## What changed during optimization

q/N fell from 16.411446133424036 to 16.11080233178303 after repair; over the
original opportunity starting at update 177 it fell by 2.0554% from
16.448895619388466. The five complete 32-update blocks improved q/N by
0.0068835, 0.0366589, 0.0630986, 0.0732548 and 0.0760331. Progress per 100
charged forwards increased from 0.001503 in the first block to 0.023040 in the
last complete block. The final 11 updates added 0.04471485 improvement; they
are not a sixth equal-sized block. This supports another bounded opportunity,
not a linear extrapolation of convergence time.

There were 1518 observable-positivity rejections, 28 Armijo rejections and
16 typed numerical-domain rejections. All 1518 positivity-rejected candidates
violated at least one E288 row; other rows could also fail. Positivity failures
are 97.18% of rejections and 77.21% of all charged forwards, not a measured
wall-time fraction. No numerical-domain rejection occurred after new update 56.
These are concrete feasibility/step-geometry diagnostics, not an exact Hessian
condition number. Raw and penalized terminal gradient maxima are both about
0.096; their difference maximum is only 5.9214e-6.

## Saved-only COMPASS decomposition

The reproducible [review JSON](../analysis/w8-a03-saved-review-20260914/review.json)
was generated with [review_w8_saved.py](../scripts/review_w8_saved.py). It verified
all 371 archive files against the downloaded archive, result record and local
run, and all 4600 frozen input files. It dispatches zero model evaluations.

The fixed covariance has exactly zero cross-block entries for DY, HERMES,
COMPASS, and the high-COMPASS subset versus its complement. Independent block
quadratics are therefore meaningful here. DY q/743 improved 8.689883 to
8.293976, HERMES q/344 5.352868 to 4.973800, and COMPASS q/1203 24.342678 to
24.123297. Per-block normalizations are not additive q/N contributions.
DY raw residual RMS worsened slightly while its covariance-aware score and
adjusted residual RMS improved; experimental nuisance penalty increased from
187.7053 to 197.8863, so not every residual diagnostic improves uniformly.

The 188 high-COMPASS rows remain all underpredicted and account for 32.4413% of
final q. Their q changed only from 11969.5808857 to 11968.8039242. Subtracting
the exact fixed matched contribution `fixed_numerator/denominator/density_volume`
from each saved prediction gives a final trainable-contribution RMS of
0.01874093 fixed sigma, compared with residual RMS 7.978963. In 160 of 188 rows
the absolute trainable contribution is below 0.01 fixed sigma. The fixed
matched contribution RMS is 4.293147 fixed sigma. Prediction-change RMS over
the repaired segment is only 0.000790053 fixed sigma.

This is endpoint amplitude decomposition, NOT a Jacobian measurement, a feasible
response bound, or a proof that a larger trainable contribution cannot be reached.
The fixed term includes the prescribed matching subtraction; do not call it FO
alone. A zero subtraction result at saved precision is not structural independence.
The evidence motivates a later targeted sensitivity test if needed; no data cut,
covariance change or physics modification is warranted by this result.

## Publication and next decision

The immutable [archive](https://github.com/zetanaut/tmd-global-fit-lab/releases/download/run-continuation-w8-feasibility-2h-local-a03-52265fbd3eb9/continuation-w8-feasibility-2h-local-a03-52265fbd3eb9.tar.gz)
contains 10489941 bytes and SHA256
`bcb743246008be76e3bef8cfc8c6e4b9618ed0c25152122ca303154bae33f75e`.
It was downloaded separately and verified before collecting the result. The
run directory has no symlinks; a credential-pattern scan of non-NPZ files found
no matches. No historical asset or result was overwritten.

On 14 September 2026 Dustin approved the reviewed plan: one further two-hour
continuation from 423, unchanged repaired optimizer/history and scientific
contract, plus saved-only high-COMPASS investigation. Register a new exact trial
and cumulative allowance before claiming or launching. If progress per call
persistently deteriorates while gradients stay large, propose a separately
controlled equal-budget optimizer comparison from one checkpoint; no automatic
switch or successor is granted. Model sensitivity probes are not hidden inside
this saved-only review and require their own bounded specification if needed.
