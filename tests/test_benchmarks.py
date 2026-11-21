"""Benchmarks against published tables and hand calculations.  Run:  python -m pytest -q"""
import math

import pytest

from geotech import CM2S_TO_M2YR, KGCM2_TO_KPA
from geotech.bearing import bc_factors, bearing_capacity, water_table_factor
from geotech.lab import analyse_oedometer, cu_from_uu, fit_mohr_coulomb
from geotech.profile import COHESIVE, Layer, SoilProfile, SPTRecord
from geotech.settlement import consolidation_sublayer, degree_of_consolidation, schmertmann
from geotech.spt import cn_overburden, correct_profile_spt, dilatancy
from geotech.stress import circle_centre, corner_factor, rect_centre, rect_point, two_to_one


# ---- IS 6403:1981 Table 1 -------------------------------------------------
@pytest.mark.parametrize("phi,Nc,Nq,Ng", [
    (0, 5.14, 1.00, 0.00), (10, 8.35, 2.47, 1.22), (20, 14.83, 6.40, 5.39),
    (30, 30.14, 18.40, 22.40), (40, 75.31, 64.20, 109.41),
])
def test_bc_factors_is6403_table1(phi, Nc, Nq, Ng):
    c, q, g = bc_factors(phi)
    assert c == pytest.approx(Nc, rel=2e-3)
    assert q == pytest.approx(Nq, rel=2e-3)
    assert g == pytest.approx(Ng, rel=2e-3, abs=1e-2)


def test_water_table_factor():
    assert water_table_factor(0.5, 1.5, 2.0) == 0.5
    assert water_table_factor(3.5, 1.5, 2.0) == 1.0
    assert water_table_factor(2.5, 1.5, 2.0) == pytest.approx(0.75)


# ---- Boussinesq / Newmark ---------------------------------------------------
def test_newmark_table_values():
    # Newmark chart values (Das, Table for I): m = n = 1 -> 0.1752; m = n = 2 -> 0.2325; m=0.5,n=1 -> 0.1202
    assert corner_factor(1, 1, 1) == pytest.approx(0.1752, abs=1e-4)
    assert corner_factor(2, 2, 1) == pytest.approx(0.2325, abs=1e-4)
    assert corner_factor(0.5, 1, 1) == pytest.approx(0.1202, abs=1e-4)


def test_superposition_centre_equals_4_corners():
    assert rect_point(100, 2, 3, 0, 0, 1.7) == pytest.approx(rect_centre(100, 2, 3, 1.7))
    # point at the corner
    assert rect_point(100, 2, 3, 1, 1.5, 1.7) == pytest.approx(100 * corner_factor(2, 3, 1.7))


def test_circle_and_2to1():
    assert circle_centre(100, 2, 1) == pytest.approx(100 * (1 - 1 / 2 ** 1.5))
    assert two_to_one(100, "Square", 2, 2, 2) == pytest.approx(25.0)


# ---- SPT (IS 2131) -----------------------------------------------------------
def test_spt_corrections():
    cn, capped = cn_overburden(1.0 * KGCM2_TO_KPA)  # p' = 1 kg/cm2
    assert cn == pytest.approx(0.77 * math.log10(20), rel=1e-9)
    assert dilatancy(25) == pytest.approx(20.0)
    assert dilatancy(12) == 12


def _sand_profile():
    return SoilProfile(layers=[Layer(0, 3, "sand", gamma_moist=18, gamma_sat=20, dilatancy=True),
                               Layer(3, 10, "clay", soil_type=COHESIVE, gamma_moist=18, gamma_sat=18)],
                       gwt_measured=1.0, gwt_design=0.5,
                       spt=[SPTRecord(2.0, 20)])


def test_spt_uses_measured_wt():
    p = _sand_profile()
    step = correct_profile_spt(p)[0]
    # sigma' at 2 m with measured WT 1 m: 18*1 + (20-9.81)*1 = 28.19 kPa
    assert step.sigma_eff_kpa == pytest.approx(28.19)
    n1 = 0.77 * math.log10(20 / (28.19 / KGCM2_TO_KPA)) * 20
    assert step.N1 == pytest.approx(n1)
    assert step.N2 == pytest.approx(15 + 0.5 * (n1 - 15))


# ---- Lab tools ---------------------------------------------------------------
def test_direct_shear_fit_hand_calc():
    f = fit_mohr_coulomb([50, 100, 150], [29.8, 58.9, 87.5])
    assert math.degrees(math.atan((87.5 - 29.8) / 100)) == pytest.approx(f.phi, abs=1e-9)
    assert f.c == pytest.approx(58.7333 - 0.577 * 100, abs=1e-3)


def test_uu():
    cu, _ = cu_from_uu([57.2, 55.8, 58.1])
    assert cu == pytest.approx(28.52, abs=0.01)


def test_oedometer_units_and_cc():
    r = analyse_oedometer([0.1, 0.25, 0.5, 1, 2, 4, 8, 2, 0.5],
                          [0.914, 0.897, 0.882, 0.853, 0.779, 0.692, 0.603, 0.626, 0.649],
                          ["Loading"] * 7 + ["Unloading"] * 2,
                          cv=[None, 1.2e-3, 1.1e-3, 8.9e-4, 6.3e-4, 5e-4, 4.4e-4, None, None])
    assert r.p_kpa[-3] == pytest.approx(8 * 98.0665)
    assert r.Cc == pytest.approx((0.692 - 0.603) / math.log10(2), rel=1e-6)
    assert r.cv_m2yr[4] == pytest.approx(6.3e-4 * 3155.76, rel=1e-4)
    assert 90 < r.sigma_p < 160  # Casagrande, plausible range


# ---- Settlement -----------------------------------------------------------------
def test_consolidation_cases():
    s, case = consolidation_sublayer(1.0, 1.0, 0.3, 0.03, 100, 100, 100)
    assert case == "NC" and s == pytest.approx(0.3 / 2 * math.log10(2))
    s, case = consolidation_sublayer(1.0, 1.0, 0.3, 0.03, 100, 150, 100)
    assert s == pytest.approx(0.03 / 2 * math.log10(1.5) + 0.3 / 2 * math.log10(200 / 150))


def test_terzaghi_U():
    assert degree_of_consolidation(0.197)[0] == pytest.approx(0.50, abs=2e-3)
    assert degree_of_consolidation(0.848)[0] == pytest.approx(0.90, abs=2e-3)


def test_schmertmann_hand_calc():
    # uniform sand, E = 10 MPa, square B = 2 m, Df = 1 m, q_net = 200 kPa, dry, gamma = 18
    p = SoilProfile([Layer(0, 20, "sand", gamma_moist=18, gamma_sat=20, E=10000)], 50, 50)
    r = schmertmann(p, "Square", 2.0, None, 1.0, 200.0, t_years=0.1, dz=0.001)
    sig0, sigp = 18.0, 18 * 2.0
    Izp = 0.5 + 0.1 * math.sqrt(200 / sigp)
    C1 = 1 - 0.5 * sig0 / 200
    # integral of Iz over 0..2B for the triangle: 0.5*(0.1+Izp)*1 + 0.5*Izp*3
    integral = 0.5 * (0.1 + Izp) * 1.0 + 0.5 * Izp * 3.0
    assert r.settlement == pytest.approx(C1 * 200 * integral / 10000, rel=1e-3)


# ---- Bearing capacity hand calculation ----------------------------------------
def test_bearing_square_dry_sand():
    # phi = 30, c = 0, gamma 18, B = 2, Df = 1.5, WT deep, general shear, no depth factors
    p = SoilProfile([Layer(0, 20, "sand", gamma_moist=18, gamma_sat=20, phi_eff=30)], 50, 50)
    r = bearing_capacity(p, "Square", 2.0, None, 1.5, mode="general", use_depth_factors=False)
    q = 27.0
    exp = q * (18.401 - 1) * 1.2 + 0.5 * 2 * 18 * 22.402 * 0.8
    assert r.q_nu == pytest.approx(exp, rel=1e-3)
    assert r.q_ns == pytest.approx(exp / 3, rel=1e-3)
