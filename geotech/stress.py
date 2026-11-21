"""P4 - Vertical stress increase below loaded areas.

* Boussinesq (1885) solution integrated over a uniformly loaded rectangle gives the
  stress under a CORNER (Newmark 1935):
     I = 1/(4 pi) [ 2 m n sqrt(V) / (V + m^2 n^2) * (V + 1) / V
                    + atan( 2 m n sqrt(V) / (V - m^2 n^2) ) ],  V = m^2 + n^2 + 1,
     m = B/z, n = L/z; when V < m^2 n^2 the arctangent is taken in (pi/2, pi).
  (Das, Principles of Geotechnical Engineering, "stress below a rectangular area";
   IS 8009 (Part 1):1976 uses the same influence factors.)
  Any other point (centre, edge, outside) by superposition of corner rectangles.
* Uniformly loaded circle, below the centre:
     d_sigma = q [1 - 1 / (1 + (R/z)^2)^1.5]   (Boussinesq integration; Das, ibid.)
* 2:1 (2V:1H) approximate method:
     rectangle d_sigma = q B L / ((B + z)(L + z)); strip q B / (B + z);
     circle q D^2 / (D + z)^2   (Das, Principles of Foundation Engineering, 2:1 method)
z is measured from the base of the footing.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def corner_factor(B: float, L: float, z: float) -> float:
    """Newmark influence factor I for a point below the corner of a B x L rectangle at depth z."""
    if B <= 0 or L <= 0:
        return 0.0
    if z <= 1e-9:
        return 0.25  # directly under the corner at the surface: q/4
    m, n = B / z, L / z
    V = m * m + n * n + 1.0
    mn2 = (m * n) ** 2
    a = 2 * m * n * math.sqrt(V) / (V + mn2) * (V + 1.0) / V
    b = math.atan2(2 * m * n * math.sqrt(V), V - mn2)  # atan2 keeps the (pi/2, pi) branch when V < m^2 n^2
    return (a + b) / (4 * math.pi)


def _signed(a: float, b: float, z: float) -> float:
    s = math.copysign(1.0, a) * math.copysign(1.0, b)
    if a == 0 or b == 0:
        return 0.0
    return s * corner_factor(abs(a), abs(b), z)


def rect_point(q: float, B: float, L: float, x: float, y: float, z: float) -> float:
    """Boussinesq stress at (x, y, z) below a B x L rectangle centred at the origin
    (B along x, L along y), by superposition of four corner rectangles."""
    x1, x2 = -B / 2 - x, B / 2 - x
    y1, y2 = -L / 2 - y, L / 2 - y
    I = _signed(x2, y2, z) - _signed(x1, y2, z) - _signed(x2, y1, z) + _signed(x1, y1, z)
    return q * I


def rect_centre(q: float, B: float, L: float, z: float) -> float:
    """Below the centre = 4 x corner of (B/2 x L/2) (superposition)."""
    return 4.0 * q * corner_factor(B / 2, L / 2, z)


def rect_corner(q: float, B: float, L: float, z: float) -> float:
    return q * corner_factor(B, L, z)


def strip_centre(q: float, B: float, z: float) -> float:
    """Boussinesq strip (approximated by L = 1000 B rectangle)."""
    return rect_centre(q, B, 1000.0 * B, z)


def circle_centre(q: float, D: float, z: float) -> float:
    if z <= 1e-9:
        return q
    R = D / 2
    return q * (1.0 - 1.0 / (1.0 + (R / z) ** 2) ** 1.5)


def two_to_one(q: float, shape: str, B: float, L: float, z: float) -> float:
    """2V:1H dispersion."""
    if shape == "Strip":
        return q * B / (B + z)
    if shape == "Circle":
        return q * B ** 2 / (B + z) ** 2
    return q * B * L / ((B + z) * (L + z))


def boussinesq_centre(q: float, shape: str, B: float, L: float, z: float) -> float:
    if shape == "Circle":
        return circle_centre(q, B, z)
    if shape == "Strip":
        return strip_centre(q, B, z)
    return rect_centre(q, B, L, z)


def boussinesq_corner(q: float, shape: str, B: float, L: float, z: float) -> float:
    if shape == "Circle":
        return float("nan")  # no corner
    if shape == "Strip":
        return rect_corner(q, B, 1000.0 * B, z)  # edge of a strip
    return rect_corner(q, B, L, z)


def profile_table(q: float, shape: str, B: float, L: float, depths: Iterable[float]):
    """Delta sigma_z (kPa) vs depth below base for centre, corner and 2:1."""
    rows = []
    for z in depths:
        rows.append(dict(z=z,
                         centre=boussinesq_centre(q, shape, B, L, z),
                         corner=boussinesq_corner(q, shape, B, L, z),
                         two_one=two_to_one(q, shape, B, L, z)))
    return rows


def group_stress(footings, x: float, y: float, z_abs: float) -> float:
    """Superposed Boussinesq stress at plan point (x, y) and absolute depth z_abs (m bgl)
    from several rectangular footings.  footings: iterable of dicts with keys
    x, y (centre), B (along x), L (along y), Df (m bgl), q (net pressure, kPa)."""
    s = 0.0
    for f in footings:
        z = z_abs - f["Df"]
        if z <= 0:
            continue
        s += rect_point(f["q"], f["B"], f["L"], x - f["x"], y - f["y"], z)
    return s
