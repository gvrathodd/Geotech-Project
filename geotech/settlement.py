"""P5 - Settlement: granular layers (Schmertmann et al. 1978), 1-D consolidation of
NC / OC clay in sublayers <= 0.5 m, and the time-settlement curve (Terzaghi).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import numpy as np

from .profile import COHESIVE, GRANULAR, SoilProfile
from . import stress as st


# ------------------------------------------------------------ Schmertmann 1978
@dataclass
class SchmertmannResult:
    settlement: float  # m
    C1: float
    C2: float
    Izp: float
    zp: float  # depth of peak below base, m
    z_infl: float  # depth of influence below base, m
    Iz0: float
    sigma_vp: float  # sigma'_v at the depth of the peak, kPa
    q_net: float
    rows: list = field(default_factory=list)  # per sublayer
    skipped_cohesive: float = 0.0  # thickness of cohesive soil inside the influence zone, m


def schmertmann_iz(z: float, B: float, L: float, Izp: float):
    """Strain influence factor Iz (Schmertmann, Hartman & Brown 1978).
    Axisymmetric (L/B = 1): Iz = 0.1 at z = 0 -> Izp at z = B/2 -> 0 at z = 2B.
    Plane strain (L/B >= 10): Iz = 0.2 at z = 0 -> Izp at z = B -> 0 at z = 4B.
    Linear interpolation of Iz0, zp and z_max for 1 < L/B < 10."""
    f = (min(max(L / B, 1.0), 10.0) - 1.0) / 9.0
    Iz0 = 0.1 + 0.1 * f
    zp = (0.5 + 0.5 * f) * B
    zmax = (2.0 + 2.0 * f) * B
    if z < 0 or z > zmax:
        return 0.0, Iz0, zp, zmax
    if z <= zp:
        return Iz0 + (Izp - Iz0) * z / zp, Iz0, zp, zmax
    return Izp * (zmax - z) / (zmax - zp), Iz0, zp, zmax


def schmertmann(profile: SoilProfile, shape: str, B: float, L: Optional[float], Df: float,
                q_net: float, t_years: float = 0.1, dz: float = 0.05,
                gwt: Optional[float] = None, include_cohesive: bool = False) -> SchmertmannResult:
    """S = C1 C2 q_net sum(Iz / E dz)   (Schmertmann, Hartman & Brown 1978, JGED 104(GT8))
    C1 = 1 - 0.5 sigma'_0 / q_net >= 0.5 (embedment);  C2 = 1 + 0.2 log10(t / 0.1 yr) (creep)
    Izp = 0.5 + 0.1 sqrt(q_net / sigma'_vp), sigma'_vp at depth Df + zp.
    Cohesive layers in the influence zone are skipped (their settlement is computed by
    consolidation) unless include_cohesive=True.  E is taken from each layer (kPa).
    """
    gwt = profile.gwt_design if gwt is None else gwt
    if shape == "Strip":
        L = 1000.0 * B
    elif L is None or shape in ("Square", "Circle"):
        L = B
    sig0 = profile.sigma_eff(Df, gwt)
    _, Iz0, zp, zmax = schmertmann_iz(0.0, B, L, 0.5)
    sig_vp = profile.sigma_eff(Df + zp, gwt)
    if q_net <= 0:
        return SchmertmannResult(0.0, 1.0, 1.0, 0.5, zp, zmax, Iz0, sig_vp, q_net)
    Izp = 0.5 + 0.1 * math.sqrt(q_net / sig_vp)  # peak influence factor
    C1 = max(0.5, 1.0 - 0.5 * sig0 / q_net)  # depth/embedment correction
    C2 = 1.0 + 0.2 * math.log10(max(t_years, 0.1) / 0.1)  # creep correction
    rows, total, skipped = [], 0.0, 0.0
    n = max(1, int(math.ceil(zmax / dz)))
    h = zmax / n
    for k in range(n):
        zm = (k + 0.5) * h
        lay = profile.layer_at(Df + zm)
        Iz = schmertmann_iz(zm, B, L, Izp)[0]
        if lay.soil_type == COHESIVE and not include_cohesive:
            skipped += h
            rows.append(dict(z=zm, depth=Df + zm, layer=lay.description, Iz=Iz, E=lay.E, ds=0.0, note="cohesive: by consolidation"))
            continue
        ds = C1 * C2 * q_net * Iz / lay.E * h
        total += ds
        rows.append(dict(z=zm, depth=Df + zm, layer=lay.description, Iz=Iz, E=lay.E, ds=ds, note=""))
    return SchmertmannResult(total, C1, C2, Izp, zp, zmax, Iz0, sig_vp, q_net, rows, skipped)


# ----------------------------------------------------- 1-D consolidation (NC/OC)
@dataclass
class ConsolidationRow:
    layer: str
    top: float
    bottom: float
    H: float
    z_mid: float
    sigma0: float
    sigma_p: float
    d_sigma: float
    sigma_f: float
    case: str
    Cc: float
    Cs: float
    e0: float
    s: float  # m


@dataclass
class ConsolidationResult:
    total: float
    rows: List[ConsolidationRow]
    per_layer: dict  # description -> settlement m
    layers: list  # cohesive layers used (Layer objects)


def consolidation_sublayer(H, e0, Cc, Cs, s0, sp, ds):
    """One-dimensional consolidation settlement of a sublayer of thickness H
    (Terzaghi; Das, Principles of Geotechnical Engineering, consolidation settlement):
      NC (sigma'_p = sigma'_0):        s = Cc H/(1+e0) log10((s0+ds)/s0)
      OC, s0+ds <= sigma'_p:           s = Cs H/(1+e0) log10((s0+ds)/s0)
      OC, s0+ds  > sigma'_p:           s = Cs H/(1+e0) log10(sp/s0) + Cc H/(1+e0) log10((s0+ds)/sp)
    """
    sf = s0 + ds
    if ds <= 0:
        return 0.0, "no load"
    if sp <= s0 * (1 + 1e-9):
        return Cc * H / (1 + e0) * math.log10(sf / s0), "NC"
    if sf <= sp:
        return Cs * H / (1 + e0) * math.log10(sf / s0), "OC (sf <= sp)"
    return (Cs * H / (1 + e0) * math.log10(sp / s0)
            + Cc * H / (1 + e0) * math.log10(sf / sp)), "OC (sf > sp)"


def consolidation(profile: SoilProfile, d_sigma: Callable[[float], float], Df: float,
                  max_sub: float = 0.5, gwt: Optional[float] = None,
                  max_depth: Optional[float] = None) -> ConsolidationResult:
    """Consolidation settlement of every cohesive layer below the base.

    d_sigma(z_abs): stress increase (kPa) at absolute depth z_abs (m bgl).
    Each cohesive layer is split into equal sublayers no thicker than max_sub (<= 0.5 m).
    """
    max_sub = min(max_sub, 0.5)
    gwt = profile.gwt_design if gwt is None else gwt
    rows, per, used = [], {}, []
    for lay in profile.sorted_layers():
        if lay.soil_type != COHESIVE or lay.Cc <= 0:
            continue
        top, bot = max(lay.top, Df), lay.bottom
        if max_depth is not None:
            bot = min(bot, max_depth)
        if bot <= top:
            continue
        used.append(lay)
        n = int(math.ceil((bot - top) / max_sub - 1e-9))
        H = (bot - top) / n
        sum_l = 0.0
        for k in range(n):
            a = top + k * H
            zm = a + H / 2
            s0 = profile.sigma_eff(zm, gwt)
            sp = lay.sigma_p(s0)
            ds = d_sigma(zm)
            s, case = consolidation_sublayer(H, lay.e0, lay.Cc, lay.Cs, s0, sp, ds)
            sum_l += s
            rows.append(ConsolidationRow(lay.description, a, a + H, H, zm, s0, sp, ds, s0 + ds, case,
                                         lay.Cc, lay.Cs, lay.e0, s))
        per[f"{lay.description} ({lay.top:g}-{lay.bottom:g} m)"] = sum_l
    return ConsolidationResult(sum(per.values()), rows, per, used)


def footing_stress_fn(method: str, q_net: float, shape: str, B: float, L: Optional[float], Df: float):
    """Return d_sigma(z_abs) for 'Boussinesq centre', 'Boussinesq corner' or '2:1'."""
    if shape in ("Square", "Circle") or L is None:
        L = B
    if shape == "Strip":
        L = 1000.0 * B

    def f(z_abs):
        z = z_abs - Df
        if z <= 0:
            return q_net
        if method == "Boussinesq centre":
            return st.boussinesq_centre(q_net, shape, B, L, z)
        if method == "Boussinesq corner":
            return st.boussinesq_corner(q_net, shape, B, L, z)
        return st.two_to_one(q_net, shape, B, L, z)

    return f


# --------------------------------------------------------- time - settlement
def degree_of_consolidation(Tv):
    """Average degree of consolidation U(Tv) - Terzaghi (1925) series solution:
    U = 1 - sum_{m=0}^{inf} (2/M^2) exp(-M^2 Tv),  M = pi (2m+1)/2."""
    Tv = np.atleast_1d(np.asarray(Tv, float))
    U = np.ones_like(Tv)
    for m in range(200):
        M = math.pi * (2 * m + 1) / 2
        U -= 2.0 / M ** 2 * np.exp(-M ** 2 * Tv)
    U[Tv <= 0] = 0.0
    return np.clip(U, 0.0, 1.0)


def drainage_path(H: float, drainage: str) -> float:
    """H_dr = H/2 for double drainage, H for single drainage."""
    return H / 2.0 if drainage == "Double" else H


def time_settlement(layers_sc: list, t_years: np.ndarray):
    """layers_sc: list of (Sc m, H m, cv m2/yr, drainage) per clay layer.
    Tv = cv t / Hdr^2 (Terzaghi).  Returns total settlement array (m) and per-layer arrays."""
    total = np.zeros_like(t_years, dtype=float)
    parts = []
    for Sc, H, cv, drainage in layers_sc:
        Hdr = drainage_path(H, drainage)
        Tv = cv * t_years / Hdr ** 2
        s = Sc * degree_of_consolidation(Tv)
        parts.append(s)
        total += s
    return total, parts


def time_for_U(U: float, H: float, cv: float, drainage: str) -> float:
    """Time (yr) to reach average degree of consolidation U.
    Tv = (pi/4) U^2 for U <= 0.6; Tv = 1.781 - 0.933 log10(100 (1 - U)) for U > 0.6
    (Das, Principles of Geotechnical Engineering, Tv-U approximations)."""
    if U <= 0.6:
        Tv = math.pi / 4 * U ** 2
    else:
        Tv = 1.781 - 0.933 * math.log10(100 * (1 - U))
    return Tv * drainage_path(H, drainage) ** 2 / cv
