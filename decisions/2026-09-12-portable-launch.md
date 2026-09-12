# Portable collaboration launch

Decision: establish one private GitHub study repository with a frozen relocatable
baseline input release, atomic claims, bounded single-GPU/CPU trials, and
immutable result artifacts. Scale independent cells across local/UVA GPUs rather
than silently introducing distributed single-model optimization.

Ready first: PORT whole-data replay. No architecture winner or portable GPU
speedup is claimed. Source/model transport passed the recorded limited CPU
comparison; whole-data target-environment validation remains a mandatory gate.

Subsequent work follows W01–W08 and P0–P5. The initial runtime intentionally
does not guess the unpinned original family or pretend all future initialization
and conditioning variants are already implemented. New agents may implement
and preregister those in-scope comparisons, with evidence, under this workflow.

Publication state and remote access must be verified before handing a clone URL
to the UVA agent. No cluster job or new GPU fit was launched during preparation.

