import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from tmdlab.io import sha


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "compare_saved_raw_gradients.py"


def endpoint(path, *, theta=None, gradient=None):
    theta = np.arange(3, dtype=np.float64) if theta is None else theta
    gradient = np.arange(3, dtype=np.float64) / 10 if gradient is None else gradient
    np.savez(path, theta=theta, values=np.ones(2), raw_gradient=gradient,
             penalized_gradient=gradient + 1)


def invoke(tmp_path, candidate, cpu, a6000, *, cpu_hash=None, extra=()):
    out = tmp_path / "comparison.json"
    return subprocess.run([sys.executable, str(SCRIPT), "--candidate", str(candidate),
        "--cpu", str(cpu), "--cpu-sha256", cpu_hash or sha(cpu),
        "--a6000", str(a6000), "--a6000-sha256", sha(a6000),
        "--out", str(out), *extra], cwd=tmp_path, text=True, capture_output=True), out


def test_saved_raw_gradient_comparison_passes_without_pythonpath(tmp_path):
    candidate, cpu, a6000 = (tmp_path / n for n in ("candidate.npz", "cpu.npz", "a6000.npz"))
    for p in (candidate, cpu, a6000): endpoint(p)
    run, out = invoke(tmp_path, candidate, cpu, a6000)
    assert run.returncode == 0, run.stderr
    result = json.loads(out.read_text())
    assert result["passed"] is True and result["comparisons"]["cpu"]["maximum_absolute_error"] == 0


@pytest.mark.parametrize("case", ["wrong_hash", "wrong_theta", "nonfinite_candidate"])
def test_saved_raw_gradient_comparison_rejects_invalid_inputs(tmp_path, case):
    candidate, cpu, a6000 = (tmp_path / n for n in ("candidate.npz", "cpu.npz", "a6000.npz"))
    for p in (candidate, cpu, a6000): endpoint(p)
    kwargs = {}
    if case == "wrong_hash": kwargs["cpu_hash"] = "0" * 64
    elif case == "wrong_theta": endpoint(cpu, theta=np.array([9., 1., 2.]))
    else: endpoint(candidate, gradient=np.array([0., np.nan, 2.]))
    run, out = invoke(tmp_path, candidate, cpu, a6000, **kwargs)
    assert run.returncode != 0 and not out.exists()
