# Historical evidence — not portable trial completions

Snapshot from the existing study and independent saved-array review12 Sep2026.
All q/N use the fixed 2,290-row metric. Original widths8/16/24 have
1,570/2,882/4,706 parameters. Historical identities and source artifacts belong
to the released input provenance, not to a fictitious portable runtime run.

The completed screening had24 cells: three widths x eight starts,64 accepted
steps per cell. Best q/N: w8/S01 17.202162; w16/S02 17.189029; w24/S00 17.194659.
All were still improving; none established plateau. Width24 had the better
median, but start spread and late-step improvements prevented winner selection.

| Historical saved endpoint | q/N | High-COMPASS raw RMS | E772 pull | E605 pull |
|---|---:|---:|---:|---:|
| Assigned w24 checkpoint064 | 16.863796532 | 7.979614604 | 7.436866 | 6.316500 |
| Alternative w24 checkpoint065 | 16.868490339 | 7.979612608 | 7.474047 | 6.320255 |
| Alternative-branch w24 V6 final | 16.804830241 | 7.979795541 | 7.382081 | 6.275841 |
| Assigned w8 checkpoint083 | 16.960843107 | 7.979778518 | 7.058223 | 5.723511 |
| w8 V6 final | 16.955715679 | 7.979834084 | 7.030463 | 5.712184 |
| w16 original refinement final | 16.661796605 | 7.979384360 | 7.754104 | 6.517480 |

The six-endpoint independent saved-array check reproduced q/N within3.55e-15;
DY profile closure was within7.28e-12. All had2,290 finite positive predictions.
All188 wholly-high-recoil COMPASS rows were underpredicted at every endpoint.
RMS is in fixed marginal-sigma units; these are correlated diagnostics, not
independent significances. Named pulls are existing conditional prior units.

V6's w24 result followed an alternative parent and is diagnostic, not completion
of the assigned checkpoint064/+32 trajectory. Its numerical information is still
usable. V6 w8/w24 slightly reduced named pulls relative to their actual parents;
do not conflate persistent strain with worsening in every update. w16's lower
score does not establish an architecture winner or greater optimization maturity.

Older unconstrained 192-update CPU continuations reached16.198207/16.319574 but
had15/47 negative DY predictions. Their comparison does not measure an isolated
“cost of positivity” because trajectories/budgets differ.

At the last connector review, the corrected local V7 had accepted the exact P0
scope and was running. Before P1, import its final closed receipts and artifacts
through W01; this snapshot must not be treated as live local-run status.

Portable preparation evidence: `validation/port-equivalence-2026-09-12.json`
checks six DY/SIDIS rows at all three widths. Portable versus original CPU
predictions and fixed-cotangent VJPs matched exactly in that check; saved-prediction
differences were <=2.80e-14 fixed sigma. This limited test does not replace PORT.

