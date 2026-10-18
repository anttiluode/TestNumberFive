"""Exploratory, NOT a registered gate: mode shifts after localized experience.

Generalized modes G phi=lambda C phi: a small membrane shunt perturbation
obeys first-order Delta lambda = sum_i Delta leak_i * phi_i^2.
A cable edge change would instead use Delta g*(phi_a - phi_b)^2.
"""
import json
from pathlib import Path
import numpy as np
from .experiment import cable, after_experience


def eigs(model):
    invsqrt=1/np.sqrt(model.C)
    S=(invsqrt[:,None]*model.G)*invsqrt[None,:]
    lam, W=np.linalg.eigh(S)
    return lam, invsqrt[:,None]*W


def main():
    model=cable(42)
    lam, phi=eigs(model)
    rows=[]
    for b in range(4):
        # Budget 0.065 is chosen for perturbative validity, not the registered
        # 0.65 write. This is conceptual analysis rather than a benchmark gate.
        changed, d=after_experience(model,b,budget=.065)
        post,_=eigs(changed)
        first_order=(phi*phi).T@d
        actual=post-lam
        rows.append({'experience_branch':b,'mode_indices':list(range(12)),
                     'first_order':first_order[:12].tolist(),
                     'exact':actual[:12].tolist(),
                     'max_abs_error_first_12':float(np.max(np.abs(actual[:12]-first_order[:12])))})
    out={'interpretation':'First-order sensitivity of eigenvalues to local membrane shunt, 10% preregistered write size; exploratory.',
         'rows':rows}
    Path('results/mode_shifts.json').write_text(json.dumps(out,indent=2)+'\n')
    print('Wrote results/mode_shifts.json')
    for row in rows:
        print('branch',row['experience_branch'], 'first-order max abs error',round(row['max_abs_error_first_12'],7))

if __name__=='__main__':main()
