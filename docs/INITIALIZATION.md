# Controlled initialization — development status

`tmdlab.initialization.widen` transports a CPU float64 Nested-FiLM model into a
wider model at unchanged depth and fixed conditioning/species/CS definitions.
It is a saved-parameter operation, not an executable trial initialization route.

For each boundary, the first old-width radial channels are copied. In every
block, old output rows retain their old inputs and have zero weights on new
inputs. FiLM gamma and beta rows are copied to their respective widened slices
(all gamma rows precede all beta rows). The output head retains old weights and
has zero weights on new features. Thus the retained channels and boundary
function are unchanged in exact arithmetic. The entire CS module is copied.
New feature internals remain seeded and nonzero. New output and cross-channel
connections can learn; initially insulated new internals do not falsely acquire
gradients before those connections move.

`tmdlab.paired_starts` now makes deterministic **candidate** sets in the
correct order: it first makes distinct, bounded narrow parameter vectors from
three distinct narrow seeds, then applies `widen` to each exact narrow candidate.
The widening seed therefore only initializes added features and cannot be
misrepresented as an independent narrow start. Candidate receipts bind source
and candidate parameter hashes, perturbation norm and zero model calls. The
factory returns in-memory models only; it does not write checkpoints, register
trials, assert feasibility or grant an optimizer budget.

CPU tests use nonzero learned parameters and cover widths8/16/24 at unchanged
depth1/2/3, boundary values and b derivatives, CS equality, parameter counts,
source immutability and non-dead new output features. Floating-point transport
is checked numerically, not claimed bitwise identical across BLAS backends.

Still required before a scientific width matrix:

- Exact input model/source/parameter identities and a registered new-start format.
- All2,290 observable predictions, fixed metric, positivity and directional replay
  on the actual backend. Boundary-function tests are not this gate.
- At least three explicitly distinct paired feasible starts. Widen each common
  narrow start to its wider partners; do not relabel the same deterministic
  narrow trajectory as independent repetitions by changing only widening seeds.
- A bounded, preregistered feasibility search, with all perturbation, repair,
  replay and model-call costs counted. Do not change physics or clip predictions.

No new scientific start, optimizer reset, depth transport or family comparison
is authorized solely by merging this helper.
