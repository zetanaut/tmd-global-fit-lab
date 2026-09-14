# Local RTX 4090 width-8 PORT plan

## Decision

Run a fresh, zero-update full-data width-8 PORT replay on the local NVIDIA
GeForce RTX 4090 before any local recovery continuation. This is a distinct
GPU/driver environment from the qualified Rivanna RTX A6000 environment and
therefore needs its own replay and directional qualification. The trial uses
the merged optional-progress supervisor repair and cannot consume any P1
optimization allowance.

## Preconditions and limits

The isolated checkout at the claimed revision passed all 258 CPU tests. The
shared frozen baseline bundle was verified file-by-file: 4,600 files and
identity `09af3277101858478ed6ab6303c532bae4b865ba94770f3c9743c91ccb52073c`.
The locally visible RTX 4090 reports 24,564 MiB and supports PyTorch 2.12.0
with CUDA 12.6 and float64 tensors. It is an otherwise idle single-GPU host.

The run retains the all-row fixed evaluator, seed, width-8 anchor, float64,
deterministic settings, saved replay references, two active-mu directional
checks, and all standard resource/call ceilings. It has no optimizer phase;
any numerical, resource, or monitoring failure is a preserved PORT result and
does not authorize a retry or a P1 continuation.

## Promotion gate

Only a completed replay with passed value, q/N, available raw-gradient, both
directional, resource, and saved-array checks qualifies this exact local
environment for a separately preregistered state-preserving width-8 P1
successor. A passing PORT result establishes neither convergence nor an
architecture result.

## A01 outcome and A02 technical retry

Claimed attempt `replay-w8-rtx4090-a01` ended before its first telemetry sample
or model dispatch. Its supervisor recorded `telemetry_failure: ValueError:
finite cgroup limit unavailable`; the endpoint audit is `no_endpoint`, and all
scientific counters are zero. The confined output archive is
`replay-w8-rtx4090-a01-5a38186ff8bf.tar.gz` with SHA-256
`643ed46d247416d2c7634f1041d86a4de2a71d4614eb5d31a7a71c6f37be6c96`.

The host's interactive session lacks a finite cgroup limit, but a disposable
`systemd-run --user` service verified `memory.max=17179869184`. A new A02
trial therefore runs within that 16 GiB service cgroup. This changes only the
launcher/resource binding; it keeps the code, evaluator, all-row replay,
checkpoint, numerical gates, and zero-update scope unchanged. A02 is a fresh
claim and retains A01's zero-call terminal evidence.

A02's service reached that finite cgroup but started with its default working
directory, so its Python process could not resolve the relative trial path. It
did not enter `tmdlab.run`, create a run directory, sample telemetry, or make a
model call. A disposable service probe then verified both the intended checkout
as `WorkingDirectory` and `memory.max=17179869184`. A03 is the single final
launcher correction: it binds that working directory explicitly. It retains
both prior zero-call attempts and does not authorize an unbounded retry series.

A03 entered the correct checkout and finite cgroup, but its supervisor failed
closed before dispatch because this non-Slurm workstation had no
`CUDA_VISIBLE_DEVICES` value. The user explicitly confirmed that this is a
local single-GPU host, not a Slurm allocation. A disposable bounded-service
probe then verified that setting `CUDA_VISIBLE_DEVICES=0` exposes exactly one
RTX 4090 to CUDA (UUID `8a52c480-835f-a522-42bd-cc144e59e44e`) while retaining
the 16 GiB `memory.max`. A04 is therefore an owner-directed local-device
binding attempt, not a scheduler override: no `SLURM_*` variable is present.
It is the final zero-update PORT attempt in this sequence.
