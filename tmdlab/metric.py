"""Fixed full covariance algebra and saved-array scientific diagnostics."""
import numpy as np
from scipy.linalg import cho_factor, cho_solve

class Metric:
    def __init__(self, bundle):
        with np.load(bundle.file("metric.npz"), allow_pickle=False) as z:
            self.arrays = {k:z[k].copy() for k in z.files}
        a = self.arrays
        self.data, self.cov = a["data"], a["covariance"]
        self.n = self.data.size
        if self.n != 2290 or self.cov.shape != (self.n, self.n) or not np.array_equal(self.cov, self.cov.T) or not all(np.isfinite(x).all() for x in a.values()):
            raise ValueError("invalid full metric")
        self.sigma = np.sqrt(np.diag(self.cov))
        if np.any(self.sigma <= 0):
            raise ValueError("nonpositive marginal variance")
        self.chol = cho_factor(self.cov, lower=True)
        self.info = bundle.metric_info

    def score(self, values, mu):
        values = np.asarray(values, dtype=np.float64)
        if values.shape != self.data.shape or not np.isfinite(values).all():
            raise ValueError("invalid predictions")
        residual = self.data-values
        precision = cho_solve(self.chol, residual)
        q = float(residual @ precision)
        margin = values/self.sigma-1e-8
        if not np.all(margin > 0):
            return None
        barrier = float(-mu*np.mean(np.log(margin)))
        cot = -precision/self.n-mu/(self.n*self.sigma*margin)
        return dict(values=values.copy(), q_per_measurement=q/self.n, objective=q/(2*self.n)+barrier, barrier=barrier, cotangent=cot, raw_cotangent=-precision/self.n, min_T_over_sigma=float(np.min(values/self.sigma)))

    def describe(self, values):
        residual = self.data-values
        precision = cho_solve(self.chol, residual)
        q = float(residual @ precision)
        a = self.arrays
        A = np.column_stack((a["DY_responses"], a["U"][:743]))
        D = a["DY_diagonal"]
        if a["U"][743:].any():
            raise ValueError("DY-only nuisance decomposition no longer valid")
        eta = np.linalg.solve(np.eye(A.shape[1])+(A.T/D)@A, A.T@(residual[:743]/D))
        adjusted = residual[:743]-A@eta
        penalty = float(eta@eta)
        closure = abs(float(adjusted@(adjusted/D)+penalty-residual[:743]@precision[:743]))
        if closure > 1e-7:
            raise ValueError("DY profile closure failed")
        names = self.info["DY_nuisance_ids"]
        high = np.asarray(self.info["high_COMPASS_indices"], dtype=int)
        if high.size != 188 or len(set(high.tolist())) != 188:
            raise ValueError("exact 188-row diagnostic region required")
        def describe(ix):
            r = residual[ix]/self.sigma[ix]
            return dict(rows=int(r.size), mean=float(r.mean()), rms=float(np.sqrt(np.mean(r*r))), underpredicted=int((residual[ix]>0).sum()))
        return dict(q_per_measurement=q/self.n, finite=True, negative=int((values<0).sum()), zero=int((values==0).sum()), min_T_over_sigma=float((values/self.sigma).min()), high_COMPASS=describe(high), processes={"DY":describe(slice(0,743)), "HERMES":describe(slice(743,1087)), "COMPASS":describe(slice(1087,2290))}, DY_nuisances=dict(zip(names, map(float,eta[:len(names)]))), experimental_nuisance_penalty=float(eta[:len(names)]@eta[:len(names)]), numerical_nuisance_penalty=float(eta[len(names):]@eta[len(names):]), DY_adjusted_RMS_fixed_sigma=float(np.sqrt(np.mean((adjusted/self.sigma[:743])**2))), DY_profile_closure_abs_error=closure)

