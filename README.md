# TMD global-fit laboratory

A portable experiment and results repository for the fixed-physics, unpolarized
DY/SIDIS b-space architecture study. It is designed for autonomous Codex agents,
local GPU workstations, and UVA Rivanna/Afton CPU/GPU allocations.

**Status, 14 September 2026:** The local RTX 4090 width-8 P1B continuation
completed 96 additional accepted updates, reaching 177 cumulative portable P1
updates and q/N = 16.448895619. Its saved endpoint audit and clean execution
pass; both convergence windows fail. The
[P1B result review](decisions/2026-09-14-local-w8-p1b-outcome.md) records the
verified archive, preserved optimizer history and full cost ledger. Widths 16/24
remain at the earlier interrupted 46/30-update endpoints. The architecture
study remains active. Read the
[current study plan](docs/CURRENT_STUDY_PLAN.md)
and [published results](RESULTS.md) before claiming any further work.

## Scientific purpose

Extract incoming TMDPDF boundaries, outgoing TMDFF boundaries, and a universal
shared Collins–Soper kernel using all 2,290 observations. Determine which network
choices improve a controlled, sufficiently optimized fit and which residual
limitations remain. A decreasing loss is not by itself an adequate fit, an
architecture winner, or an uncertainty estimate.

Read [the scientific contract](docs/SCIENCE.md), [experiment program](docs/EXPERIMENTS.md),
[historical evidence](docs/BASELINE_RESULTS.md), and [current result ledger](RESULTS.md).
Coordinate initial access and staged work in the [launch tracker](https://github.com/zetanaut/tmd-global-fit-lab/issues/1).

## Agent quick start

```bash
git clone https://github.com/zetanaut/tmd-global-fit-lab.git
cd tmd-global-fit-lab
# Read AGENTS.md and its required documents before running jobs.
python3.11 -m venv .venv
source .venv/bin/activate
# Install a suitable PyTorch CPU/CUDA build for this machine first if needed.
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/input_assets.py fetch
python scripts/check_repository.py
```

These commands require repository access and GitHub CLI
authentication on the transfer workstation. See [publisher setup](docs/PUBLISHING.md)
for access and the current private-repository branch-protection limitation.
The input release is approximately 2.2 GB, split into sub-1-GiB tar assets with
SHA-256 hashes. It contains the exact 2,290 operator arrays, fixed metric, four
positive checkpoint starts, and selected original-source provenance. Large
arrays are deliberately excluded from Git history.

Claim a trial on a workstation with GitHub credentials:

```bash
python -m tmdlab.claim --trial trials/replay-w16-gpu-a01.json \
  --owner YOUR_UNIQUE_AGENT_NAME --out run-output/claims/replay-w16-gpu-a01.json
python -m tmdlab.run --trial trials/replay-w16-gpu-a01.json \
  --bundle inputs/baseline-v1 --device cuda:0 \
  --claim run-output/claims/replay-w16-gpu-a01.json \
  --out run-output/replay-w16-gpu-a01
```

Use allocated hardware and a clean checkout. On UVA, submit the corresponding
Slurm task rather than running the command on the login node. CPU trials use
their own `*-cpu-*` specifications and `--device cpu`. Never launch the same
claim at two sites. Follow [coordination](docs/COORDINATION.md),
[UVA setup](docs/RIVANNA.md), and the [result contract](docs/RESULTS_CONTRACT.md).

## Repository layout

| Path | Purpose |
|---|---|
| `AGENTS.md`, `docs/` | Self-contained mission, conventions, program and operations |
| `trials/*.json` | Immutable, executable preregistrations; exact starts and budgets |
| `decisions/` | Evidence-based phase promotions and scope decisions |
| `data/baseline-v1.json` | Immutable numerical release inventory and checksums |
| `checkpoints/`, `checkpoint-objects/`, `evidence/` | Hash-addressed V7 finals, lineage and historical evidence; baseline unchanged |
| `tmdlab/` | Portable model, signed evaluator, fixed metric, supervisor and result tools |
| `slurm/` | One-GPU and CPU job-array templates |
| `validation/`, `tests/` | Development evidence and executable CPU safeguards |
| `results/`, `RESULTS.md` | Small result records and generated tracking table |
| `inputs/`, `artifacts/`, `run-output/` | Local-only large files, ignored by Git |

## What is ready and what remains

The initial executable scope is Native Nested-FiLM widths 8/16/24 with depth 1,
full-data replay and bounded continuations from registered same-schema starts.
The portable evaluator supports CPU and a single assigned CUDA device; multiple
GPUs run independent cells. The computation was ported into a new version with
relative paths, not copied with broken local absolute-path imports.

The initial PORT gates have passed. The exact closed V7 P0 w8/w24
endpoints are now imported; w16 remains the released reference. P0 is complete
but unconverged. See [checkpoint overlays](docs/CHECKPOINT_OVERLAYS.md) and
[historical results](docs/BASELINE_RESULTS.md). The separately owned native P1
program does not wait for portable qualification. No new portable trial is
authorized by this import. The family/depth/conditioning matrices are scientifically declared,
but their adapters/initialization factories still require implementation and
preregistration. The backlog is detailed enough for another agent to own those
tasks; they are not falsely labeled ready-to-run models. Existing lower-loss
historical endpoints remain diagnostic and do not select a production model.
