# Rivanna PORT matrix: complete locally, publication pending

## Decision

The six preregistered full-data portability/replay cells have completed under
their frozen identities and passed their numerical gates, saved-array audit,
and supervisor/cleanup checks. This clears the portable PORT prerequisite for
future portable trials that have their own committed specifications, claims,
and scientific authorization. It does **not** establish optimizer convergence,
an architecture ranking, physical adequacy, or a production selection.

No portable fit is authorized by this decision alone. Native P1 remains
independently Manager-owned and must not be duplicated.

## Completion evidence

Each successful cell used all 2,290 observations, float64 deterministic
execution, the fixed metric/operators/physics, eight forwards, three VJPs, and
zero optimizer updates. Prediction and q/N replay errors passed; both active-mu
directional checks passed at the first `h=1e-5` attempt. Width 16's parent has
a saved raw-gradient reference and both CPU/GPU comparisons passed it. Widths
8 and 24 have no saved raw-gradient reference; their raw gradients were
computed/saved and directional checks passed, but that absence is not a
raw-gradient replay comparison.

| Trial | Run ID | Job | Device | q/N | Model seconds | Peak worker RSS GiB | Peak GPU GiB |
|---|---|---:|---|---:|---:|---:|---:|
| replay-w8-cpu-a01 | replay-w8-cpu-a01-fe0e2232a8a7 | 19760962 | CPU, 1 math thread | 18.129406519 | 1529.59 | 8.709 | — |
| replay-w8-gpu-a02 | replay-w8-gpu-a02-65b3fcf031c1 | 19762121 | RTX A6000 | 18.129406519 | 128.08 | 1.330 | 9.066 |
| replay-w16-cpu-a02 | replay-w16-cpu-a02-054110dbf1b0 | 19763448 | CPU, 4 math threads | 16.661796605 | 1270.15 | 9.279 | — |
| replay-w16-gpu-a02 | replay-w16-gpu-a02-45994b868011 | 19763449 | RTX A6000 | 16.661796605 | 176.57 | 1.295 | 9.783 |
| replay-w24-cpu-a02 | replay-w24-cpu-a02-fa5d2af0bd21 | 19764528 | CPU, 4 math threads | 16.863796532 | 1396.76 | 9.823 | — |
| replay-w24-gpu-a02 | replay-w24-gpu-a02-c511ed48adc1 | 19763995 | RTX A6000 | 16.863796532 | 147.42 | 1.308 | 10.691 |

GPU timing is an observed portability cost, not a fair architecture comparison
against CPU trials: widths, parent checkpoints, nodes, and CPU thread profiles
differ. Nonetheless the observed same-width replay model-window ratios are
about 11.9x for width 8 and 7.2x for width 16 in favor of the qualified A6000.
The portable runtime uses one assigned CUDA device only; scale future independent
cells across one GPU each rather than requesting several GPUs for one fit.

## Immutable local archives

All durable copies were verified file-by-file against scratch. Archives contain
only their exact confined run outputs, scheduler provenance, claims, and script
snapshots; scans found no symlinks or credential patterns.

| Run ID | Archive SHA-256 |
|---|---|
| replay-w8-cpu-a01-fe0e2232a8a7 | `bda4928c5e72de76b8d094facb98f563150684bcfe5dd4ec26b7fc09330a02cd` |
| replay-w8-gpu-a02-65b3fcf031c1 | `2120cf57e894ae4ff0493728132fe5ca537e3610cca62c4e78d39458fc4281da` |
| replay-w16-cpu-a02-054110dbf1b0 | `3c3b0053052c221f7bc9c187af8d0c74b0b00dbf33320e0b82f0eee7424121de` |
| replay-w16-gpu-a02-45994b868011 | `93d3106d0e2be028f3270d73b4e3e40b69531982a51d006df5f2c9e15b2ebcfb` |
| replay-w24-cpu-a02-fa5d2af0bd21 | `0d5cca4f6f560f383f8e1185519340fb2354be91b1556bbdd95b6e86163ee370` |
| replay-w24-gpu-a02-c511ed48adc1 | `905f5dfc8c874af6054671cb81f0dedeefbc9635d78697568abffe7f2d594874` |

The original width-8 A100 submission `19761013` was canceled while pending,
with no allocation or scientific launch. Its original a01 claim remains
preserved; the successful A6000 result is the distinct a02 trial and claim.

## Publication state and next resource decision

These records are locally complete, but not canonical repository result records:
the supplied GitHub token returns HTTP 403 for both release creation and
pull-request access. Before invoking `tmdlab.results collect`, upload every
unique archive as a new immutable release asset, download it to a separate
location, and verify its exact SHA-256. Then record only the verified URL.
Never substitute planned URLs or overwrite an asset.

The measured A6000 replay profile is one GPU, two CPUs, 16 GiB host allocation,
a 12 GiB worker RSS ceiling, and a 20 GiB GPU ceiling; actual worker RSS was
about 1.3 GiB and GPU peak was 9.1--10.7 GiB. A current scheduler inventory
showed roughly ten nominal slots for that profile, but reservations and priority
make that a capacity bound, not a start guarantee. For a new approved portable
optimization phase, first run one bounded GPU pilot that records update
throughput, utilization, and fit-time memory; then run 2--3 independent,
preregistered cells concurrently if it remains healthy. Do not infer fit
convergence or full-fit resource peaks from zero-update PORT alone.

