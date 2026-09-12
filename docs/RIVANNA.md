# UVA Rivanna/Afton handoff

Prepared from UVA Research Computing documentation checked12 September2026.
The cluster agent must verify current partitions, modules, its allocation and
site policy with `sinfo`, `module spider`, and UVA guidance. No UVA login,
allocation, Slurm submission or remote GPU validation was performed during
repository preparation.

UVA uses Slurm; production work runs on compute nodes, not login nodes. Current
guidance identifies `gpu` for GPU jobs and `standard` for single-node CPU jobs.
Request an explicit partition, allocation and GPU resource. See
[UVA compute service](https://rc.virginia.edu/services/compute-and-storage/aftonrivanna)
and [UVA login/compute-node guidance](https://staging.learning.rc.virginia.edu/notes/hpc-intro/connecting_to_the_system/connecting_logging_on/).

## Operator-supplied configuration

The UVA agent needs: computing ID; authorized Slurm account/allocation;
concurrency/SU ceiling; retained storage location; scratch/work location; and
approved software environment. Never invent an account name or assume unlimited
GPU entitlement. Repo access and data transfer credentials belong on the
login/transfer workstation. No tokens in `--export=ALL`, sbatch scripts or logs.

Use a Python >=3.11 environment with a compatible GPU PyTorch build. UVA provides
Apptainer-backed PyTorch modules; version availability and GPU compatibility can
change. `module spider pytorch` and `module spider apptainer` establish local
options. Containers use `--nv` for GPU access; avoid mixing arbitrary host CUDA
modules into a container that already supplies its CUDA libraries. See
[UVA PyTorch instructions](https://staging.rc.virginia.edu/userinfo/hpc/software/pytorch/).
Do not copy its historical version examples as a promise they match this code.

For Apptainer, execute the Python runner INSIDE the approved SIF with the repo,
inputs and output directories bound. Adapt `array_task.py`'s invocation to
`apptainer exec --nv <verified.sif> python ...`; `TMD_PYTHON` alone is for a
directly executable interpreter/venv, not a multi-word shell command. Record SIF
SHA256 and exact package versions in the run evidence. Test CPU and full GPU
replay before fitting. No root container builds or scheduler bypasses are needed.

## One GPU or many

Start with one full GPU with >=24GiB; request an appropriate current GPU type
with `--gres=gpu:<type>:1` if the partition's generic selection can give a smaller
device. UVA lists several heterogeneous GPU types; do not assume identical
throughput or compatibility. Hardware changes require new portability attempts.
Initial multi-GPU scaling is independent cells in a Slurm job array, each with
one GPU. Do not apply DDP to this stateful scientific optimizer without a separate
numerical/distributed-state validation project.

On the submission host, create `run-output/tasks-gpu.json` with one entry per
already-claimed distinct trial:

```json
[
  {"trial":"trials/replay-w8-gpu-a01.json","claim":"/ABS/claims/w8.json"},
  {"trial":"trials/replay-w16-gpu-a01.json","claim":"/ABS/claims/w16.json"},
  {"trial":"trials/replay-w24-gpu-a01.json","claim":"/ABS/claims/w24.json"}
]
```

Set task-specific paths, replacing the placeholders with your allocation and
shared paths (commas in paths are unsuitable for Slurm's export syntax):

```bash
export TMD_REPO=/ABS/tmd-global-fit-lab
export TMD_PYTHON=/ABS/verified-venv/bin/python
export TMD_BUNDLE=/ABS/inputs/baseline-v1
export TMD_TASKS=/ABS/run-output/tasks-gpu.json
export TMD_OUTPUT=/ABS/run-output/port-gpu-a01
sbatch --account=YOUR_ALLOCATION --array=0-2%2 \
  --export=TMD_REPO,TMD_PYTHON,TMD_BUNDLE,TMD_TASKS,TMD_OUTPUT \
  slurm/trial-gpu.sbatch
```

`%2` caps active array tasks at two GPUs; choose the operator-approved limit.
The template requests1CPU,48GiB host memory,1GPU,65minutes. These are requests,
not permission to exceed trial ceilings. GPU types and account-specific limits
must be confirmed. CPUs reserved for a GPU job are not automatically utilized.
CPU replay/QA uses `trial-cpu.sbatch` with CPU trial specs and no GPU allocation.

Monitor with `squeue -j JOBID` and obtain final accounting with
`sacct -j JOBID --format=JobID,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS`.
Keep the `.batch`/step records and note missing metrics. Do not substitute
requested memory or preflight memory for measured peaks. Pending jobs do not
consume the model clock. Preemption, timeout and failed setup remain tracked
attempts. Arrays must not requeue into an existing output directory.

After jobs close, transfer the output from shared/scratch storage to retained
storage, publish run assets from a GitHub-authenticated workstation and submit
the result PR. Compute nodes need neither GitHub credentials nor network access.
UVA scratch is temporary; consult the current retention policy rather than
assuming archival durability.
