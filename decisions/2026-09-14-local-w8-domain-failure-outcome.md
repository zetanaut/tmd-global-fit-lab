# Local width-8 numerical-domain failure — 14 September 2026

The instrumented run `continuation-w8-feasibility-2h-local-a01-09192af5f429`
ended at 17:20:58 UTC with failed execution, a valid saved endpoint, and no
convergence. This is not a count/time/resource stop. Source was
`59b834fcc21e3f6786563ac7600b0315a56c5de2`; the GPU was the qualified local
RTX 4090. The enlarged policy operated beyond the historical 192-update cap.

## Retained evidence

- New accepted updates: 75; cumulative: 252 (parent: 177).
- q/N: 16.448895619388466 to 16.411446133424036.
- New charged forwards/VJPs: 911/78, including the failed final dispatch.
- Cumulative forwards/VJPs: 2349/283.
- New infeasible candidates: 751; rejected candidates: 752. The fatal candidate
  is a charged forward, not a completed rejection in the original counters.
- Model window consumed: 2206.107684707269 seconds; cumulative model-window
  time: 8762.75273999467 seconds. The original 7200-second opportunity was not
  fully consumed. A successor must subtract this cost, not reset the grant.
- Both convergence windows fail; terminal penalized-gradient maximum is
  0.4090572535270205. The final raw gradient is explicitly missing.
- Saved-only audit passes: all 2290 predictions finite and strictly positive,
  minimum T/sigma 5.000262800733636e-7; no clipping or removed observations.

The complete original directory was archived without mutation, published, then
downloaded independently and compared byte-for-byte with `tar --compare`.
Archive SHA256:
`95e9c9da27cf4d1d20c9fc145e4e442ef2f77df568f84e57caebd14e678b7744`.
[Immutable archive](https://github.com/zetanaut/tmd-global-fit-lab/releases/download/run-continuation-w8-feasibility-2h-local-a01-09192af5f429/continuation-w8-feasibility-2h-local-a01-09192af5f429.tar.gz).
The associated immutable result is
`results/continuation-w8-feasibility-2h-local-a01/continuation-w8-feasibility-2h-local-a01-09192af5f429.json`.

## Failure localization

The first candidate for cumulative update 253 failed in the incoming boundary
guard: `nonfinite boundary or zero damping; no clipping`. Its L-BFGS direction
norm was 12572.15954712584, versus 50.99537305061753 at the preceding update;
the accepted parameter norm was 22.599957934437782. The direction was finite
and descending (g dot p = -833.7636807056105), so the existing fallback did not
apply. No candidate prediction vector was returned, hence no row-level verdict
for that fatal dispatch appears in the original line-search log.

A bounded CPU boundary-only engineering probe reconstructed the exact direction
from saved curvature pairs and gradient. It evaluated the 13424 incoming nodes
of the first operator, `obs:E288_200:0`, with zero full-observable model calls
and zero optimizer updates. At alpha=1 the finite damping logits ranged from
-2647.268649420182 to 3391.775623936569 and softplus rounded to zero at 6400
nodes; alpha=0.5 had 3008 zero-damping nodes. At alpha=0.25 and 0.125 this
boundary check passed. This does NOT establish full-observable feasibility or
Armijo acceptance at those smaller steps.

Thus the immediate numerical mechanism is softplus underflow at an oversized
trial step. The run-level failure occurs because this model-domain exception
escapes the line-search rejection path. The saved accepted state itself remains
valid. Large direction growth and tiny curvature cosines motivate further
conditioning review; they do not prove a specific Hessian condition number or
an irreducible fit floor.

## Authorized next action

The owner requested investigation and a fix. Test a narrowly typed, opt-in
candidate-domain rejection policy: shrink invalid forward candidates without
clipping, changing the damping formula, resetting curvature history, changing
Armijo, or relaxing positivity/convergence. Keep unexpected, input, replay,
VJP, deadline, and hardware errors fatal. Preserve this failed attempt and all
costs. A new trial/claim may resume the exact audited state only after tests and
the unchanged full-data replay/derivative gate; its budget must be the remaining
original opportunity. No automatic retry loop or other GPU/architecture arm.
