"""P3 - Net ultimate and net safe bearing capacity to IS 6403:1981.

IS 6403:1981 (Code of practice for determination of bearing capacity of shallow
foundations, first revision), clause 5.1.2:
  General shear:  q_nu = c Nc sc dc ic + q (Nq - 1) sq dq iq + 0.5 B gamma Ngamma sgamma dgamma igamma W'
  Local shear:    q'_nu = (2/3) c N'c sc dc ic + q (N'q - 1) sq dq iq + 0.5 B gamma N'gamma ... W'
                  with N' factors evaluated at phi' = atan(0.67 tan phi)
  Cohesive soil (phi = 0, undrained): q_nu = cu Nc sc dc ic, Nc = 5.14 (clause 5.1.2 / 5.2)
  q = effective overburden pressure at foundation level; gamma = bulk unit weight
  of the soil below the base; W' = water-table correction (clause 5.1.2.4).
Bearing capacity factors (Table 1 of IS 6403:1981):
  Nq = e^(pi tan phi) tan^2(45 + phi/2), Nc = (Nq - 1) cot phi, Ngamma = 2 (Nq + 1) tan phi (Vesic 1973)
Shape factors (Table 2), depth factors (5.1.2.2), inclination factors (5.1.2.3).
Effective area for eccentric loads: B' = B - 2 eB, L' = L - 2 eL (IS 6403:1981,
eccentrically loaded footings; Meyerhof 1953 effective-area method).
Net safe bearing capacity q_ns = q_nu / FS (IS 6403:1981 definitions; FS = 3 per the brief).
Clause numbers cited here should be checked against the group's copy of the code.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .profile import COHESIVE, Layer, SoilProfile

SHAPES = ("Strip", "Square", "Rectangle", "Circle")


# ------------------------------------------------------------------ factors
def bc_factors(phi_deg: float) -> tuple[float, float, float]:
    """IS 6403:1981 Table 1 bearing capacity factors (Nc, Nq, Ngamma)."""
    if phi_deg <= 1e-9:
        return 5.14, 1.0, 0.0  # phi = 0: Prandtl Nc = pi + 2
    p = math.radians(phi_deg)
    Nq = math.exp(math.pi * math.tan(p)) * math.tan(math.pi / 4 + p / 2) ** 2  # Reissner
    Nc = (Nq - 1.0) / math.tan(p)  # Prandtl
    Ng = 2.0 * (Nq + 1.0) * math.tan(p)  # Vesic (1973), as tabulated in IS 6403 Table 1
    return Nc, Nq, Ng


def shape_factors(shape: str, B: float, L: float) -> tuple[float, float, float]:
    """IS 6403:1981 Table 2 shape factors (sc, sq, sgamma)."""
    if shape == "Strip":
        return 1.0, 1.0, 1.0
    if shape == "Square":
        return 1.3, 1.2, 0.8
    if shape == "Circle":
        return 1.3, 1.2, 0.6
    r = B / L  # rectangle, B <= L
    return 1.0 + 0.2 * r, 1.0 + 0.2 * r, 1.0 - 0.4 * r


def depth_factors(phi_deg: float, Df: float, B: float) -> tuple[float, float, float]:
    """IS 6403:1981 clause 5.1.2.2 depth factors (dc, dq, dgamma).
    dc = 1 + 0.2 (Df/B) sqrt(N_phi); dq = dgamma = 1 for phi < 10 deg,
    dq = dgamma = 1 + 0.1 (Df/B) sqrt(N_phi) for phi > 10 deg; N_phi = tan^2(45 + phi/2).
    (Valid only where the backfill is properly compacted - code note.)"""
    nphi = math.tan(math.radians(45 + phi_deg / 2)) ** 2
    dc = 1.0 + 0.2 * (Df / B) * math.sqrt(nphi)
    dq = 1.0 if phi_deg < 10 else 1.0 + 0.1 * (Df / B) * math.sqrt(nphi)
    return dc, dq, dq


def inclination_factors(alpha_deg: float, phi_deg: float) -> tuple[float, float, float]:
    """IS 6403:1981 clause 5.1.2.3: ic = iq = (1 - alpha/90)^2, igamma = (1 - alpha/phi)^2
    (alpha = inclination of the load to the vertical, deg; igamma = 0 if alpha >= phi)."""
    ic = (1.0 - alpha_deg / 90.0) ** 2
    if phi_deg <= 1e-9:
        ig = 0.0 if alpha_deg > 0 else 1.0
    else:
        ig = max(0.0, 1.0 - alpha_deg / phi_deg) ** 2
    return ic, ic, ig


def water_table_factor(Dw: float, Df: float, B: float) -> float:
    """IS 6403:1981 clause 5.1.2.4: W' = 1 if water table at/below Df + B,
    0.5 if at/above the foundation base, linear interpolation in between."""
    if Dw >= Df + B:
        return 1.0
    if Dw <= Df:
        return 0.5
    return 0.5 + 0.5 * (Dw - Df) / B


# ----------------------------------------------------------------- analysis
@dataclass
class BCTerms:
    mode: str
    c: float
    phi: float
    Nc: float
    Nq: float
    Ng: float
    term_c: float
    term_q: float
    term_g: float
    q_nu: float


@dataclass
class BCResult:
    shape: str
    B: float
    L: float
    Df: float
    eB: float
    eL: float
    B_eff: float
    L_eff: float
    A_eff: float
    layer: str
    undrained: bool
    c: float
    phi: float
    gamma: float
    q: float  # effective overburden at Df, kPa
    sigma_tot_Df: float
    W: float
    sc: float
    sq: float
    sg: float
    dc: float
    dq: float
    dg: float
    ic: float
    iq: float
    ig: float
    general: BCTerms
    local: BCTerms
    mode_used: str
    q_nu: float
    FS: float
    q_ns: float
    q_safe_gross: float
    P: Optional[float] = None
    q_gross_applied: Optional[float] = None
    q_net_applied: Optional[float] = None
    ok: Optional[bool] = None
    warnings: list = field(default_factory=list)


def _terms(mode, c, phi, q, gamma, Beff, s, d, i, W, undrained) -> BCTerms:
    sc, sq, sg = s
    dc, dq, dg = d
    ic, iq, ig = i
    if mode == "local" and not undrained:
        c_m = 2.0 / 3.0 * c  # IS 6403 5.1.2(b): c' = 2/3 c
        phi_m = math.degrees(math.atan(0.67 * math.tan(math.radians(phi))))  # tan phi' = 0.67 tan phi
    else:
        c_m, phi_m = c, phi
    Nc, Nq, Ng = bc_factors(phi_m)
    tc = c_m * Nc * sc * dc * ic
    tq = q * (Nq - 1.0) * sq * dq * iq  # net: (Nq - 1)
    tg = 0.5 * Beff * gamma * Ng * sg * dg * ig * W
    return BCTerms(mode, c_m, phi_m, Nc, Nq, Ng, tc, tq, tg, tc + tq + tg)


def bearing_capacity(profile: SoilProfile, shape: str, B: float, L: Optional[float], Df: float,
                     P: Optional[float] = None, MB: float = 0.0, ML: float = 0.0,
                     alpha_deg: float = 0.0, FS: float = 3.0, mode: str = "auto",
                     use_depth_factors: bool = True, gamma_fill: float = 20.0,
                     gwt: Optional[float] = None, layer_override: Optional[Layer] = None) -> BCResult:
    """Full IS 6403:1981 calculation.

    shape: Strip | Square | Rectangle | Circle (B = diameter for a circle).
    P: vertical column load at founding level (kN; kN/m for strip).  MB, ML: moments
    causing eccentricity along B and along L (kN*m).  mode: 'general', 'local',
    'interpolated' or 'auto'.  gamma_fill: average unit weight of footing + backfill
    above the base (kN/m3) used for the applied pressure.
    """
    warnings = []
    gwt = profile.gwt_design if gwt is None else gwt
    if shape in ("Square", "Circle", "Strip") or L is None:
        L = B if shape != "Strip" else 1.0
    if shape == "Rectangle" and L < B:
        B, L = L, B
        warnings.append("B and L swapped so that B <= L.")
    lay = layer_override or profile.layer_at(Df + 1e-6)
    # warn if another layer starts within B below the base
    for l in profile.sorted_layers():
        if Df + 1e-6 < l.top < Df + B:
            warnings.append(f"Layer '{l.description}' starts {l.top - Df:.2f} m below the base "
                            f"(within B): check it separately (weak-layer check).")
            break

    undrained = bool(lay.undrained)  # user flag: short-term phi = 0 analysis with cu
    if undrained:
        c, phi = lay.cu, 0.0
    else:
        c, phi = lay.c_eff, lay.phi_eff

    # ---- eccentricity -> effective dimensions (IS 6403 effective area method)
    eB = eL = 0.0
    if P and P > 0:
        eB, eL = abs(MB) / P, abs(ML) / P
    if shape == "Circle" and (eB > 0 or eL > 0):
        warnings.append("Eccentric circular footing: analysed as equivalent square of equal area.")
        shape_used = "Square"
        Bsq = math.sqrt(math.pi) / 2 * B
        B_eff, L_eff = Bsq - 2 * eB, Bsq - 2 * eL
    elif shape == "Strip":
        shape_used = shape
        B_eff, L_eff = B - 2 * eB, 1.0
    else:
        shape_used = shape
        B_eff, L_eff = B - 2 * eB, L - 2 * eL
    if B_eff <= 0 or L_eff <= 0:
        raise ValueError("Eccentricity too large: effective width <= 0.")
    if L_eff < B_eff and shape != "Strip":
        B_eff, L_eff = L_eff, B_eff
    if (eB > B / 6 + 1e-9 or eL > L / 6 + 1e-9) and shape != "Circle":  # tolerance: e = B/6 is still in the kern
        warnings.append("Eccentricity exceeds the kern (e > B/6): part of the base is in tension.")
    if shape == "Square" and (eB > 0 or eL > 0):
        shape_used = "Rectangle"  # effective area is rectangular
    A_eff = B_eff * (L_eff if shape != "Strip" else 1.0)
    if shape == "Circle" and eB == 0 and eL == 0:
        A_eff = math.pi * B ** 2 / 4

    # ---- overburden and unit weight
    sig_tot, u, q = profile.stresses(Df, gwt)  # q = effective overburden at founding level
    gamma = lay.gamma_sat if gwt < Df + B_eff else lay.gamma_moist  # bulk unit weight below base
    W = water_table_factor(gwt, Df, B_eff)

    # ---- factors
    s = shape_factors(shape_used, B_eff, L_eff)
    phi_for_d = 0.0 if undrained else phi
    # depth factors use the actual width B (Df/B), not B' - effective dimensions enter only the shape
    # factors and the gamma term (Meyerhof effective-area method; Das, Principles of Foundation Engineering)
    d = depth_factors(phi_for_d, Df, B) if use_depth_factors else (1.0, 1.0, 1.0)
    i = inclination_factors(alpha_deg, phi_for_d)

    gen = _terms("general", c, phi, q, gamma, B_eff, s, d, i, W, undrained)
    loc = _terms("local", c, phi, q, gamma, B_eff, s, d, i, W, undrained)

    if undrained:
        # IS 6403: q_nu = cu Nc sc dc ic with Nc = 5.14; local shear uses (2/3) cu
        if mode == "local":
            mode_used, q_nu = "undrained, local shear (2/3 cu)", (2.0 / 3.0) * c * 5.14 * s[0] * d[0] * i[0]
        else:
            mode_used, q_nu = "undrained, general shear (phi = 0)", c * 5.14 * s[0] * d[0] * i[0]
        loc = _terms("general", 2.0 / 3.0 * c, 0.0, q, gamma, B_eff, s, d, i, W, True)
        loc.mode = "local"
    else:
        if mode == "auto":
            # Textbook rule used with IS 6403 (e.g. Murthy; Punmia): phi <= 28 local,
            # phi >= 36 general, linear interpolation between.
            mode = "interpolated"
        if mode == "general":
            mode_used, q_nu = "general shear", gen.q_nu
        elif mode == "local":
            mode_used, q_nu = "local shear", loc.q_nu
        else:
            t = min(max((phi - 28.0) / 8.0, 0.0), 1.0)
            q_nu = loc.q_nu + t * (gen.q_nu - loc.q_nu)
            mode_used = f"interpolated ({t:.2f} general + {1 - t:.2f} local)"

    q_ns = q_nu / FS  # net safe bearing capacity
    res = BCResult(shape, B, L, Df, eB, eL, B_eff, L_eff, A_eff, lay.description, undrained,
                   c, phi, gamma, q, sig_tot, W, *s, *d, *i, gen, loc, mode_used, q_nu, FS, q_ns,
                   q_ns + q, warnings=warnings)

    if P is not None and P > 0:
        A_full = (math.pi * B ** 2 / 4 if shape == "Circle" else B * (L if shape != "Strip" else 1.0))
        Wf = gamma_fill * A_full * Df  # weight of footing + backfill above the base
        q_gross = (P + Wf) / A_eff
        q_net = (P + Wf - sig_tot * A_full) / A_eff  # net = gross - total overburden removed
        res.P = P
        res.q_gross_applied = q_gross
        res.q_net_applied = q_net
        res.ok = q_net <= q_ns + 1e-9
    return res


def size_footing(profile: SoilProfile, shape: str, P: float, Df: float, L_over_B: float = 1.0,
                 MB: float = 0.0, ML: float = 0.0, FS: float = 3.0, mode: str = "auto",
                 step: float = 0.05, B_min: float = 0.6, B_max: float = 10.0, **kw) -> BCResult:
    """Smallest B (multiple of `step`) for which q_net,applied <= q_ns."""
    B = B_min
    last = None
    while B <= B_max + 1e-9:
        L = B * L_over_B if shape == "Rectangle" else None
        try:
            r = bearing_capacity(profile, shape, B, L, Df, P=P, MB=MB, ML=ML, FS=FS, mode=mode, **kw)
            last = r
            if r.ok:
                return r
        except ValueError:
            pass
        B = round(B + step, 6)
    if last is None:
        raise ValueError("No footing size found.")
    last.warnings.append(f"No size up to B = {B_max} m satisfies bearing capacity.")
    return last


# ------------------------------------------------------- weak underlying layer
@dataclass
class WeakLayerCheck:
    layer: str
    z_top: float  # depth of weak layer top below the base, m
    delta_sigma: float  # 2:1 stress at weak-layer top, kPa
    q_nu_weak: float
    FS: float
    ok: bool


def weak_layer_check(profile: SoilProfile, B: float, L: float, Df: float, q_net: float,
                     FS_req: float = 3.0, max_depth_factor: float = 2.0) -> Optional[WeakLayerCheck]:
    """Projected-area check of a soft cohesive layer below the footing.

    The net pressure is spread at 2V:1H to the top of the layer (2:1 method, Boston
    code; Bowles, Foundation Analysis and Design, two-layer bearing) and compared with
    the net ultimate capacity of a fictitious footing (B+z)(L+z) on that layer,
    q_nu = cu Nc sc (IS 6403, phi = 0, Nc = 5.14, sc = 1 + 0.2 B/L), no depth factor.
    """
    for l in profile.sorted_layers():
        if l.top >= Df and l.top < Df + max_depth_factor * B and l.soil_type == COHESIVE and l.cu > 0:
            z = l.top - Df
            Bz, Lz = B + z, L + z
            ds = q_net * B * L / (Bz * Lz)  # 2:1 dispersion
            q_nu = l.cu * 5.14 * (1 + 0.2 * Bz / Lz)
            fs = q_nu / ds if ds > 0 else float("inf")
            return WeakLayerCheck(l.description, z, ds, q_nu, fs, fs >= FS_req)
    return None
