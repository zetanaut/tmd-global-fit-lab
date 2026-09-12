# Trial result contract

A result has three distinct verdicts: execution status, numerical/scientific
endpoint validity, and convergence/comparison interpretation. A passed replay
or completed phase schedule does not imply plateau or physical adequacy.

## Keep the full run archive

Required when available: trial specification, launch/owner/claim/environment,
worker and supervisor summaries, complete calls/counters/accepted-step records,
checkpoints, last feasible theta/predictions, raw and penalized gradients or
explicit missing reason, preflight/directional checks, sampled resources and
actual sampled maxima, saved-array audit, scheduler accounting, logs and cleanup.
Failed setup may have no endpoint; record failure rather than inventing one.

For each endpoint report: q/N; positivity/zero/negative counts and minimum T/sigma;
all-process raw residual diagnostics;188-row high-COMPASS residuals; named DY
nuisance shifts and separate experimental/numerical penalties; adjusted residual
diagnostics and closure; plateau eligibility/results; exact lineage; update/call/
time costs; and environmental differences. Normalize predictions by the fixed
marginal sigma, never by a potentially tiny current prediction.

## Publish and submit

From a credentialed transfer workstation, first inspect logs for credentials or
unrelated personal data. Archive a single exact run directory; do not package a
home directory, environment, raw workspace or symlinks to other trees.

```bash
# RUN_ID is the unique launch run_id, not a recycled architecture name.
tar -C /ABS/output-parent -czf artifacts/RUN_ID.tar.gz RUN_DIRECTORY
sha256sum artifacts/RUN_ID.tar.gz
gh release create run-RUN_ID artifacts/RUN_ID.tar.gz \
  --repo zetanaut/tmd-global-fit-lab \
  --title 'RUN_ID' --notes 'Immutable trial artifact; see result PR for verdict.'
```

Use a new tag and asset every time; never use `--clobber`. Download it to a
separate directory and verify the SHA256 before recording the URL. Then:

```bash
git switch -c results/RUN_ID
python -m tmdlab.results collect --run /ABS/RUN_DIRECTORY \
  --artifact artifacts/RUN_ID.tar.gz \
  --artifact-url https://github.com/zetanaut/tmd-global-fit-lab/releases/download/run-RUN_ID/RUN_ID.tar.gz
python -m tmdlab.results report
python scripts/check_repository.py
python -m pytest -q
git add results RESULTS.md
git commit -m 'Record RUN_ID with execution and saved-array audit'
git push -u origin results/RUN_ID
gh pr create --title 'Result: RUN_ID' --body-file /ABS/result-review-notes.md
```

The collector does not itself upload or confirm remote availability; the
download-and-hash check is mandatory. Keep its evidence with the result PR.
GitHub release assets accommodate large artifacts; individual assets must stay
within GitHub's current release limits. Large files do not belong in normal Git
history. See [GitHub large-file guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## Review checklist

Confirm spec/code/bundle/parent match the remote claim; all available timestamps
and costs are retained; no unexpected rows or covariance changes; GPU precision
and hardware gates passed; cleanup/scheduler outcomes agree; saved endpoint hashes
match downloaded artifacts; q and DY profile close; positivity is measured on
all2,290 raw observables; plateau uses21 states at unchanged mu; residual changes
are not mislabeled as residual levels; and conclusions qualify censored or
unconverged comparisons. New implementation/hardware results are not silently
merged with historical scores as though their optimization histories matched.
