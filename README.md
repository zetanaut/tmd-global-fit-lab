# TMD global-fit laboratory

A portable experiment and results repository for the fixed-physics, unpolarized
DY/SIDIS b-space architecture study. It is designed for autonomous Codex agents,
local GPU workstations, and UVA Rivanna/Afton CPU/GPU allocations.

**Status:** repository and numerical input release prepared locally; GitHub
publication requires the owner's `zetanaut` login. The baseline portable model
and evaluator pass the recorded six-row CPU comparison against the original
implementation at all three widths. Full 2,290-row CPU/GPU portability trials
are preregistered, not yet reported as completed. Subsequent architecture phases
have explicit dependencies and implementation tasks below.

## Scientific purpose

Extract incoming TMDPDF boundaries, outgoing TMDFF boundaries, and a universal
shared Collins–Soper kernel using all 2,290 observations. Determine which network
choices improve a controlled, sufficiently optimized fit and which residual
limitations remain. A decreasing loss is not by itself an adequate fit, an
architecture winner, or an uncertainty estimate.

Read [the scientific contract](docs/SCIENCE.md), [experiment program](docs/EXPERIMENTS.md),
[historical evidence](docs/BASELINE_RESULTS.md), and [current result ledger](RESULTS.md).

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

These commands require publication and repository access; they are not evidence
that publication has already happened. See [publisher setup](docs/PUBLISHING.md).
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

Before training, complete the PORT gates and import the latest closed P0
endpoints. The family/depth/conditioning matrices are scientifically declared,
but their adapters/initialization factories still require implementation and
preregistration. The backlog is detailed enough for another agent to own those
tasks; they are not falsely labeled ready-to-run models. Existing lower-loss
historical endpoints remain diagnostic and do not select a production model.

