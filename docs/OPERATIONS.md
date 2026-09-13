# Execution and recovery

## Environment

Use Python >=3.11, NumPy, SciPy, PyTorch and psutil as declared in pyproject.toml.
Install in an isolated virtual environment or approved container; do not change
another running study's environment. The original host used Python3.11 and
PyTorch2.12.0+cu126. Package ranges are installation compatibility ranges, NOT a
claim that every combination is numerically qualified. Each run records exact
versions, GPU, CUDA build, thread count, platform, code and data identities.

Use float64, deterministic algorithms and no TF32. Run CPU tests first. Then run
the full PORT trial on the actual compute environment. Saved-reference tolerance:
predictions <=1e-7 fixed sigma; q/N <=1e-8 absolute; raw-gradient max error <=1e-7
where a raw reference exists; two active-mu directional errors <2e-6 absolute.
Derivative probes shrink only to remain feasible/resolve finite-difference error;
they may not change the acceptance tolerance after seeing a favored result.

Do not assume a PyTorch build works on every GPU generation. Verify CUDA support,
float64 and memory on an allocated node. Initial full-data cache requires roughly
8 GiB plus model/autograd overhead; use a full GPU with >=24 GiB as the initial
portable profile. An 11-GiB card or small MIG slice is not a drop-in target.

## Lifecycle

`ready spec -> atomic claim -> scheduler allocation -> durable launch ->
setup/replay -> derivative gate -> bounded trial -> saved-only audit ->
immutable artifact release -> result PR -> scientific review`.

The clock starts at durable acceptance on the allocated worker host, not at the
Slurm queue-submission time. Queue delay is reported separately. Default trial
model work (including input loading/setup, replay and probes) <=1,800s; total
window3,600s with1,800s saved-only reserve. The supervisor uses an independent
process clock and a separate telemetry thread. Telemetry failure or staleness
over1s fails closed. At cutoff it sends TERM only to its owned process group,
then KILL after2s if necessary. This is bounded escalation, not a claim of exact
real-time interruption of every GPU kernel or OS stall. Slurm wall time adds an
outer ceiling; a fatal supervisor/host loss must be reconciled using scheduler
accounting, not a fabricated cleanup receipt.

The external monitor persists sampled process-tree RSS, available host memory
and GPU memory attributed to the worker's process tree. These are sampled peaks,
not a mathematical bound on unobserved sub-sample spikes. Cached operator bytes
are checked before allocation. The trial's GPU is scheduler-exclusive; this is
not a device-wide total-memory limit over unrelated users on other GPUs.

Scientific full-call and forward counters are different: a feasible objective
uses a forward followed by a VJP evaluation. Both consume forward units; the VJP
also consumes a full-call unit. Counters are charged before dispatch, including
failed/interrupted attempts. Each accepted step is saved atomically. Missing
last-call status is “unknown/interrupted,” not zero cost.

## Failure and recovery

- Hash/schema/row-order/physics mismatch: fail closed. Preserve receipt and stop
  that trial. Do not regenerate historical hashes or substitute nearby parents.
- Replay/directional failure: no optimization. Diagnose in a new bounded attempt
  without relaxing tolerances or silently switching precision/backend.
- Positivity trial failure: record rejection. Never clip or remove a row.
- 32-step backtracking exhaustion: report line-search failure, not convergence or
  proof no feasible descent exists. Preserve the last feasible checkpoint.
- Count/time/resource cap: censored/partial evidence. Audit saved arrays without
  another model call; retain raw-gradient absence explicitly.
- Crash/preemption: use `sacct`/logs/last atomic checkpoint, reconcile calls and
  elapsed time, and preregister a new attempt. Default runner never resumes an
  existing output directory. New attempts do not retroactively erase old costs.
- Missing input asset/credential/allocation: record the specific blocker and do
  useful CPU/code/review work that does not require it.

Historical specifications intentionally reset L-BFGS history on a new
continuation. They retain their original limits and are not uninterrupted
trajectories. The separately preregistered `p1-resume-v1` policy restores verified
curvature pairs and21-state windows. It allows segments up to13,200s plus600s
saved QA, with at least120s reserved INSIDE model time for endpoint gradients.
Exact trial limits may be smaller. Ancestor result receipts determine spent
model-window time; a segment cannot exceed the remaining cumulative allowance
(at most21,600s in this policy). All dispatched calls remain charged.

The atomic `restart.npz` is authoritative if a hard kill leaves `last.npz`
behind. Saved-only audit records which file it evaluated; import requires exact
agreement with that audited endpoint and a hash-bound terminal dispatch ledger.
TERM is deferred only across a short coherent CPU/file state commit. GPU UUID
identity is checked against CUDA; mandatory NVML memory samples do not wait for
optional utilization queries. Optional failures/stale data remain explicit.

## Data and artifacts

Input files are immutable, verified relative-path transports of original bytes.
The source manifest still contains historical absolute paths as provenance;
the runtime does NOT dereference them. It resolves only the separately hashed
portable map. No original home directory, LHAPDF installation, source builder,
or current agent thread is needed to consume frozen inputs.

Keep checkpoints and outputs on shared project/scratch storage during a run;
copy them to retained storage and GitHub release assets promptly. Never rely on
scratch as the sole archive. Never run cleanup against a broad home/workspace
directory. Input bundles and run outputs are excluded from Git history.
