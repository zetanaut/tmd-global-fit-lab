# Staged portable P1 GPU plan

## Decision

After six successful full-data PORT replays, run a fresh **portable** P1
continuation allocation for the three sealed Nested-FiLM depth-1 starts: width
8/S01, width 16/S02, and width 24/S00. This is a portable implementation study,
not the separately assigned native P1 program. The original P0 allocations are
fully consumed and retained as history; every new cell has a fresh P1 allocation
ID, reset L-BFGS history, exact starting bytes, and zero shared optimizer state.

Each cell fixes mu=1e-6 and allows at most 96 new accepted updates, 600 forwards,
240 VJP/full calls, 1,800 seconds model work, and 3,600 seconds total including
saved-output QA. A time/call/resource stop is a preserved partial result, not a
reason to extend the window or silently retry.

## Staging and throughput

Start width 16 as the real fit-time resource/throughput pilot because it is the
lowest-q sealed P0 endpoint and its parent is in the frozen baseline bundle.
It is also a scientifically valid full P1 allocation, not a disposable smoke.
Claim and submit width 8 and width 24 independently only after the width-16
pilot has recorded at least ten accepted updates with preflight passing,
fresh sampled telemetry, no supervisor stop, worker RSS below 12 GiB, owned GPU
memory below 20 GiB, and host-available memory at least 8 GiB. Then run the
remaining two cells concurrently, one complete RTX A6000 each.

This limits the first unmeasured optimization workload to one GPU, then uses
2--3 independent GPUs rather than trying to distribute one optimizer across
devices. The current portable runtime accepts only one assigned CUDA device;
multi-GPU fitting is not implemented or implied. Do not use Afton for P1 until
the exact intended GPU/software family has completed its own PORT qualification.
Rivanna RTX A6000 is the qualified family.

## Exact starts

| Portable P1 cell | Sealed start | q/N at start | Historical accepted updates |
|---|---|---:|---:|
| width 8 | V7 overlay S01 | 16.955715679 | 160 |
| width 16 | frozen baseline p0-w16-096 S02 | 16.661796605 | 160 |
| width 24 | V7 overlay S00 | 16.807363794 | 160 |

The V7 overlay bindings enforce exact endpoint and historical-parent hashes.
The width-16 binding records the exact bundle checkpoint SHA-256. Existing
P0 endpoint evidence says none of these trajectories established the required
21-state plateau. This P1 round assesses that question with equal new
opportunity; it is not an architecture comparison or production selection.

## Required result handling

Each finished or censored run must retain full counters, optimizer states,
endpoint predictions/gradients, raw and adjusted residual diagnostics, DY
closure/nuisances, resource telemetry, scheduler accounting, claim, and exact
archive. Publish a unique immutable artifact, separately download and hash-check
it, then create the canonical result record. Do not use a planned URL as a
published result. Current GitHub API token limitations affect release/PR
publication, not the archived evidence or the create-only Git claims.

