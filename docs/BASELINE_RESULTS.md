# Historical evidence — not portable trial completions

Snapshot updated from the closed V7 receipts and independent saved-array review
13 Sep2026. See [immutable import](../evidence/p0-v7-2026-09-13/index.json) and
[overlay usage](CHECKPOINT_OVERLAYS.md). P0 is complete but unconverged.
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
| Assigned w24 V7 final (parent064 +32) | 16.807363794 | 7.979771258 | 7.474290 | 6.342844 |
| Assigned w8 V7 final (parent083 +13) | 16.955715679 | 7.979834084 | 7.030463 | 5.712184 |
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

V7 closed at 22:14:27 UTC on 12 September. The three selected starts each now
have 160 accepted updates: 64 screening +96 refinement. The correct w16 final
remains the byte-identical released reference. V7's w24 fails both plateau
windows; w8's 13 new updates cannot supply 21 states. Do not splice histories
across the explicitly declared optimizer reset. w16's prior windows also failed.
All three endpoints are strictly positive; minimum T/sigma is 5.81920e-6 (w24),
3.87002e-6 (w8), and 0.00968457 (w16). Positivity does not establish convergence.

The 13 September independent audit verified 93 source pins, q/N within7.11e-15,
and DY profile closure within7.28e-12. The import rechecked all 93 pins and used
saved-array algebra only. V7 w24 improves total q/N while its named DY pulls and
experimental nuisance penalty increase; w8's named pulls slightly decrease.
The persistent ~7.98 high-COMPASS residual RMS is not the small parent-to-final
prediction change. All188 high-COMPASS rows remain underpredicted. V6 w8 is a
repeat of essentially the same path, not an independent seed or 13 additional
unique updates; retain its separate execution cost.

V7 terminal costs are w24 217 forwards/40 full calls/32 accepted and w8
141/19/13, respectively. Historical cumulative receipt totals are qualified:
older attempt002 adds another10 forwards/four full calls with zero accepted
updates. Unknown elapsed time and true worker peaks remain unknown, not zero;
the historical `resource_peak` field is preflight-only.

V8 is a CPU-only safeguard repair: seven surrogate tests, zero new model/GPU
calls and no new compute allowance. Python-signal/sleep tests do not certify
interruption of a stalled native CUDA call, nor retroactively certify V7 peaks.
Its copied P0 allocation is consumed. Native P1 is separately assigned to the
Manager; it does not wait for portable qualification. This import neither
launches P1 nor claims current native-run status, PORT clearance or UVA submission.

Portable preparation evidence: `validation/port-equivalence-2026-09-12.json`
checks six DY/SIDIS rows at all three widths. Portable versus original CPU
predictions and fixed-cotangent VJPs matched exactly in that check; saved-prediction
differences were <=2.80e-14 fixed sigma. This limited test does not replace PORT.
