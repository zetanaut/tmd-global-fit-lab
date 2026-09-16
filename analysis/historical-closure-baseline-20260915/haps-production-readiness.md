# HAPS-KaFF1.0 production-readiness gate

Date: 2026-09-16

## Finding

The all-19-row diagnostic shows that HAPS-KaFF1.0 removes the current central
K− sign obstruction: all 19 implicated rows are positive, while NNFF10 is
negative in 16/19.  This is a valid theory-input sensitivity result, but it is
not yet a production input choice.

The HAPS paper explicitly states that the extraction combines SIA data with
charge-separated SIDIS multiplicities from HERMES and COMPASS:

<https://arxiv.org/abs/2606.16754>

Our proposed likelihood contains HERMES K− observations.  Consequently, direct
use of HAPS central values with those observations would reuse information from
the fitted data set.  The current HAPS delivery also has no verified grid
redistribution license in its inspected repository metadata, and its replica
ensemble has not been calibrated into our likelihood covariance model.

## Gate status

| Gate | Status | Required closure |
|---|---|---|
| Central K− positivity | PASS (conditional) | Retain diagnostic receipt and matching controls |
| HERMES independence | BLOCKED | Obtain a HERMES-excluded/leave-one-out HAPS refit, or remove HERMES from the likelihood |
| Covariance/replica treatment | BLOCKED | Define replica propagation and cross-covariance policy |
| Redistribution/license | BLOCKED | Obtain explicit permission or use an independently redistributable FF |
| Production operators | NOT STARTED | Generate only after the preceding gates close |

## Scientifically sound production route

1. Do **not** promote the current HAPS tables into the HERMES fit.
2. Request or produce a HERMES-excluded HAPS kaon fit (SIA + COMPASS only),
   with the exact runcard, data list, covariance, and redistributable grid.
3. Validate that independent grid on all 19 rows, including Gaussian and
   endpoint controls and both matching prescriptions.
4. Propagate its replica ensemble as a clearly separated FF uncertainty, with
   an explicit overlap policy for COMPASS.
5. Only then generate versioned HAPS operators and run a bounded pilot before
   any global optimization.

Until step 2 is available, the production-safe choices are to retain NNFF10
with the K− obstruction reported as a failed central-theory gate, or to source
another kaon FF determination independent of HERMES.
