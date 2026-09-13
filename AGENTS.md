# Start here: autonomous experiment agents

Read this file, `README.md`, `docs/SCIENCE.md`, `docs/EXPERIMENTS.md`,
`docs/COORDINATION.md`, `docs/OPERATIONS.md`, and `docs/RESULTS_CONTRACT.md`
completely before work. On UVA read `docs/RIVANNA.md` too. Then inspect the
current main branch, trial registry, result records, open PRs and claim refs.
No private conversation, local home directory, or original Director is required
for the portable validation stage. The explicit development backlog identifies
what is not yet implemented; do not mistake declared phases for executable jobs.

## Mission and authority

Advance the fixed-physics DY/SIDIS architecture study through documented,
reproducible trials and scientific decisions. Use available authorized compute;
record useful negative results, failures, and censored runs as carefully as wins.
Dustin has authorized agents on local GPUs and UVA CPU/GPU clusters to contribute.
This is not authorization to spend an unspecified allocation: use the account,
concurrency, wall-time and storage quotas supplied by the operator.

You may implement portable infrastructure and preregister the next in-scope
architecture experiment, run accepted trials, perform saved-array QA, and submit
result PRs. Ordinary budget exhaustion or missing plateau is not a permission
hold. Preserve failed attempts, propose bounded successors, and continue useful
work. Stop only for an actual failed gate, missing essential input/access, or a
decision outside the fixed scientific contract. Do not invent an “original”
network identity to unblock a family comparison.

Do not change physics, observations/cuts, C/U/t0, PDFs/FFs, matching, the fixed
normalization reference, numerical accuracy labels, or full-observable positivity.
Do not select production models, publish scientific conclusions as established,
run replicas/BNNs, or enlarge scientific scope without a recorded human decision.
Architecture/evaluator transport code changes need a new implementation identity
and replay tests; never recompute old hashes to hide changes to pinned artifacts.

## Before computation

1. Work on a branch with a clean committed checkout. Run CPU tests.
2. Obtain the input release; verify release-part and full bundle hashes. Do not
   use a partial input set or reconstruct data from plots/text tables.
3. Run the PORT replay gates on each new environment/backend/GPU family. A
   six-row CPU development test is not the full-data GPU gate.
4. Choose a `ready` preregistered trial. Claim it atomically on GitHub before
   submission. Read back the remote claim. A chat/issue comment is not a lock.
5. Record scheduler allocation, compute profile, exact code/spec/bundle/parent,
   owner, start time, absolute deadlines, and bounds. Never override Slurm's
   `CUDA_VISIBLE_DEVICES`. One independent trial per allocated GPU.
6. Run through the external supervisor. No training on cluster login nodes,
   unbounded loops, hidden retries, duplicated GPU owners, or in-place restarts.

## After every outcome

Preserve checkpoints/logs/telemetry before scratch expires. Run saved-array QA.
Upload an immutable run release, verify its downloadable hash, add the small
result JSON on a unique result branch, regenerate `RESULTS.md`, run CI and open
a PR. Include failed attempts even if they have no endpoint. Never overwrite a
record or release asset. Amend conclusions through new decision records.

If a job disappears, query `squeue`/`sacct`, inspect its process/cleanup/output,
and reconcile its remaining budget. A disconnected agent is not a stopped job.
Never steal a claim automatically because a lease or chat session looks old.

## Work that can proceed in parallel

CPU agents: input/artifact verification, tests, saved residual/nuisance analyses,
resource audits, parameter-count inventories, claim/result PR review, and bounded
CPU reference trials. GPU agents: distinct claimed whole-data replay/fit cells.
One GPU does not accelerate another trial merely by using DDP; this initial
runtime deliberately has no distributed single-model optimizer.

## Source and credentials

Access is owner-only: Dustin and his agents use owner-approved authentication
under `zetanaut`. Do not invite collaborators or create separate GitHub accounts
for agents. Every agent still needs a unique agent/site/session owner ID, an
isolated checkout and branch, and its own atomic trial claims; the shared GitHub
account does not distinguish workers or permit duplicate launches.

Keep GitHub tokens and UVA credentials off compute nodes, out of Slurm exports,
logs, committed files and prompts. Publish from a login/transfer workstation.
Default repository visibility is private. There is no blanket redistribution
license for historical scientific assets; see `NOTICE.md`. Do not push raw
workspace histories, personal onboarding, agent thread IDs or credential stores.
