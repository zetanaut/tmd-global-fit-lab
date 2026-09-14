# Width-16 long training A02: corrected launcher, identical scientific opportunity

The [seven-hour width-16 plan](2026-09-14-uva-w16-long-training-plan.md)
remains the scientific design. A01 job `19945517` obtained an A6000 but ended
after two seconds during batch bootstrap, before scientific launch acceptance,
allocated tests, output-root creation or any model call. Its inherited launcher
incorrectly required an unmerged, superseded monitoring draft as an ancestor of
the released source. This was a launcher provenance error, not a numerical,
memory or optimization outcome. The failed attempt, original claim and exact
scripts remain preserved; no scientific run ID or endpoint is fabricated.

The new immutable trial is
[`continuation-w16-feasibility-7h-uva-a02`](../trials/continuation-w16-feasibility-7h-uva-a02.json).
It uses the same reviewed 46-update restart, unit optimizer, shared diagnostics,
all physics and convergence criteria, and the same segment/cumulative budgets
as A01. Zero new scientific calls or model-clock time were consumed in A01;
its two seconds of allocated execution are retained separately. No old claim
or output is reused, and no automatic retry is authorized by this record.

The corrected local launcher requires the actual merged monitor and diagnostic
commits. One shared static validator checks all source ancestry, pinned hashes,
input/container references, qualification evidence and absent run roots on the
submission host and again during batch bootstrap. A failed static check must
prevent submission. This closes the gap where scheduler test-only validation
accepted the resource request without exercising the launcher's Git guards.

The resource specialist retains the approved single A6000, two CPUs, 16 GiB,
eight-hour walltime and `spinquest_standard` account. Ordinary allocated tests,
complete input verification and restart replay/directional gates remain mandatory.
No standalone GPU qualification or change to evaluator arithmetic is needed.

Release requires independent review, CPU CI on the final source, a new atomic
claim/readback and the successful shared static validator. The user-authorized
training request remains active. Review actual long-training diagnostics and
convergence after this attempt; a successful bootstrap is not a scientific result.
