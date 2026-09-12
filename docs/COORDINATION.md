# GitHub coordination and ownership

GitHub main is the reviewed plan/result ledger. Agent conversations are not the
authority for input identity, ownership, completed work, or scientific decisions.
Use Issues for discussion and PRs for persistent changes; machine-readable trial,
claim and result files are authoritative within their stated scope.

## Claim before running

1. Fetch main and read the exact trial spec and prerequisites. Check existing
   results and remote claim refs: `git ls-remote --heads origin 'refs/heads/claims/*'`.
2. Commit code/spec changes and use a clean checkout. Generate a unique owner name
   (agent/site/session), not a shared “worker” name.
3. Run `python -m tmdlab.claim --trial trials/ID.json --owner NAME
   --out run-output/claims/ID.json`. Store the receipt with the job inputs.
4. The tool creates a unique claim commit and a remote `claims/ID` branch with an
   atomic absent-ref precondition. Its empty `--force-with-lease=<ref>:` form means
   CREATE ONLY; it cannot replace an existing claim. Readback must match the exact
   returned claim commit. If another agent wins, choose different useful work.
5. Submit the run using that receipt and the claimed code commit. Do not check out
   the claim branch to run: the receipt's `code_commit` is the executable revision.

Claims persist after completion. They are not recycled or automatically expired.
The spec's `status: ready` is its immutable preregistration state, not live job
status. Do not edit it to running/completed; derive live/completed state from the
claim, scheduler receipts and append-only result records. Keep draft plans outside
`trials/` until the exact specification is ready to commit.
A technical retry gets a new preregistered attempt ID and links the old attempt,
its costs and exact checkpoint. A disappeared chat or pending Slurm job is not a
reason to reclaim ownership. Verify `squeue`, `sacct`, outputs and the prior owner.
Human/maintainer disposition of abandoned work is a new decision record.

One shared claim must never be launched at two sites. Local output-directory
creation is exclusive, and Slurm output roots should be on a filesystem shared
by the participating jobs. This is not a Byzantine security system against a
collaborator deliberately fabricating claims; access control and review still
matter. Credentials stay on the submission/transfer host, not in job environments.

## Result publication

Each agent works on a unique branch such as `results/<run-id>`. After computation,
upload the immutable archive and its checksums as a run release. Add the small
JSON result, regenerate the table, and open a PR. Include failures and partial
runs. Never force-update an old result branch, overwrite an asset, or amend a
historical record after someone has cited its identity.

Resolve table-only merge conflicts by regenerating from all merged JSON records.
Do not discard another agent's entries. An independent reviewer checks hashes,
parent/run lineage, limits, replay/positivity, convergence qualifications, and
residual/nuisance meaning before accepting scientific conclusions.

Suggested Issue labels: `portability`, `ready`, `running`, `review`, `blocked-input`,
`numerical-gate`, `scientific-decision`, `cpu`, `gpu`, `rivanna`. Labels are aids,
not a substitute for atomic claims or result receipts.
