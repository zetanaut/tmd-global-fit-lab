# P1 logical-GPU telemetry retry

## Observed technical stop

The independently claimed portable P1 width-8 and width-24 A01 jobs started
after the width-16 staging gate, but both stopped before worker dispatch.  On
Rivanna nodes where Slurm assigned physical GPU 6, the container exposed the
one allocated device as logical `CUDA_VISIBLE_DEVICES=0`.  The telemetry
supervisor incorrectly sent physical ID 6 to container-local `nvidia-smi`;
it failed closed before a model call, accepted update, preflight, resource
sample, or endpoint existed.

| Cell | A01 claim | Slurm job | Elapsed | Scientific work |
|---|---|---:|---:|---|
| width 8 | `b5410bcc6e19610921dcc5c566f0c2f92d873e2e` | 19772770 | 48 s | zero model calls |
| width 24 | `49f26d8256934ccbebc3695b519186b1329813f7` | 19772771 | 29 s | zero model calls |

The exact scheduler, launch, supervisor, cleanup, audit, and empty telemetry
artifacts remain in their separate run roots.  Neither original claim nor its
attempt ID is reused.

## Repair qualification

Commit `fd4a029382f7d0be027c2fe472ce914be2cdf776` makes telemetry query
container-visible logical device zero, matching the only supported worker
device `cuda:0`, while retaining Slurm physical IDs in launch provenance.  A
fresh non-scientific A05 allocation (`19773173`) completed on an RTX A6000:
53 focused tests passed, direct real-device telemetry passed with logical
visibility zero, and a process-local physical-ID-6 fixture still selected and
sampled logical device zero.  It recorded five sampled supervisor readings,
no stop reason, and no trial, claim, model, or optimizer activity.

## Decision

Create fresh A02 specifications for width 8 and width 24.  They preserve the
sealed starts, fixed physics/data/metric, float64, `mu=1e-6`, and the original
96-update / 600-forward / 240-full-call / 1,800-second model bounds.  They
are technical retries only after the qualified selector repair; they are not
extensions, reuses, or scientific interpretations of A01.
