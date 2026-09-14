# Width-16 A02: candidate-domain failure after 137 new updates

Run `continuation-w16-feasibility-7h-uva-a02-69f3be55d0f8`, Slurm job
19946083, ended on 14 September at 19:47:56 UTC. Execution failed; its saved
endpoint is valid and unconverged. It used the reviewed source
`f79b01080176eecd8dfa083e9c6c20ff0de46b59` on one RTX A6000, two CPUs and
16 GiB host RAM under `spinquest_standard`. The earlier A01 launcher failure
consumed two allocation seconds and zero model work; its separate record is
preserved in the [A02 plan](2026-09-14-uva-w16-long-training-a02-plan.md).

## Outcome and retained evidence

- Accepted updates: 137 new, 183 cumulative, starting from 46.
- q/N: 16.56779534832199 to 16.364263303504803, a reduction of 0.2035320448.
- Charged calls: 1288 new forwards and 145 new VJPs; cumulative 1583 and 205.
- New positivity-infeasible candidates: 994; new line-search rejections: 1000.
  The final failed forward returned no prediction vector and was not a
  completed rejection in the historical counters.
- Model-window time: 8930.176312024996 seconds, including setup/replay in the
  supervisor window; ancestor-inclusive total 11214.05901648308 seconds.
- Slurm allocation: 2h30m01, FAILED 2:0. Supervisor resource stop: absent.
  Cleanup and saved-array audit passed; no memory/telemetry stop is indicated.
- Saved predictions: all 2290 finite and strictly positive, minimum T/sigma
  4.351463134481926e-05. Both convergence windows fail; penalized-gradient
  maximum 0.2034840350198679. Final raw gradient is explicitly missing because
  the exception preceded endpoint evaluation.
- High-COMPASS 188-row residual RMS remains 7.979179945743357. Persistence
  does not establish an irreducible floor or an architecture ranking.

The immutable archive includes the scientific run, allocated validation,
submitted source/batch provenance, and terminal scheduler accounting. It was
downloaded separately and matched byte-for-byte before collection/import:
[run artifact](https://github.com/zetanaut/tmd-global-fit-lab/releases/download/run-continuation-w16-feasibility-7h-uva-a02-69f3be55d0f8/continuation-w16-feasibility-7h-uva-a02-69f3be55d0f8.tar.gz),
SHA256 `e80631fc27831534e18f5f013f0fdf9b2b5b7bbbe9d6e7bc33c41354857e3b3c`.
The archive root contains the scientific directory at
`outputs/continuation-w16-feasibility-7h-uva-a02`.

## Failure localization and recovery boundary

The first candidate for cumulative update 184 failed at the incoming boundary
guard with `ValueError: nonfinite boundary or zero damping; no clipping`.
Its saved L-BFGS direction norm was 555376.0677910727 and g dot p was
-21809.531766169064. The direction was finite and descending, so the existing
fallback did not apply. The old message combines two predicates and alone
cannot distinguish nonfinite boundary output from representational zero damping.

The local width-8 repair in PR41 separates these numerical-domain errors and
allows an explicitly opted-in trial to reject candidate forward failures within
the existing backtracking loop. Its validation-only curvature certificate also
addresses cancelling saved dot products without rewriting history. That repair
is a candidate for UVA recovery, not proof that the UVA failing step has already
been completed. A new bounded attempt must verify the actual boundary failure,
unchanged whole-data restart predictions/penalized gradient and directional
checks, then record acceptance beyond update 183. No clipping, history reset,
physics/floor/convergence change or additional seven-hour grant is justified.

Imported restart identity:
`7597e89266238b98e0c3006a628977dbd272debed9a302e9a2c5dd4504e42543`;
object SHA256 `0d5a6794442b8deb54232b0d27482096128351562d6e7d8364d38145e66f71b2`.
All optimizer arrays, 15 curvature pairs and the 21-state convergence window
are byte-equivalent at array level. Only the counters differ: the one failed
forward after checkpoint-137 is added, taking 1582 to 1583. The
[import validation](../validation/uva-w16-a02-restart-import-20260914.json)
records the independent archive digest check and all curvature certificates.

The remainder of the original 25200-second opportunity is
16269.823687975004 seconds. A successor may use at most 16269 integer model
seconds, including its own setup/replay/probes and endpoint reserve, with the
unchanged cumulative ceilings 4142 updates, 16679 forwards, 8252 VJPs and
27484 model seconds. It requires a new reviewed specification and claim.
