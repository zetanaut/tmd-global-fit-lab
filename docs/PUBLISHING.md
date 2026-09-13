# Owner-side GitHub setup

Target: `zetanaut/tmd-global-fit-lab`, private initially. The repository, input
release and access controls must be created before a remote agent can clone/run.
No password or token should be pasted into an agent conversation.

Authenticate GitHub CLI as `zetanaut` through its supported login flow:
`gh auth login --hostname github.com --git-protocol https --web --scopes workflow`.
Verify with `gh api user --jq .login` and `gh auth status`.
See [GitHub CLI authentication](https://cli.github.com/manual/gh_auth_login).
Use a narrowly scoped dedicated credential for later automation; tokens must
not appear in clone URLs, scripts, issues, logs or Slurm exports.
The initial publisher needs workflow permission to push the CPU CI definition.

After content/rights review and a clean committed checkout:

```bash
bash scripts/publish_repository.sh
gh release create inputs-baseline-v1 dist/input-assets/baseline-v1-*.tar \
  --repo zetanaut/tmd-global-fit-lab \
  --title 'Frozen baseline inputs v1' \
  --notes 'Exact operator bytes and fixed metric; inventory: data/baseline-v1.json'
python scripts/input_assets.py fetch --cache artifacts/remote-check --dest scratch/remote-check
```

The fetch step verifies downloaded parts, extraction safety, all4,600 files and
the bundle identity. Only after that succeeds change the release lock's
`publication_status` to `uploaded_and_download_verified`, commit the receipt,
and update README status. Do not change any existing asset/hash to mask drift.

Dustin confirmed owner-only access: just him and his agents. Do not invite
collaborators or require separate GitHub accounts for agents. Use owner-approved
authentication under `zetanaut` on the submission/transfer hosts; a new host
still needs its own authorized setup. Keep agent/site/session owner IDs,
checkouts, branches and trial claims distinct even though GitHub authentication
is shared. See [coordination](COORDINATION.md).

Keep Issues enabled and protect main with required `cpu-contracts` checks and
PR review where account features permit. Agents must follow review conventions
and never delete historical release assets. A claim writer needs permission to
create `claims/*` refs; compute jobs need no GitHub credential. Configure
protections to preserve claim creation while disallowing arbitrary main updates
and claim overwrite/deletion.

On 12 September 2026, GitHub returned HTTP 403 for private-repository branch
protection on this account, requiring GitHub Pro or public visibility. Neither
an upgrade nor a visibility change was made. CI, PR review conventions and
client-side create-only claims work, but server-enforced branch protection is
not enabled. Write-capable collaborators remain trusted; these conventions do
not prevent a collaborator from deliberately bypassing them. A change in plan
or visibility requires the owner's decision. Recheck before granting access.

The publisher refuses to overwrite or initialize an existing remote repository.
If the name is taken, inspect it and ask the owner before changing its contents.
Do not push this package to the unrelated `uva-spin/b-space` deployment key.

The original owner-side input export command is documented in
`scripts/export_inputs.py --help`. It reads the original source tree and Manager
checkpoints and writes a new transport bundle. Remote agents consume the release
and never need those original local paths. Do not rebuild the frozen bundle to
add future checkpoints; implement the separate hashed checkpoint overlay in W02.
