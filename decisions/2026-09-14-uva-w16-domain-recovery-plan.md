# Width-16 A03: recover the boundary failure within the original allowance

The user requested investigation of the UVA failure independently of the local
width-8 diagnosis, and a fix. The [A02 outcome](2026-09-14-uva-w16-domain-failure-outcome.md)
preserves the failed execution, valid 183-update endpoint, charged calls and
archive. This plan applies the reviewed shared PR41 repair to a new UVA trial;
it changes no physics, data, metric, positivity floor or convergence criteria.

## Evidence and remaining question

The archived traceback identifies the first candidate forward for cumulative
update 184. The full-size L-BFGS direction is finite and descending but has
norm 555376.0677910727. The old incoming-boundary guard combines nonfinite
output and representational zero damping in one error message.

A bounded NumPy-only engineering probe of the first operator's 13424 incoming
nodes found finite candidate logits down to about -129954 and zero softplus
values at 4800 nodes for alpha=1. The accepted state has no zero damping in this
probe. This is boundary-only CPU evidence, not a full-observable evaluation or
an allocated GPU reproduction. Its BLAS direction reduction differed slightly
from the archived norm; no saved history was changed to force equality.

The definitive test uses the ordinary first candidate in A03, on the qualified
A6000 after the unchanged whole-data replay gate. PR41 first checks boundary
output finiteness and then positive damping, so a logged
`boundary_zero_damping` verdict establishes finite boundary output followed by
zero damping. A `boundary_nonfinite` verdict establishes the other original
predicate instead; preserve that distinction rather than asserting identical
local/UVA mechanisms. All these candidate forwards remain inside the worker's
counted time and call ledger; no separate uncharged full-data probe is needed.

## Exact repair and state

Opt into `optimizer.candidate_errors = reject-forward-domain-errors-v1`.
Only typed candidate forward/fixed-metric domain failures become backtracking
rejections. Preflight, probes, VJPs, endpoints, unrelated errors, resource stops
and deadlines remain fatal. Keep unit initial alpha, halving, Armijo and the
32-attempt limit. There is no clipping, damping floor, rescaling or history reset.
The shared magnitude-based curvature certificate validates cancellation-prone
pairs without rewriting s/y/rho or changing two-loop arithmetic.

Use restart `7597e89266238b98e0c3006a628977dbd272debed9a302e9a2c5dd4504e42543`,
object `0d5a6794442b8deb54232b0d27482096128351562d6e7d8364d38145e66f71b2`.
It preserves all optimizer arrays, 15 pairs, 21 convergence states, 183 accepted
updates and q/N 16.364263303504803. Its 1583 forwards and 205 VJPs include the
failed final forward after checkpoint-137. Prior model time is
11214.05901648308 seconds, including the older 46-update parent.

## Bounded resource opportunity

The original seven-hour segment spent 8930.176312024996 of 25200 seconds.
A03 receives 16269 integer model seconds, rounded down from 16269.823687975004;
its setup, replay and all optimizer calls count in that window. Reserve 300
seconds inside it for the endpoint, followed by 1200 seconds saved-only QA.
The name retains `7h` to identify the original envelope, not a fresh seven hours.

The UVA specialist approved one A6000, one node/task, two CPUs, 16 GiB host RAM,
five-hour Slurm walltime, public `gpu`/`gpu:a6000:1`, `spinquest_standard`,
`--export=NIL` and no requeue. The 17469-second application/QA ceiling leaves
531 seconds for allocated preflight and final retention, compared with about
69 seconds setup and seconds of terminal retention in A02. Reuse the proven
launcher and shared static validator; all new pins and guards run before submit.

Remaining guards are 3959 new updates, 15096 forwards and 8047 VJPs. Cumulative
ceilings remain 4142/16679/8252 and 27484 model seconds. No new compute grant,
optimizer experiment, width-8 duplication or standalone GPU qualification.

## Validation and decision

Require CPU tests/CI, exact spec and imported-state checks, independent review,
clean frozen source, an atomically read-back new claim and successful static
launcher validation. In the allocation retain full input/checkpoint validation
and CUDA/NVML identity verification. Before optimization require whole-data
parent prediction/q/penalized-gradient replay and two directional checks at
the existing tolerances; restore the saved optimizer point after replay.

Inspect update 184's direction and candidate diagnostics. The recovery criterion
is a recorded rejection of the formerly fatal candidate followed by a feasible,
Armijo-accepted update beyond 183. A changed error label or a finite boundary
alone is insufficient. If recovered, continue under the remaining window with
reports every 32 new accepted updates and atomic checkpoints at every update.
Convergence remains the unchanged two-window test. Preserve any new failure;
no unchanged retry loop or silent expansion of limits is authorized by this plan.
