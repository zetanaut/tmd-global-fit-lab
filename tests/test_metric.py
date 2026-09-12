import numpy as np
from scipy.linalg import cho_factor
from tmdlab.metric import Metric

def tiny_metric():
    m=Metric.__new__(Metric)
    m.data=np.array([1.,2.,3.]);m.n=3
    m.cov=np.array([[2.,.4,0.],[.4,3.,.2],[0.,.2,1.]])
    m.sigma=np.sqrt(np.diag(m.cov));m.chol=cho_factor(m.cov,lower=True)
    return m

def test_fixed_metric_and_barrier_directional_derivative():
    m=tiny_metric();values=np.array([.8,1.3,2.5]);d=np.array([.2,-.1,.3]);mu=1e-6;h=1e-5
    p=m.score(values,mu)
    fd=(m.score(values+h*d,mu)["objective"]-m.score(values-h*d,mu)["objective"])/(2*h)
    assert abs(fd-p["cotangent"]@d)<1e-9
    r=m.data-values
    assert abs(p["q_per_measurement"]-r@np.linalg.solve(m.cov,r)/3)<1e-12

def test_full_observable_positivity_is_not_clipped():
    m=tiny_metric()
    assert m.score(np.array([-.01,1.,1.]),1e-6) is None
    assert m.score(np.array([0.,1.,1.]),1e-6) is None
