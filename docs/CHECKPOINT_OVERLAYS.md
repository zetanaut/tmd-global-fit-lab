# Closed P0 endpoints and checkpoint overlays

W01 imports the exact V7 w8/S01 and w24/S00 final NPZ bytes. W02 adds a
saved-only verifier and runtime loading path without modifying the 2.2 GB
baseline bundle or its private release. The two objects total 182,708 bytes and
are stored directly in this private Git repository; no separate download, token
transfer, mutable alias, or input-release update is needed.

## Exact identities

| Endpoint | Canonical manifest identity (`overlay:` prefix in a trial) | Exact NPZ SHA-256 |
|---|---|---|
| V7 w8/S01 | `8cf0e6dd1d50c54e51e727028f566ef9352314e6e7bcc5113d8595b8783d39d0` | `de97942f3a030cbc6648b6b452381d316aa945d1a8629a5360313c80ebd6ae61` |
| V7 w24/S00 | `7744bbd6e185b8c706c2a84e3f0bc80a61824a85cd8ab1c27d5ccea62e8ebfd8` | `bfe8a29ab9e2e8ed203f2e5a781038be41aeac76cf52818b00015d9495384ae6` |
| w16/S02 unchanged | Existing bundle key `p0-w16-096` | `cf634461ee7bddae3d76ca90cc03e339bd5b6b272cbb26fb3b5bd7eeb0285843` |

Manifests live at `checkpoints/<canonical-identity>.json`. Their identity is
SHA-256 of sorted compact JSON excluding the `identity` member. NPZ objects live
at `checkpoint-objects/<file-sha256>.npz`; these are different kinds of hashes.
The original baseline checkpoint names retain their existing meaning.

## Verification without scientific execution

From a checkout with the unchanged baseline fetched using the existing workflow:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python scripts/verify_checkpoints.py --bundle inputs/baseline-v1
python -m pytest -q tests/test_checkpoints.py
python scripts/check_repository.py
```

This reads saved arrays only. It verifies exact object bytes, manifest identity,
source/metric/bundle identity, original parent hash/q/model/parameter schema,
scientific evidence hash and ledger, all-float64 array shapes/finiteness, saved
q/barrier/objective and strict positivity. It also rechecks w16 and the baseline
lock/inventory hashes. It does not rerun operator-model evaluation, gradients,
directional checks, GPU checks or the separately owned portable prereq harness.

The one-shot `scripts/import_closed_v7.py --source-root <original-study-root>
--bundle <baseline-directory>` documents how this import was made. It requires
the original evidence tree and refuses to overwrite an existing import. Normal
agents use the committed artifacts and verifier, not this local import tool.

## Future trial binding (not an executable allocation)

An overlay trial still needs the entire existing exact preregistered trial JSON,
reviewed prerequisites, fresh claim and launch workflow. In addition it must pin
`start_checkpoint` to `overlay:<manifest-identity>` and include:

```json
{
  "phase": "P1",
  "checkpoint_binding": {
    "endpoint_sha256": "de97942f3a030cbc6648b6b452381d316aa945d1a8629a5360313c80ebd6ae61",
    "parent_sha256": "d195ecee17317e5164872dfcf096040ba69542ef1b8852f6995d28232a0ed075",
    "accepted_updates_before": 160,
    "optimizer_history_reset": true,
    "allocation_id": "replace-with-reviewed-new-allocation",
    "budget_origin": "new_allocation"
  }
}
```

Here `parent_sha256` is the V7 endpoint's historical parent083, not the endpoint
itself. New phase updates and caps are charged to a genuinely new allocation,
with the previous 160 accepted updates and segment costs retained separately.
The consumed P0 allocation has zero remaining updates. Wrong lineage, stale
counts, P0 phase reuse, or reuse of the origin allocation ID are rejected before
model construction. A syntactically new allocation ID is not permission to run;
review and claims remain mandatory. Existing PORT specs are unchanged and still
refer to the original released parents, not these imported finals.

This first adapter deliberately accepts the exact V7 saved-array inventory and
its scientific-audit receipt format, with a parent in the immutable baseline.
Arbitrary later result formats, overlay-parent chains and new model families
need reviewed import adapters/tests; they are not silently accepted. No new
ready trial, scientific claim, GPU PORT run or UVA submission accompanies this PR.

## Immutable evidence and qualifications

`evidence/p0-v7-2026-09-13/index.json` links receipt/lineage/scientific evidence
with both original-source SHA-256 and committed-derivative SHA-256. Scientific
numbers are retained; personal absolute paths and coordination identifiers are
removed or normalized, commands omitted. These JSON files are explicitly
redacted derivatives, **not** byte-identical original receipts. The exact
originals remain in the source archive; their hashes permit owner-side checking.
No personal onboarding, raw chat, thread identifier or credential is included.
The original Director status and P1 assignment and V8 source/test/output are
hash-pinned references only, not copies of personal coordination documents.

The import rechecked 93 scientific source pins. All three selected trajectories
have 160 accepted updates; P0 is complete and unconverged. V6 w24 is a different
parent branch; V6 w8 is a repeated path, not an extra seed/update allocation.
Historical receipt cumulative totals are not complete project totals: preserve
older attempt002's additional 10 forwards/four full calls/zero accepted steps,
as well as separate repeated-path cost. Unknown wall time and worker peaks stay
unknown; preflight peaks are not maximum worker telemetry.

V8's seven CPU surrogate tests are repair evidence only, not native CUDA-stall
clearance, a fit, or a new compute window. Native P1 remains solely Manager-owned
and does not wait for this portable work. See [current historical conclusions](BASELINE_RESULTS.md).

CI rejects modification/deletion of previously committed checkpoint manifests,
objects, historical evidence, trials and results, as well as the baseline lock.
Corrections are new reviewed records, never input-release overwrites. The private
repository's owner-review convention still applies; CI is not server-side write
protection against an owner bypass.
