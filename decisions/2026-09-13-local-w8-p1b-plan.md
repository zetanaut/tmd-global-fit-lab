# Local width-8 P1B extended-optimization plan

## Decision

Run one state-preserving width-8 Nested-FiLM P1B continuation on the local RTX
4090. It begins from the audited 81-update P1 restart and permits96 additional
accepted updates at the unchanged `mu=1e-6`, for a target of177 cumulative
accepted updates. It preserves the exact L-BFGS curvature/history/window and
charges all prior and new calls. This is a bounded optimization opportunity
well beyond the interrupted Rivanna segment, not a fresh start or an
architecture selection.

## Fixed scope and limits

Physics, all2,290 rows, bundle/source/metric identities, float64,
determinism, full-observable positivity, unit backtracking, and the P1
convergence criteria are unchanged. The run has at most13,200 seconds of
model work plus600 seconds saved-only QA; its endpoint-gradient reserve is180
seconds. Its cumulative ledger is capped at177 accepted updates,4,741 forwards,
612 VJPs and17,696 model seconds. A count, resource, time, feasibility or
convergence stop is retained without an in-place restart.

The local host binds the only observed RTX4090 as CUDA logical device0 and its
physical UUID is verified before worker dispatch. It runs in a finite16 GiB
user-service cgroup with a20 GiB owned-GPU ceiling. The local PORT replay is
operational qualification only and is not used as a score comparison.

## Interpretation

This single width-8 result can show whether its own trajectory continues to
improve or reaches the unchanged convergence test. It cannot rank widths:
widths16/24 need separately preregistered comparable extended opportunities
before a capacity conclusion. If width8 remains unconverged at this cap, the
next action is an explicit review, not automatic continuation.
