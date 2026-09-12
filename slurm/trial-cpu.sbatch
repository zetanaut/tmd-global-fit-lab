#!/usr/bin/env bash
#SBATCH --job-name=tmd-cpu
#SBATCH --partition=standard
#SBATCH --cpus-per-task=1
#SBATCH --mem=48G
#SBATCH --time=01:05:00
#SBATCH --signal=B:TERM@120
#SBATCH --output=slurm-%A_%a.out
set -euo pipefail
: "${TMD_REPO:?absolute checkout required}"
: "${TMD_PYTHON:?absolute verified Python required}"
: "${TMD_BUNDLE:?absolute verified input bundle required}"
: "${TMD_TASKS:?absolute tasks JSON required}"
: "${TMD_OUTPUT:?absolute output base required}"
cd "$TMD_REPO"
exec "$TMD_PYTHON" scripts/array_task.py --tasks "$TMD_TASKS" --index "${SLURM_ARRAY_TASK_ID:-0}" --bundle "$TMD_BUNDLE" --output "$TMD_OUTPUT" --device cpu
