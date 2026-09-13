"""Deterministic shared L-BFGS recursion; no model or device dependencies."""
def two_loop(gradient,history):
    q=gradient.copy(); alphas=[]
    for s,y,rho in reversed(history):
        alpha=rho*float(s@q); alphas.append(alpha); q-=alpha*y
    gamma=1.
    if history:
        s,y,_=history[-1]; gamma=max(min(float(s@y)/max(float(y@y),1e-300),1e6),1e-12)
    r=gamma*q
    for (s,y,rho),alpha in zip(history,reversed(alphas)):
        r+=s*(alpha-rho*float(y@r))
    return r
