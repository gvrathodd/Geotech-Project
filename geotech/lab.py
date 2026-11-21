"""P2 - Laboratory parameter tools: direct shear least-squares fit, UU triaxial,
one-dimensional consolidation (Cc, Cs, Casagrande sigma'_p, cv unit conversion).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np

from . import CM2S_TO_M2YR, KGCM2_TO_KPA


# ------------------------------------------------------------ direct shear fit
@dataclass
class ShearFit:
    c: float  # kPa
    phi: float  # deg
    tan_phi: float
    r2: float
    n: int


def fit_mohr_coulomb(sigma_n: Sequence[float], tau_f: Sequence[float],
                     force_c_zero: bool = False) -> ShearFit:
    """Least-squares fit of the Mohr-Coulomb envelope tau_f = c' + sigma_n tan(phi').

    Ordinary least squares (normal equations):
      tan(phi') = [n S(xy) - S(x)S(y)] / [n S(x^2) - (S(x))^2],  c' = y_bar - tan(phi') x_bar
    With c' forced to zero: tan(phi') = S(xy) / S(x^2).
    (Mohr-Coulomb criterion: Das, Principles of Geotechnical Engineering, shear strength.)
    """
    x = np.asarray(sigma_n, float)
    y = np.asarray(tau_f, float)
    n = len(x)
    if n < 2:
        raise ValueError("At least two (sigma_n, tau_f) points are needed.")
    if force_c_zero:
        t = float((x * y).sum() / (x * x).sum())
        c = 0.0
    else:
        t = float((n * (x * y).sum() - x.sum() * y.sum()) / (n * (x * x).sum() - x.sum() ** 2))
        c = float(y.mean() - t * x.mean())
    yhat = c + t * x
    ss_res = float(((y - yhat) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
    return ShearFit(c=c, phi=math.degrees(math.atan(t)), tan_phi=t, r2=r2, n=n)


# --------------------------------------------------------------- UU triaxial
def cu_from_uu(deviator_at_failure: Sequence[float]) -> tuple[float, List[float]]:
    """Undrained strength cu = (sigma1 - sigma3)_f / 2 for each specimen; returns mean and list.
    (phi_u = 0 concept for saturated clay; Das, Principles of Geotechnical Engineering, UU test.)"""
    vals = [d / 2.0 for d in deviator_at_failure]
    return float(np.mean(vals)), vals


# -------------------------------------------------------------- consolidation
@dataclass
class OedometerResult:
    p_kpa: np.ndarray
    e: np.ndarray
    stage: List[str]
    Cc: float
    Cs: float
    sigma_p: float  # kPa, Casagrande
    construction: dict  # geometry of the Casagrande construction for plotting
    cv_m2yr: List[Optional[float]]


def analyse_oedometer(p: Sequence[float], e: Sequence[float], stage: Sequence[str],
                      p_unit: str = "kg/cm2", cv: Optional[Sequence[Optional[float]]] = None,
                      cv_unit: str = "cm2/s", n_virgin: int = 2) -> OedometerResult:
    """Interpret an incremental-loading oedometer test.

    * Pressure converted to kPa (1 kg/cm2 = 98.0665 kPa).
    * Cc = -de / dlog10(p) of the last n_virgin loading points (virgin compression line).
    * Cs = slope of the unloading branch, least-squares over unloading points incl. max load.
    * sigma'_p by Casagrande (1936) construction: point of maximum curvature on the
      e-log p loading curve, horizontal line and tangent there, bisector of the angle,
      intersection of the bisector with the virgin line (IS 2720 Part 15:1986 /
      Das, Principles of Geotechnical Engineering, pre-consolidation pressure).
    * cv converted to m2/yr (1 cm2/s = 3155.76 m2/yr).
    """
    p = np.asarray(p, float) * (KGCM2_TO_KPA if p_unit == "kg/cm2" else 1.0)
    e = np.asarray(e, float)
    stage = [str(s).strip().lower() for s in stage]
    load = np.array([s.startswith("load") for s in stage])
    pl, el = p[load], e[load]
    order = np.argsort(pl)
    pl, el = pl[order], el[order]
    xl = np.log10(pl)

    # Virgin compression line through the last n_virgin loading points
    xv, ev = xl[-n_virgin:], el[-n_virgin:]
    sv, iv = np.polyfit(xv, ev, 1)  # e = iv + sv*x
    Cc = -sv

    # Unloading branch, start at the maximum load
    imax = int(np.argmax(p))
    unl = [i for i, s in enumerate(stage) if s.startswith("unload")]
    Cs = float("nan")
    if unl:
        idx = [imax] + unl
        su, _ = np.polyfit(np.log10(p[idx]), e[idx], 1)
        Cs = -su

    # Casagrande: curvature of a monotone cubic through the loading points
    from scipy.interpolate import PchipInterpolator

    f = PchipInterpolator(xl, el)
    xs = np.linspace(xl[0], xl[-1], 2001)
    d1 = f.derivative(1)(xs)
    d2 = f.derivative(2)(xs)
    kappa = np.abs(d2) / (1 + d1 ** 2) ** 1.5
    # restrict to the part of the curve before the virgin line
    mask = xs <= xv[0]
    k = np.where(mask, kappa, -1)
    im = int(np.argmax(k))
    xm, em, sm = xs[im], float(f(xs[im])), d1[im]
    ang = math.atan(sm)  # tangent angle (negative)
    sb = math.tan(ang / 2.0)  # bisector of horizontal (0) and tangent
    # intersection of e = em + sb (x - xm) with e = iv + sv x
    xp = (iv - em + sb * xm) / (sb - sv)
    sigma_p = 10 ** xp
    construction = dict(xm=xm, em=em, tangent_slope=sm, bisector_slope=sb,
                        virgin_slope=sv, virgin_intercept=iv, xp=xp, ep=iv + sv * xp)

    cvs: List[Optional[float]] = []
    if cv is not None:
        for v in cv:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                cvs.append(None)
            else:
                cvs.append(float(v) * (CM2S_TO_M2YR if cv_unit == "cm2/s" else 1.0))
    return OedometerResult(p, e, list(stage), float(Cc), float(Cs), float(sigma_p), construction, cvs)


def cc_skempton(LL: float) -> float:
    """Remoulded-clay correlation Cc = 0.007 (LL - 10)  (Skempton 1944)."""
    return 0.007 * (LL - 10.0)


def cc_terzaghi_peck(LL: float) -> float:
    """Undisturbed clay of low-medium sensitivity Cc = 0.009 (LL - 10) (Terzaghi & Peck 1967)."""
    return 0.009 * (LL - 10.0)


def e0_saturated(w: float, Gs: float) -> float:
    """e = w Gs / S with S = 1 (phase relationship)."""
    return w * Gs
