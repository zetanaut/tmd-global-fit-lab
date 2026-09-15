# Width-8 second window: valid endpoint, line-search exhausted

## Execution and endpoint verdicts

Run `continuation-w8-feasibility-2h-local-a04-12ba1d1a3371`, source
`e2a6945296201369ebffa9a633f60a29c8bf9945`, continued the audited 423-update
state on the single RTX 4090. Its immutable [result record](../results/continuation-w8-feasibility-2h-local-a04/continuation-w8-feasibility-2h-local-a04-12ba1d1a3371.json)
and [archive](https://github.com/zetanaut/tmd-global-fit-lab/releases/download/run-continuation-w8-feasibility-2h-local-a04-12ba1d1a3371/continuation-w8-feasibility-2h-local-a04-12ba1d1a3371.tar.gz)
are published and download-verified.

- The run accepted **235 new updates**, reaching **658 cumulative**.
- q/N improved from 16.11080233178303 to **15.91920723937984**, a further
  1.1892% reduction.
- The worker stopped at `line_search_exhausted_32_trials` while proposing update
  659. This is a bounded optimizer failure, not a crash, GPU loss or resource
  exhaustion. The service's exit-2/partial status is retained.
- Saved-array audit passed: all 2,290 endpoint predictions are finite and
  positive; minimum T/sigma is 1.1830791479577918e-6. Endpoint SHA256 is
  `619687b78a2aa214ef8d9af36d1d09a940fda9a75d3759d93bffaaddcf010869`.
- The terminal raw-gradient call did not run after line-search exhaustion, so
  raw-gradient and raw/penalized-gradient-difference fields are explicitly
  missing. Penalized-gradient maximum is 0.25892813965529077. Convergence is
  therefore not established.

The run used 6444.63 seconds of model-window time before the final saved-only
audit, leaving some registered segment time unused because the line search had
already failed. Cumulative charges are 658 accepted updates, 7058 forwards,
743 full/VJP calls, 5387 infeasible trials and 5561 line-search rejections.
Candidate verdicts are 235 Armijo passes, 21 Armijo rejections, 2134 completed
positivity failures and 90 typed numerical-domain rejections. The last accepted
step used alpha 9.313225746154785e-10; the next 32 attempts shrank to
4.656612873077393e-10 and remained infeasible after several domain rejections.

## Learning behavior

The first complete 32-update block improved q/N by 0.0914594 (0.0328991 per
100 forwards). The next blocks yielded 0.0229766, 0.0070937, 0.0003726,
0.0432666, 0.0208020 and 0.0015807. Thus the second window contains real
continued improvement but a strongly deteriorating and intermittent rate; it
does not support another unchanged continuation as the default action.

The final 11-update partial interval added 0.0040436 and is not compared with
complete 32-update blocks. The unchanged plateau windows fail: the last-window
gradient maximum is 0.2589281, q/N range 0.0040436, prediction-span RMS
0.0380623 and maximum 0.291398, all above registered tolerances.

## Residual and high-COMPASS review

The [saved-only A04 review](../analysis/w8-a04-saved-review-20260915/review.json)
verified the downloaded archive and frozen inputs without model evaluations.
The 188 high-COMPASS rows remain all underpredicted, with residual RMS
7.9786854 and 32.8295% of final q. Their normalized prediction change across
A04 has RMS 0.0011426; 160 rows still have absolute trainable endpoint
contribution below 0.01 fixed sigma. This repeats the earlier conclusion:
the block is nearly static along this trajectory, but the decomposition is not
a Jacobian, a feasible-response bound or proof of an irreducible physics floor.

Other diagnostics improved but not uniformly. Final DY adjusted RMS is 2.04916,
experimental nuisance penalty 191.41483 and numerical nuisance penalty 3.80833.
The endpoint remains an unconverged, time/line-search-censored optimization
state, not a production fit or calibrated goodness-of-fit result.

## Scientific decision

A04 answers the immediate question: **additional unchanged time was informative,
but the trajectory now encounters a reproducible positivity/domain line-search
bottleneck before convergence.** Do not launch another unchanged continuation
automatically. The next experiment should be a separately preregistered,
equal-budget optimizer/feasibility comparison from the audited update-658 state,
with the current unit-backtracking trajectory retained as the control. Any
candidate-step remedy must preserve all 2,290 rows, fixed covariance, physics,
barrier and convergence criteria and must be tested on matched budgets. No
downweighting, clipping, error inflation or architecture conclusion follows.

Archive SHA256: `d57b1aea6cb72257839cf38aeb1031a0860fe1877d7cc3ce316a722b6942a421`.
