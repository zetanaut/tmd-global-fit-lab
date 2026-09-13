# Resource profiles for remaining UVA PORT cells

Full-data width-8 CPU and RTX A6000 PORT runs passed their frozen numerical
gates and saved-array audits, with zero optimizer updates. This decision selects
bounded resource profiles for the remaining width-16/24 CPU/GPU cells. New a02
specifications preserve the original a01 files and do not claim their IDs.

## Qualification evidence

- CPU run `replay-w8-cpu-a01-fe0e2232a8a7`, Slurm job `19760962`:
  model-work time 1529.59 seconds; total supervised time 1530.53 seconds;
  8 forwards, 3 VJPs, zero updates. Prediction error 2.2267e-13 fixed sigma;
  q/N error 1.0658e-14; both directional errors below 1e-10. Sampled worker
  RSS peak 8.709 GiB; scheduler RSS peak approximately 10.98 GiB.
- GPU run `replay-w8-gpu-a02-65b3fcf031c1`, Slurm job `19762121`:
  RTX A6000; model-work time 128.08 seconds; total supervised time 129.26
  seconds; 8 forwards, 3 VJPs, zero updates. Prediction error 1.6715e-14
  fixed sigma; q/N error 7.1054e-15; both directional errors below 1.1e-10.
  Sampled worker RSS/GPU peaks 1.330/9.066 GiB; scheduler RSS about 3.56 GiB.

These are separate timing/resource observations, not an architecture comparison.
The width-8 anchor lacks a saved raw-gradient reference: both runs computed
and saved raw gradients and passed the directional checks. The width-16 parent
does supply a raw-gradient reference; the width-24 parent does not. Every new
trial retains the existing conditional raw-gradient gate and both directions.
Final scheduler CPU-time fields were unreliable; zero reported TotalCPU is
not evidence of zero work or zero utilization.

## Selected CPU profile

`replay-w16-cpu-a02` and `replay-w24-cpu-a02` use four PyTorch intra-op
threads, five allocated CPUs, 48 GiB host memory, and a 65-minute outer limit.
The completed single-thread width-8 run left only about 270 seconds under the
1800-second model-work cap. Wider models and feasibility-related directional
probe shrinkage could exhaust that margin. Four threads are a bounded
resource experiment, not a measured or promised four-fold speedup.

`worker.py` already calls `torch.set_num_threads(budget['cpu_threads'])` before
model work and records the actual setting. Global OMP, OpenBLAS, and MKL
environment caps remain one, so NumPy/SciPy metric work is not multiplied.
Each new CPU trial must independently pass the same gates; changed parallel
reductions or overhead are not grounds to relax tolerance or extend the clock.
The 48 GiB RSS ceiling and host allocation remain unchanged.

## Selected GPU profile

`replay-w16-gpu-a02` and `replay-w24-gpu-a02` use one full RTX A6000,
two allocated CPUs, 16 GiB host RAM, 12 GiB worker-process-tree RSS ceiling,
and a 65-minute outer limit. The width-8 observations support this host profile
with substantial measured headroom. GPU memory remains capped at 20 GiB;
larger widths must be monitored and may still hit a resource bound.

## Fixed scientific scope and execution

All four trials keep their original width-specific checkpoint, seed, model
family/schema, all 2290 rows, bundle/source/metric identities, float64, replay
tolerances, zero optimizer phases, 240 full calls, 600 forwards, 12 GiB cache,
1800-second model-work cap, and 3600-second total window. They use the identical
scientific implementation already CPU-tested in revision 85264ee; this commit
adds only trial specifications and this decision record.

UVA operations use only `spinquest_standard`. Run at most one CPU and one GPU
trial concurrently; start width 16 first on each backend. Each cell requires
its own fresh atomic claim and immutable result archive. Gate/resource failures
or censored outcomes remain preserved; no hidden retries, budget extensions,
changes to the old trial files, native P1 duplication, or production selection.
Local outcome archives and scheduler receipts are complete for the first two
runs; GitHub release/PR publication awaits the token permission correction
already requested from the operator.

