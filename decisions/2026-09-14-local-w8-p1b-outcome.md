# Local width-8 P1B: completed optimization opportunity, convergence not reached

Run `continuation-w8-p1b-local-a01-20d406220a8a` completed on the local RTX 4090
at 2026-09-14 02:34:22 UTC (13 September, 22:34:22 EDT). It executed the
[preregistered P1B plan](2026-09-13-local-w8-p1b-plan.md) from the audited
81-update P1 restart, preserving the L-BFGS history at mu = 1e-6.

The [immutable result](../results/continuation-w8-p1b-local-a01/continuation-w8-p1b-local-a01-20d406220a8a.json)
contains the original source, trial, claim, parent, endpoint and file hashes.
The [publication verification](../analysis/p1b-local-20260914/publication-verification.json)
records saved-array checks and the separate archive download verification.

## Execution and progress

| Quantity | This segment | Cumulative portable P1 trajectory |
|---|---:|---:|
| Accepted updates | 96 | 177 |
| Charged forwards | 793 | 1,438 |
| Charged VJPs | 105 | 205 |
| Infeasible trials | 579 | 984 |
| Line-search rejections | 585 | 1,002 |
| Recorded model-window seconds | 2,061.045 | 6,556.645 |

q/N fell from 16.69970587088408 to 16.448895619388466, an improvement of
0.250810251495615. These cumulative counts belong to the portable P1 trajectory;
they do not include the separately recorded historical P0 update allocation.

The worker stopped with `phase_schedule_complete` after the requested 96 new
accepted updates. Worker and audit exit codes are zero; the supervisor recorded
no stop reason and cleanup confirms the worker was reaped. The run reached its
update target within the 13,200-second model window. Its sampled peak owned GPU
memory was 9.152 GiB, peak RSS 1.436 GiB, and minimum available host memory
14.928 GiB. No time, memory or monitoring stop was recorded.

## Endpoint validity and convergence

The audit passes on all 2,290 saved predictions, with no zero or negative values
and minimum T/sigma = 4.522141073536087e-5. The raw gradient maximum is
0.2206397440562665; the penalized gradient maximum is 0.2206201820676685.

| Convergence quantity | Earlier final window | Latest final window | Required maximum |
|---|---:|---:|---:|
| q/N range | 0.012277074329425375 | 0.003086578420610664 | 0.0001 |
| Fixed-sigma prediction-span RMS | 0.09523510177383324 | 0.01877409534905285 | 0.001 |
| Fixed-sigma prediction-span maximum | 0.7414107206667664 | 0.11987727625538724 | 0.01 |
| Terminal penalized-gradient maximum | 0.3231692580896163 | 0.2206201820676685 | 0.00001 |

Both ten-update windows at unchanged mu fail every numerical convergence
threshold. The 188 high-COMPASS diagnostic rows remain underpredicted, with raw
residual RMS 7.979325636502012 fixed sigma. The saved DY profile closes to
8.185452315956354e-12 absolute; experimental and numerical nuisance penalties
are 184.8775163743569 and 14.093398301859983. Full named nuisance and process
diagnostics are retained in the result.

## Publication checks and interpretation

Publication QA reproduced the saved endpoint audit within 1e-10 absolute,
verified all 96 accepted checkpoint scores and feasibility, checked the parent
parameter vector and replay tolerances, validated the final optimizer state,
and reproduced both convergence windows without model calls. The archive
preserves all 210 original run files. Its separate download matches the uploaded
SHA-256 and every archived file matches the original inventory.

The result collector now handles `p1-resume-v2` cumulative accounting using the
same reconciliation as V1. This includes the final raw-gradient evaluation:
the terminal dispatch ledger has one forward and one VJP beyond the final
accepted checkpoint. The recorded run source remains `c1f4dc3`; this publication
fix changes no historical run files or result records.

The extended opportunity produced further improvement and ended before
convergence. The large number of infeasible candidates warrants review, but
does not by itself identify the cause or prove poor conditioning. The next
action remains the explicit progress/feasibility/conditioning review specified
by the P1B plan. This outcome grants no new run or automatic continuation and
does not select an architecture from unequal optimization opportunities.
