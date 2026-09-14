# Sustained width-16 training on one UVA A6000

## Question and authorized scope

Dustin requested a distinct long UVA training trial that complements the local
RTX 4090 width-8 investigation and works toward demonstrated convergence. The
exact trial is
[`continuation-w16-feasibility-7h-uva-a01`](../trials/continuation-w16-feasibility-7h-uva-a01.json).
It continues width 16 from its audited 46-update endpoint, keeping the calibrated
unit-backtracking L-BFGS optimizer. Width 16 provides a different model trajectory
on a GPU with measured optimization costs. Its current score is not a reason to
declare it superior; the three widths started differently and remain unconverged.

The local agent owns the width-8 continuation from 177 updates and its diagnostic
implementation. This trial reuses that merged implementation and its 32-update
reporting cadence. It creates no duplicate width-8 trial and no competing
diagnostic implementation. The old, unclaimed width-16 common96 A02 draft is
superseded by this explicitly longer opportunity; its historical A01 remains intact.

## Verified parent and unchanged computation

Restart `9398025d32f8ffe89707faa0f7b0642b14d4ec1daceb4bcfb5013836a812954c`
binds parent run `continuation-w16-p1-m96-a01-a362528360f8`, state object
`9ab2925f528cac463d5a15929f57e7fedb5a5b883349417e4f3e14a959bad3ea`, and
q/N 16.56779534832199. The reviewed import retains 46 accepted updates, 295
forwards, 60 VJPs, 165 infeasible trials, 175 rejections, and
2,283.882704458083 prior model-window seconds. Dispatched calls after the last
accepted state remain charged. L-BFGS history, the 21-state convergence window,
mu = 1e-6, and accepted step state are restored rather than reset.

All 2,290 observations, physics, signed evaluator, float64 arithmetic, covariance,
normalization reference, positivity floor, line-search acceptance and numerical
tolerances are unchanged. The new `p1-time-window-v2` policy changes only the
permitted elapsed window and required finalization reserves. Historical policies
retain their limits. Worker, supervisor, result collector and diagnostic arithmetic
are reused through their existing registered-policy dispatch.

## Bounded opportunity and resource choice

The UVA specialist approved one A6000, one node/task, two CPUs and 16 GiB host
RAM, under `spinquest_standard`, with an eight-hour Slurm walltime. Request the
public `gpu` partition and `gpu:a6000:1`; retain NIL exports and no requeue.
The worker uses one math thread and the already qualified PyTorch container.

| Limit | New segment | Cumulative trajectory |
|---|---:|---:|
| Accepted-update guard | 4,096 | 4,142 |
| Charged forward guard | 16,384 | 16,679 |
| Charged VJP guard | 8,192 | 8,252 |
| Model-window seconds | 25,200 | 27,484 |

The seven-hour model window includes loading, replay, diagnostics and a
300-second endpoint-gradient reserve. Saved-array QA has a further 1,200 seconds,
giving 26,400 seconds inside the eight-hour allocation. The outer 2,400-second
margin allows allocated preflight and retention. Cumulative elapsed time rounds
prior work plus the new segment upward by less than one second; the independent
25,200-second segment bound is authoritative. This is a newly authorized bounded
optimization opportunity, not a concealed increase to an old trial's allowance.

The large call/update caps are protective bounds intended to let time or
convergence govern. Report any cap that actually binds; they are not predictions
of achieved work. The prior short width-16 A6000 segment measured roughly 20–70
seconds between accepted updates, 94% median GPU utilization, 9.783 GiB owned
GPU memory and 1.320 GiB sampled worker RSS. That supports substantial additional
work in seven hours, but neither predicts convergence nor guarantees unchanged
cost as the trajectory evolves.

B200 passed replay, but has no measured optimization advantage for this workload
that justifies its approximately 8.06-times higher live billing rate. Keeping the
measured A6000 environment avoids adding a hardware change to this baseline test.
The eight-hour request's billing upper bound is 1,280 scheduler billing-unit-hours;
this is not a verified remaining allocation balance or a monetary price. Resource
and scheduler details are retained in local operational records.

## Execution and evidence

Use a clean pinned source, successful CPU CI, independently reviewed trial and
new atomic claim with remote readback. The actual allocation performs the existing
full input/environment checks, CUDA/NVML UUID binding, parent value and gradient
replay, and two directional checks before optimization. Existing numerical and
resource checks suffice; this bound-only extension needs no separate GPU
qualification job.

The supervisor uses the merged asynchronous optional-progress reader. Mandatory
memory sampling remains fresh and independent. Each accepted state is atomically
saved. An independent optional retention process may copy provisional output to
persistent storage during execution; terminal retention must verify every file
against the stopped run. Copies are not evidence of a new accepted state, and
live multi-file copies are not complete restart archives until verified.

Record rejected row identities and normalized positivity margins, feasible
Armijo rejections, proposed/accepted step sizes, directional and curvature
diagnostics, and summaries every 32 new accepted updates. These reports reuse
computed model values and do not reset or stop optimization. Include q/N versus
updates, forwards, VJPs and elapsed work; residual/nuisance diagnostics; the
188 high-COMPASS rows; raw endpoint gradients; resource/diagnostic overhead;
and all failed or interrupted work.

Stop early only for the unchanged convergence gate or an existing explicit
time/call/resource/numerical/line-search condition. The fixed gate requires both
ten-update windows at unchanged mu: q/N range <= 1e-4, fixed-sigma prediction
span RMS <= 1e-3 and maximum <= 1e-2, terminal penalized-gradient maximum <= 1e-5.
A normal time-reserve stop remains partial optimization evidence. Running for
seven hours, passing GPU monitoring, or reaching a guard count is not convergence.

## Decision after the run

Publish the full immutable archive, independently verify its downloadable hash,
and review the result with all convergence qualifications. If the gate passes,
report convergence for this fixed trajectory and tested criterion, without
claiming a global optimum or a width winner. If it does not pass, use progress,
constraint attribution and conditioning evidence to choose a bounded successor
or one controlled optimizer experiment from a matched saved state. Continuing
improvement can justify another opportunity; a shared feasibility bottleneck
should be investigated before automatically spending another long allocation.

Compare diagnostic patterns with the locally owned width-8 run. Different
hardware, starts and optimization opportunities preclude a direct architecture
ranking. Width 24 and the paired-start matrix remain separate subsequent work.
No automatic retry, requeue, cancellation of another trial, or optimizer switch
is part of this specification.
