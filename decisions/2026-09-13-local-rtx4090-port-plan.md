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
