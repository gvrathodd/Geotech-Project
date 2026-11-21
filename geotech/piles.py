"""Alternative foundation - bored cast-in-situ piles and the piled-raft (CPRF) check.

* Reese & O'Neill (1989) drilled shafts in granular soil (Das, Principles of
  Foundation Engineering, drilled-shaft chapter):
    shaft  f_s = beta * sigma'_v,  beta = 1.5 - 0.244 z^0.5 (0.25 <= beta <= 1.2) for N60 >= 15,
           beta x N60/15 for N60 < 15
    tip    q_p = 57.5 N60 kPa (N60 <= 75); q_p = 4310 kPa for N60 > 75 (D_b < 1.27 m)
* Cohesive layers (alpha method, Reese & O'Neill): f_s = 0.55 cu.
* IS 2911 (Part 1/Sec 2):2010 Annex B static formula, cohesionless soil:
    Q_u = A_p (0.5 D gamma' N_gamma + P_D N_q) + sum K P_Di tan(delta) A_si
  N_q from IS 2911 Fig. 1 (user-read value), N_gamma from IS 6403 Table 1, P_D limited to the
  effective overburden at the critical depth (15-20 D).
* Single-pile settlement: Vesic (1977) three-part method (Das, Principles of Foundation
  Engineering, "settlement of piles"): s = s_e1 + s_e2 + s_e3.
* Piled raft: Poulos-Davis-Randolph (PDR) method (Randolph 1983; Poulos 2001,
  Geotechnique 51(2)):  K_pr = (K_p + K_r (1 - 2 a_rp)) / (1 - a_rp^2 K_r / K_p),
  raft share X = P_r / P_t = K_r (1 - a_rp) / (K_p + K_r (1 - 2 a_rp)).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from .bearing import bc_factors
from .profile import COHESIVE, SoilProfile


@dataclass
class PileResult:
    method: str
    D: float
    L: float  # pile tip depth below ground, m
    Qp: float
    Qs: float
    Qu: float
    FS: float
    Qa: float
    rows: list = field(default_factory=list)  # shaft contributions per segment


def reese_oneill(profile: SoilProfile, D: float, tip: float, cutoff: float, n60_tip: float,
                 n60_of, ignore_shaft: Optional[List[tuple]] = None, FS: float = 2.5,
                 dz: float = 0.1, gwt: Optional[float] = None) -> PileResult:
    """n60_of(z) -> N60 at depth z (for beta reduction).  ignore_shaft: list of (top, bottom) ranges
    where shaft friction is neglected (liquefiable sands, soft clay)."""
    gwt = profile.gwt_design if gwt is None else gwt
    ignore_shaft = ignore_shaft or []
    Ap = math.pi * D ** 2 / 4
    per = math.pi * D
    qp = 4310.0 if n60_tip > 75 else 57.5 * n60_tip  # Reese & O'Neill tip resistance
    Qp = qp * Ap
    Qs, rows = 0.0, []
    n = max(1, int(round((tip - cutoff) / dz)))
    h = (tip - cutoff) / n
    for k in range(n):
        z = cutoff + (k + 0.5) * h
        lay = profile.layer_at(z)
        if any(a <= z < b for a, b in ignore_shaft):
            rows.append(dict(z=z, layer=lay.description, fs=0.0, dQ=0.0, note="neglected"))
            continue
        sv = profile.sigma_eff(z, gwt)
        if lay.soil_type == COHESIVE:
            fs = 0.55 * lay.cu  # alpha method, alpha = 0.55
        else:
            beta = min(max(1.5 - 0.244 * math.sqrt(z), 0.25), 1.2)
            N = n60_of(z)
            if N < 15:
                beta *= N / 15.0
            fs = beta * sv
        dQ = fs * per * h
        Qs += dQ
        rows.append(dict(z=z, layer=lay.description, fs=fs, dQ=dQ, note=""))
    Qu = Qp + Qs
    return PileResult("Reese & O'Neill (1989)", D, tip, Qp, Qs, Qu, FS, Qu / FS, rows)


def is2911_static(profile: SoilProfile, D: float, tip: float, cutoff: float, phi_tip: float, Nq: float,
                  K: float = 1.5, delta_ratio: float = 1.0, crit_depth_D: float = 20.0,
                  ignore_shaft: Optional[List[tuple]] = None, FS: float = 2.5,
                  dz: float = 0.1, gwt: Optional[float] = None) -> PileResult:
    """IS 2911 (Part 1/Sec 2):2010 Annex B static formula (cohesionless soils; cohesive layers by
    alpha*cu with alpha = 0.5 as a simplification)."""
    gwt = profile.gwt_design if gwt is None else gwt
    ignore_shaft = ignore_shaft or []
    Ap = math.pi * D ** 2 / 4
    per = math.pi * D
    zc = crit_depth_D * D
    PD = profile.sigma_eff(min(tip, zc), gwt)  # effective overburden at toe, limited to critical depth
    lay_t = profile.layer_at(tip)
    g_eff = (lay_t.gamma_sat - 9.81) if tip > gwt else lay_t.gamma_moist
    Ng = bc_factors(phi_tip)[2]  # IS 6403 Table 1
    Qp = Ap * (0.5 * D * g_eff * Ng + PD * Nq)
    Qs, rows = 0.0, []
    n = max(1, int(round((tip - cutoff) / dz)))
    h = (tip - cutoff) / n
    for k in range(n):
        z = cutoff + (k + 0.5) * h
        lay = profile.layer_at(z)
        if any(a <= z < b for a, b in ignore_shaft):
            rows.append(dict(z=z, layer=lay.description, fs=0.0, dQ=0.0, note="neglected"))
            continue
        PDi = profile.sigma_eff(min(z, zc), gwt)
        if lay.soil_type == COHESIVE:
            fs = 0.5 * lay.cu
        else:
            fs = K * PDi * math.tan(math.radians(delta_ratio * lay.phi_eff))
        dQ = fs * per * h
        Qs += dQ
        rows.append(dict(z=z, layer=lay.description, fs=fs, dQ=dQ, note=""))
    Qu = Qp + Qs
    return PileResult(f"IS 2911 Annex B (Nq = {Nq:g})", D, tip, Qp, Qs, Qu, FS, Qu / FS, rows)


def vesic_settlement(Qwp: float, Qws: float, D: float, L: float, Ep: float, Es_tip: float,
                     Es_shaft: float, nu: float = 0.3, xi: float = 0.5, L_shaft: Optional[float] = None) -> dict:
    """Vesic (1977): s_e1 = (Qwp + xi Qws) L / (Ap Ep)  (elastic shortening)
                    s_e2 = (qwp D / Es)(1 - nu^2) Iwp, Iwp = 0.85  (tip load)
                    s_e3 = (Qws / (p L)) (D / Es)(1 - nu^2) Iws, Iws = 2 + 0.35 sqrt(L/D)  (shaft load)"""
    Ap = math.pi * D ** 2 / 4
    p = math.pi * D
    Ls = L_shaft or L
    s1 = (Qwp + xi * Qws) * L / (Ap * Ep)
    s2 = (Qwp / Ap) * D / Es_tip * (1 - nu ** 2) * 0.85
    s3 = (Qws / (p * Ls)) * D / Es_shaft * (1 - nu ** 2) * (2 + 0.35 * math.sqrt(L / D))
    return dict(s1=s1, s2=s2, s3=s3, s=s1 + s2 + s3)


def pdr(Kp: float, Kr: float, alpha_rp: float = 0.8) -> dict:
    """Poulos-Davis-Randolph piled-raft stiffness and raft load share (Randolph 1983)."""
    Kpr = (Kp + Kr * (1 - 2 * alpha_rp)) / (1 - alpha_rp ** 2 * Kr / Kp)
    X = Kr * (1 - alpha_rp) / (Kp + Kr * (1 - 2 * alpha_rp))
    return dict(Kpr=Kpr, raft_share=X, pile_share=1 - X)
