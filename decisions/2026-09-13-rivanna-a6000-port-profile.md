# Bounded Rivanna RTX A6000 PORT profile

The width-8 A100-40GB submission could not start because the eligible GPUs were
occupied. A new hardware attempt uses one full RTX A6000 and a smaller,
evidence-based host-memory request. This changes resource qualification only;
the model, evaluator, reference checkpoint, data, metric, float64 arithmetic,
replay tolerances, directions/seed, and zero-update PORT scope are unchanged.

## Original pending submission

`replay-w8-gpu-a01` retains claim commit
`5b96019302ab4c51ba9511bd4e4f0d41237d357f`. Job `19761013` used
`spinquest_standard` and remained pending. It was canceled with both the exact
job ID and a PENDING-state filter. Scheduler accounting reports `Start=None`,
`Elapsed=00:00:00`, empty allocated resources, and no scientific launch.
Cancellation ended at 2026-09-13 03:28:00 UTC. The claim and original
preregistration remain immutable. There is no model work or fit endpoint to
classify as a scientific failure. Queue history is retained separately.

## Evidence and bounds

The same implementation passed all 161 CPU engineering tests and repository
checks in allocation `19760633`. The container SHA-256 is pinned in the new
trial; its Python/PyTorch/CUDA versions are retained in environment evidence.
The input release passed all three archive checks and all 4,600 input-file
checks. The running CPU PORT trial `19760962` is a separate owned attempt and
is unaffected by this resource change.

The full CPU evaluator retains 7,586,707,632 bytes (7.07 GiB) of tensor cache
and has sampled approximately 11 GiB peak host RSS. Code inspection shows that
the GPU evaluator retains its tensor cache and autograd work on the GPU.
Metadata inspection of all 285 groups found a largest uncompressed operator
of at most 0.051 GiB, largest stacked group weights of 0.036 GiB, and a
conservative temporary NumPy-staging estimate of 0.267 GiB. This supports a
16 GiB host allocation for a bounded GPU smoke; it is not a proof of a hard
bound on CUDA/allocator host overhead.

The new trial requests 2 CPUs, 16 GiB host RAM, one full RTX A6000, and a
65-minute outer Slurm limit under `spinquest_standard`. The supervisor's
worker-process-tree RSS ceiling is reduced to 12 GiB, leaving 4 GiB allocation
headroom. The GPU-memory ceiling remains 20 GiB, cache ceiling 12 GiB, host
available-memory floor 8 GiB, model-work limit 1,800 seconds, and total trial
window 3,600 seconds. Telemetry remains mandatory and fails closed. No TF32,
mixed precision, parameter updates, additional rows, or relaxed gates are used.

At resource review, full A6000 devices had free CPU and host-memory capacity
for this profile; the 48 GiB request could not fit. Prior infrastructure smoke
verified RTX A6000 hardware and driver 595.71.05, but it did not qualify the
scientific runtime. The new PORT attempt must perform all replay/derivative
gates and record its actual hardware and measured peaks. A6000 FP64 throughput
is lower than A100 throughput; no application speed advantage is asserted.

This preregistration does not consume the old claim, change the running CPU
checkout, authorize fitting, or select a production architecture. A resource
limit or numerical failure remains a preserved outcome; no hidden retries.
