"""P2 - SPT N corrections to IS 2131:1981 and SPT-based parameter correlations.

IS 2131:1981 (Method for standard penetration test for soils), clause on
corrections, applies two corrections to the observed N in cohesionless soils, in
this order:
  (a) overburden pressure: N' = C_N * N, with C_N read from IS 2131 Fig. 1
      (correction factor vs effective overburden pressure in kg/cm2).  Fig. 1 is
      the Peck, Hanson & Thornburn (1974) curve, C_N = 0.77 log10(20 / p'),
      p' in kg/cm2 (Peck, Hanson & Thornburn, Foundation Engineering, 2nd ed.,
      1974; also Murthy, Geotechnical Engineering, SPT corrections).
  (b) dilatancy: for saturated very fine / silty sand with N' > 15,
      N'' = 15 + 0.5 (N' - 15)  (IS 2131:1981, after Terzaghi & Peck 1948).
Corrections use the water table at the time of the test (measured), not the
design water table.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from . import KGCM2_TO_KPA
from .profile import COHESIVE, SoilProfile


def cn_overburden(sigma_eff_kpa: float, cn_max: float = 2.0) -> tuple[float, bool]:
    """Overburden correction factor C_N (IS 2131:1981 Fig. 1 / PHT 1974).

    C_N = 0.77 log10(20 / p'), p' in kg/cm2.  The curve is defined for
    p' >= 0.25 kg/cm2 (24.5 kPa); below that C_N is capped at cn_max.
    Returns (C_N, capped_flag).
    """
    p = sigma_eff_kpa / KGCM2_TO_KPA  # kPa -> kg/cm2
    if p <= 0:
        return cn_max, True
    cn = 0.77 * math.log10(20.0 / p)  # IS 2131 Fig. 1, PHT (1974)
    if cn > cn_max:
        return cn_max, True
    return cn, False


def dilatancy(n_dash: float) -> float:
    """IS 2131:1981 dilatancy correction: N'' = 15 + 0.5 (N' - 15) when N' > 15."""
    return 15.0 + 0.5 * (n_dash - 15.0) if n_dash > 15.0 else n_dash


@dataclass
class SPTStep:
    depth: float
    N: float
    refusal: bool
    layer: str
    soil_type: str
    sigma_eff_kpa: float
    sigma_eff_kgcm2: float
    CN: float
    CN_capped: bool
    N1: float  # after overburden correction
    below_wt: bool
    dilatancy_applies: bool
    N2: float  # after dilatancy correction (final corrected N)
    note: str


def correct_profile_spt(profile: SoilProfile, cn_max: float = 2.0) -> List[SPTStep]:
    """Apply IS 2131 corrections to every SPT record of a profile, showing each step."""
    out = []
    if not profile.layers:
        return out
    gwt = profile.gwt_measured  # corrections use the water level at the time of testing
    for rec in sorted(profile.spt, key=lambda r: r.depth):
        lay = profile.layer_at(rec.depth)
        s_eff = profile.sigma_eff(rec.depth, gwt)
        if rec.refusal:
            out.append(SPTStep(rec.depth, rec.N, True, lay.description, lay.soil_type, s_eff,
                               s_eff / KGCM2_TO_KPA, float("nan"), False, rec.N, rec.depth > gwt,
                               False, rec.N, "Refusal: no correction applied, treated as very dense"))
            continue
        if lay.soil_type == COHESIVE:
            out.append(SPTStep(rec.depth, rec.N, False, lay.description, lay.soil_type, s_eff,
                               s_eff / KGCM2_TO_KPA, 1.0, False, rec.N, rec.depth > gwt, False,
                               rec.N, "Cohesive soil: IS 2131 corrections not applied"))
            continue
        cn, capped = cn_overburden(s_eff, cn_max)
        n1 = cn * rec.N  # N' = C_N * N  (IS 2131 overburden correction)
        below = rec.depth > gwt
        dil = bool(lay.dilatancy and below and n1 > 15.0)
        n2 = dilatancy(n1) if dil else n1  # N'' (IS 2131 dilatancy correction)
        note = []
        if capped:
            note.append(f"C_N capped at {cn_max} (p' < 0.25 kg/cm2 outside chart range)")
        if lay.dilatancy and not below:
            note.append("above water table: no dilatancy correction")
        if lay.dilatancy and below and n1 <= 15:
            note.append("N' <= 15: no dilatancy correction")
        out.append(SPTStep(rec.depth, rec.N, False, lay.description, lay.soil_type, s_eff,
                           s_eff / KGCM2_TO_KPA, cn, capped, n1, below, dil, n2, "; ".join(note)))
    return out


# ---------------------------------------------------------------- correlations
def phi_from_n(n: float) -> float:
    """phi' (deg) from corrected N: Peck, Hanson & Thornburn (1974) chart as fitted by
    Wolff (1989): phi = 27.1 + 0.3 N - 0.00054 N^2 (Das, Principles of Foundation
    Engineering, SPT correlations for granular soil)."""
    n = min(max(n, 0.0), 60.0)
    return 27.1 + 0.3 * n - 0.00054 * n ** 2


def cu_from_n(n: float, f1: float = 4.5) -> float:
    """Undrained strength from N: cu = f1 * N kPa, f1 ~ 4-6 for PI 15-40 (Stroud 1974)."""
    return f1 * n


def e_from_n(n: float, qc_over_n_mpa: float = 0.4, L_over_B: float = 1.0) -> tuple[float, float]:
    """Schmertmann modulus from N via qc.

    qc = (qc/N) * N  [MPa] (qc/N ~0.2 silt, 0.3-0.4 silty/fine sand, 0.5 medium-coarse
    sand, 0.6-0.8 sandy gravel: Robertson, Campanella & Wightman 1983).
    E = 2.5 qc (axisymmetric, L/B = 1) to 3.5 qc (plane strain, L/B >= 10),
    linear in between (Schmertmann, Hartman & Brown 1978).
    Returns (qc kPa, E kPa).
    """
    qc = qc_over_n_mpa * n * 1000.0
    f = (min(max(L_over_B, 1.0), 10.0) - 1.0) / 9.0
    return qc, (2.5 + 1.0 * f) * qc
