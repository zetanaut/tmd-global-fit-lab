# Historical exact-data closure baseline plan

## Decision and question

Dustin requested an additional baseline using a historical study's exact data
set and the present fitting technique.  The benchmark is adopted as a required
sanity gate for the data and fit machinery before a likelihood-v2 production
fit.  The preferred study is PV17 (`arXiv:1703.10157`) because its 8,059 points
directly motivate the current data-coverage concern.

The question is deliberately split in two:

1. Can a frozen historical model, data construction, theory, and likelihood be
   reproduced by an independent implementation?
2. With those elements unchanged, can the current DNN fitting method obtain a
   comparable or better score and a compatible TMD extraction?

Changing data, theory order, cuts, normalization treatment, covariance, and
parametrization at once would not answer either question.

## Current readiness decision

PV17 is provisionally selected but is not yet executable as an exact benchmark.
The [source audit](../analysis/historical-closure-baseline-20260915/README.md)
found public historical source, data, grids, row counts, and official parameter
replicas.  It did not find a self-identifying full-data final configuration and
prediction receipt.  In particular, the initial public input card is configured
for a different PDF and Z-only execution while its saved output has the right
8,059-row accounting but a non-published score.

The H0 row subgate now passes.  The executable receipt reconstructs 21,951
candidate numeric source rows, 8,283 rows after cuts, and 224 COMPASS
normalization spectra.  Excluding each spectrum's fixed lowest-`PhT`
denominator gives exactly 8,059 effective points and every published
experiment count.  The local value-bearing manifest is ignored rather than
redistributed and is bound by SHA-256
`3b40402fc42e3a7c85a0c3842e97cce3dbdbbb872de7478649dbe8c60e4a83c4`.

Therefore the next action is the remaining H0 final-card/full-prediction-receipt
search, followed by historical-model replay (H1).  No DNN optimization is
authorized until both pass.  H1 may use the local GPU if its theory replay
benefits; the validation dependency, not CPU hardware, is authoritative.  If
public history cannot close the final run, request the exact card/predictions
from the authors; if those remain unavailable, promote MAPTMD22 only after its
own exact artifact binding passes.

## Fixed gates

The executable sequence and numerical tolerances are fixed in the
[audit record](../analysis/historical-closure-baseline-20260915/README.md):

- H0: exact ordered 21,951-candidate/8,283-selected manifest, 224 COMPASS fixed
  constraints, 8,059 effective points, and complete final-run identity;
- H1: historical 11-parameter replay with prediction and per-block score
  closure;
- H2: data-blind distillation of the PV17 functions into the DNN and exact-row
  prediction closure;
- H3: sequential same-data DNN fits on the one local GPU from the distilled
  state and at least two independent feasible starts; and
- H4: preregistered TMD-grid/envelope comparison plus paired grouped holdouts in
  which both the PV17 form and DNN are refit on identical training folds.

The in-sample DNN sanity threshold is global `q/N` no more than 0.02 above the
reproduced reference and no process-block `q/N_block` more than 0.10 above it.
This is not the superiority decision.  The DNN has much higher effective
complexity, so a lower training `q/N` becomes meaningful only with the paired
held-out comparison and stable TMD behavior.

The historical paper's `chi2/d.o.f.` and this project's `q/N` are recorded
separately.  No effective DNN degree-of-freedom count or p-value will be invented.

## Relationship to the current study

This benchmark is isolated from both the frozen 2,290-row likelihood and the
proposed full-source likelihood-v2.  It changes no existing observation,
operator, covariance, checkpoint, result, or architecture conclusion.  Its
historical theory and error treatment are controls to reproduce, not defaults
to import into likelihood-v2.

The single RTX 4090 runs only one H2/H3 cell at a time after the CPU gates.  Each
fit gets a separately registered time/convergence opportunity with generous
count ceilings; it must not inherit the obsolete 192-update cap.  Reference,
distillation, start construction, failed candidates, optimizer calls, and TMD
readout costs are all retained.

No result is called a closure pass merely because its scalar score lies near
1.55.  The exact rows, transformations, predictions, process decomposition,
and supported TMD functions must close together.
