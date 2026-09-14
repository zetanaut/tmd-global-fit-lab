# A03 prelaunch curvature-validation correction

This supersedes the *unlaunched* A02 implementation from the
[domain-repair plan](2026-09-14-local-w8-domain-repair-plan.md). The scientific
parent is still A01's exact 252-update state and the opportunity is still 4993
model seconds. There was no A02 worker, model dispatch, accepted update or
charged model-window time. Its immutable spec and claim remain preserved:
claim `aa679f728b453de5e4b3d1e4a3e71d57b00373f4`, source
`7b0109e6c0b384b1736b081016d70ba919bcdc0a`.

## Additional prelaunch finding

[CI run 34882274577](https://github.com/zetanaut/tmd-global-fit-lab/actions/runs/34882274577)
passed all CPU tests, but structural validation rejected the newly imported
curvature history. The same issue was reproduced locally by selecting the
NEHALEM OpenBLAS kernel for the read-only checker. No scientific GPU run was
started after this failure.

The old validator required relative agreement within 1e-13 between saved rho
and a newly computed reciprocal dot product. Several saved sTy values are
heavily cancelling. One has a summed absolute product magnitude
0.00015921901200901986, but a final dot of only 3.842793466156054e-10. Its saved
dot differs from accurately summed binary64 products by about 1.54e-11
*relative*, despite an absolute difference of only about 5.94e-21. A fixed
relative comparison incorrectly treats legitimate reduction roundoff as
corruption.

## Validation-only remedy

The error of a floating-point dot product is bounded in terms of the summed
absolute products, not merely the magnitude of a cancelling result. See
[Jeannerod and Rump, 2013](https://epubs.siam.org/doi/10.1137/120894488), and
[LAPACK Working Note 149, Appendix A](https://www.netlib.org/lapack/lawnspdf/lawn149.pdf)
for the floating-point/underflow model.

The validator computes a reference with `math.fsum` of binary64 products and
uses the conservative bound `2*gamma_(n+4)*sum(abs(s*y))` plus subnormal-rounding
allowance and outward rounding. This accounts for reduction, product and
reciprocal roundoff; the allowance depends on actual pair magnitudes and
dimension, not an empirically enlarged relative tolerance. It requires the
whole certified curvature interval to remain above the unchanged 1e-12
retention threshold. Ambiguous or mismatched pairs still fail closed.

No saved s, y or rho is modified. No hash, manifest, history-filtering rule,
two-loop computation or optimizer direction is recomputed differently. File
hash validation remains exact. The change only verifies the same bytes across
valid BLAS reduction orders. Tests cover the archived cancelling pairs, a
simple cancellation example, corrupted reciprocals, below-threshold curvature,
and intervals whose roundoff uncertainty is too large to certify positivity.
The finite-domain repair and all scientific gates from the A02 plan remain.
Prospective accepted snapshots are certified before mutating the live accepted
point/counters, so a genuine certificate failure preserves the prior committed
endpoint with no spurious accepted update. This ordering changes no accepted
step algebra or charged model calls; it has an injected-failure regression.

## Execution boundary

The new immutable A03 spec uses its own claim and source commit. It retains the
A01 restart and all cumulative caps without a new compute grant. Before launch,
require the full CPU suite, structural checks under default and NEHALEM kernels,
and green CI. Full-data replay and directional checks still precede any GPU
optimization. Confirm an accepted step beyond 252 after rejecting the original
fatal candidate; do not infer conditioning or convergence from recovery alone.
