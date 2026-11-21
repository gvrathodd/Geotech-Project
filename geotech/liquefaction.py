"""Extra - Liquefaction triggering by the simplified procedure of IS 1893 (Part 1):2016
Annex F (Seed & Idriss 1971 as updated by Youd et al. 2001, NCEER).

  CSR = 0.65 (a_max/g) (sigma_v0 / sigma'_v0) r_d
  r_d = 1 - 0.00765 z (z <= 9.15 m);  1.174 - 0.0267 z (9.15 < z <= 23 m)
  (N1)60 = N C_N C_E C_B C_R C_S,  C_N = (Pa / sigma'_v0)^0.5 <= 1.7
  C_R (rod length) 0.75 (<3 m), 0.80 (3-4), 0.85 (4-6), 0.95 (6-10), 1.0 (>10)
  C_B (borehole) 1.0 (65-115 mm), 1.05 (150 mm), 1.15 (200 mm)
  Fines: alpha = 0 (FC<=5), exp(1.76 - 190/FC^2) (5<FC<35), 5 (FC>=35)
         beta  = 1 (FC<=5), 0.99 + FC^1.5/1000 (5<FC<35), 1.2 (FC>=35)
  (N1)60cs = alpha + beta (N1)60
  CRR7.5 = 1/(34 - N) + N/135 + 50/(10N + 45)^2 - 1/200   for (N1)60cs < 30
  MSF = 10^2.24 / Mw^2.56 ;  FS_L = CRR7.5 * MSF / CSR
Plastic/clayey soils (cohesive layers) are screened out as non-liquefiable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from .profile import COHESIVE, SoilProfile

PA = 101.325  # atmospheric pressure, kPa


def rd(z: float) -> float:
    if z <= 9.15:
        return 1.0 - 0.00765 * z
    return 1.174 - 0.0267 * z


def c_rod(rod_length: float) -> float:
    if rod_length < 3:
        return 0.75
    if rod_length < 4:
        return 0.80
    if rod_length < 6:
        return 0.85
    if rod_length < 10:
        return 0.95
    return 1.0


def c_borehole(d_mm: float) -> float:
    if d_mm <= 115:
        return 1.0
    if d_mm <= 150:
        return 1.05
    return 1.15


def fines_correction(fc: float):
    if fc <= 5:
        return 0.0, 1.0
    if fc >= 35:
        return 5.0, 1.2
    return math.exp(1.76 - 190.0 / fc ** 2), 0.99 + fc ** 1.5 / 1000.0


def crr75(n1_60cs: float) -> float:
    if n1_60cs >= 30:
        return float("inf")  # too dense to liquefy
    return 1.0 / (34 - n1_60cs) + n1_60cs / 135.0 + 50.0 / (10 * n1_60cs + 45) ** 2 - 1.0 / 200.0


@dataclass
class LiqRow:
    depth: float
    N: float
    layer: str
    fines: float
    sigma_v: float
    sigma_eff: float
    rd: float
    CSR: float
    CN: float
    CR: float
    N1_60: float
    alpha: float
    beta: float
    N1_60cs: float
    CRR75: float
    MSF: float
    FS: float
    status: str


def liquefaction(profile: SoilProfile, amax_g: float, Mw: float = 7.5, gwt: Optional[float] = None,
                 energy_ratio: float = 60.0, borehole_mm: float = 150.0,
                 fines: Optional[dict] = None, max_depth: float = 20.0) -> List[LiqRow]:
    """Evaluate every SPT record of the profile.  fines: {layer description: FC %}."""
    gwt = profile.gwt_design if gwt is None else gwt
    fines = fines or {}
    MSF = 10 ** 2.24 / Mw ** 2.56  # Idriss magnitude scaling factor
    out = []
    for rec in sorted(profile.spt, key=lambda r: r.depth):
        z = rec.depth
        lay = profile.layer_at(z)
        sv, u, se = profile.stresses(z, gwt)
        r = rd(z)
        csr = 0.65 * amax_g * sv / se * r if se > 0 else float("nan")
        fc = float(fines.get(lay.description, 0.0))
        base = dict(depth=z, N=rec.N, layer=lay.description, fines=fc, sigma_v=sv, sigma_eff=se,
                    rd=r, CSR=csr, MSF=MSF)
        if z <= gwt:
            out.append(LiqRow(**base, CN=float("nan"), CR=float("nan"), N1_60=float("nan"), alpha=0, beta=1,
                              N1_60cs=float("nan"), CRR75=float("nan"), FS=float("inf"),
                              status="Above water table – not liquefiable"))
            continue
        if lay.soil_type == COHESIVE:
            out.append(LiqRow(**base, CN=float("nan"), CR=float("nan"), N1_60=float("nan"), alpha=0, beta=1,
                              N1_60cs=float("nan"), CRR75=float("nan"), FS=float("inf"),
                              status="Cohesive/plastic – screened out"))
            continue
        if rec.refusal or z > max_depth:
            out.append(LiqRow(**base, CN=float("nan"), CR=float("nan"), N1_60=float("nan"), alpha=0, beta=1,
                              N1_60cs=float("nan"), CRR75=float("nan"), FS=float("inf"),
                              status="Refusal / very dense – not liquefiable"))
            continue
        CN = min((PA / se) ** 0.5, 1.7)
        CE = energy_ratio / 60.0
        CB = c_borehole(borehole_mm)
        CR = c_rod(z + 1.0)  # rod length ~ test depth + ~1 m stick-up
        n160 = rec.N * CN * CE * CB * CR
        a, b = fines_correction(fc)
        ncs = a + b * n160
        crr = crr75(ncs)
        fs = crr * MSF / csr if csr > 0 else float("inf")
        status = "Liquefiable (FS < 1)" if fs < 1.0 else ("Marginal (1 ≤ FS < 1.2)" if fs < 1.2 else "Safe")
        out.append(LiqRow(**base, CN=CN, CR=CR, N1_60=n160, alpha=a, beta=b, N1_60cs=ncs, CRR75=crr,
                          FS=fs, status=status))
    return out
