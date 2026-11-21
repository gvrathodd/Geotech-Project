"""Build the three hostel borehole profiles (examples/BH-*.json) from the RAW site data
in the assignment, applying the group's parameter decisions (docs/AI_LOG.md, D9-D16).

Run:  python design/build_inputs.py
The platform itself contains no site values; these JSON files are ordinary inputs that
the user can load, edit or replace.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geotech import lab, spt  # noqa: E402
from geotech.profile import COHESIVE, GRANULAR, Layer, SoilProfile, SPTRecord  # noqa: E402

# ------------------------------------------------------------------ decisions
GS = 2.70  # specific gravity of the clay (BH-1 lab, used for BH-2/BH-3)
QC_N = {"SM": 0.4, "SP": 0.5}  # MPa per blow (D11, Robertson et al. 1983)
CV = 2.0  # m2/yr, BH-1 lab value for the 1-2 kg/cm2 increment (D15)
F1_STROUD = 4.5  # cu = 4.5 N kPa (Stroud 1974) where no UU test (D15)
FILL_GSAT = 18.5  # kN/m3, assumed (fill saturated unit weight not reported)
GW = dict(soil_type=GRANULAR, gamma_moist=21.5, gamma_sat=21.5, phi_eff=40.0, E=100000.0)

# ----------------------------------------------------------- raw lab results
OED = dict(p=[0.10, 0.25, 0.50, 1.00, 2.00, 4.00, 8.00, 2.00, 0.50],
           e=[0.914, 0.897, 0.882, 0.853, 0.779, 0.692, 0.603, 0.626, 0.649],
           stage=["Loading"] * 7 + ["Unloading"] * 2,
           cv=[None, 1.2e-3, 1.1e-3, 8.9e-4, 6.3e-4, 5.0e-4, 4.4e-4, None, None])
LAB = {
    "direct_shear": [
        {"label": "SM (DS-1) unsoaked", "sigma_n": [50, 100, 150], "tau": [37.0, 67.0, 97.2]},
        {"label": "SM (DS-1) soaked 24 h", "sigma_n": [50, 100, 150], "tau": [29.8, 58.9, 87.5]},
        {"label": "SP (SPT-3) soaked 24 h", "sigma_n": [50, 100, 150], "tau": [34.9, 68.3, 103.4]},
    ],
    "uu": [{"label": "UDS-1 (7.00-7.45 m)", "sigma3": [50, 100, 150], "deviator": [57.2, 55.8, 58.1]},
           {"label": "UDS-2 (9.50-9.95 m)", "sigma3": [50, 100, 150], "deviator": [71.0, 73.4, 72.2]}],
    "oedometer": OED,
}

# ------------------------------------------------------------- raw boreholes
# (top, bottom, description, symbol, gamma_moist, gamma_sat, fines %)
RAW = {
    "BH-1": dict(
        name="BH-1 (near C4, centre) - RL 100.00 m", gwt_measured=2.6, gwt_design=1.0,
        strata=[(0.0, 0.6, "Fill (silty sand, brick bats)", "FILL", 16.5, FILL_GSAT, None),
                (0.6, 3.4, "SM medium dense silty sand", "SM", 18.0, 20.0, 20),
                (3.4, 5.8, "SP med. dense-dense sand + gravel", "SP", 19.0, 20.4, 4),
                (5.8, 10.6, "CI soft-firm silty clay", "CI", 18.6, 18.6, None),
                (10.6, 15.0, "GW very dense sandy gravel", "GW", 21.5, 21.5, None)],
        # N = 22 at 9.0 m excluded: sampler struck a cobble (D14)
        spt=[(1.5, 13, False), (3.0, 16, False), (4.5, 24, False), (6.0, 6, False), (7.5, 5, False),
             (10.5, 8, False), (12.0, 100, True), (13.5, 100, True)],
        clay=dict(w=0.34, LL=44, source="lab"),
    ),
    "BH-2": dict(
        name="BH-2 (near A1, west end) - RL 100.20 m", gwt_measured=3.2, gwt_design=1.7,
        strata=[(0.0, 0.5, "Fill (silty sand, roots)", "FILL", 16.5, FILL_GSAT, None),
                (0.5, 3.8, "SM medium dense silty sand", "SM", 18.2, 20.0, 16),
                (3.8, 7.6, "SP dense sand + gravel", "SP", 19.3, 20.6, 3),
                (7.6, 9.6, "CI firm silty clay", "CI", 18.7, 18.7, None),
                (9.6, 15.0, "GW very dense sandy gravel", "GW", 21.5, 21.5, None)],
        spt=[(1.5, 14, False), (3.0, 17, False), (4.5, 26, False), (6.0, 31, False), (7.5, 34, False),
             (9.0, 9, False), (10.5, 100, True), (12.0, 100, True)],
        clay=dict(w=0.33, LL=42, source="corr"),
    ),
    "BH-3": dict(
        name="BH-3 (near D7, east end, 25 m from stream) - RL 99.70 m", gwt_measured=1.9, gwt_design=0.6,
        strata=[(0.0, 0.9, "Fill (silty sand, organic)", "FILL", 16.0, FILL_GSAT, None),
                (0.9, 2.6, "SM loose silty fine sand", "SM", 17.5, 19.5, 24),
                (2.6, 4.4, "SP medium dense fine-medium sand", "SP", 18.6, 20.0, 6),
                (4.4, 11.2, "CI soft-firm silty clay", "CI", 18.5, 18.5, None),
                (11.2, 15.0, "GW very dense sandy gravel", "GW", 21.5, 21.5, None)],
        spt=[(1.5, 6, False), (3.0, 14, False), (4.5, 4, False), (6.0, 4, False), (7.5, 5, False),
             (9.0, 6, False), (10.5, 8, False), (12.0, 100, True), (13.5, 100, True)],
        clay=dict(w=0.35, LL=45, source="corr"),
    ),
}


def build(bh: str, oed_res, pop_kpa: float) -> tuple[dict, list]:
    r = RAW[bh]
    notes = []
    layers = []
    for top, bot, desc, sym, gm, gs, fc in r["strata"]:
        if sym == "FILL":
            layers.append(Layer(top, bot, desc, GRANULAR, gm, gs, 0.0, 28.0, E=5000.0))
        elif sym in ("SM", "SP"):
            # dilatancy correction applies to fine / silty sand (IS 2131): SM, and BH-3 fine-medium SP
            dil = sym == "SM" or (bh == "BH-3" and sym == "SP")
            layers.append(Layer(top, bot, desc, GRANULAR, gm, gs, dilatancy=dil))
        elif sym == "CI":
            layers.append(Layer(top, bot, desc, COHESIVE, gm, gs, 0.0, 0.0, drainage="Double", cv=CV))
        else:
            layers.append(Layer(top, bot, desc, **GW))
    prof = SoilProfile(layers, r["gwt_measured"], r["gwt_design"],
                       [SPTRecord(d, n, rf) for d, n, rf in r["spt"]], r["name"])

    # --- sand parameters from corrected N (D10: SPT correlation everywhere, c' = 0)
    steps = spt.correct_profile_spt(prof)
    for lay, (top, bot, desc, sym, *_rest) in zip(prof.layers, r["strata"]):
        if sym not in ("SM", "SP"):
            continue
        ns = [s.N2 for s in steps if top <= s.depth < bot and not s.refusal]
        nbar = mean(ns)
        lay.phi_eff = round(spt.phi_from_n(nbar), 1)  # Wolff (1989)
        qc, E = spt.e_from_n(nbar, QC_N[sym], 1.0)  # E = 2.5 qc (square footings)
        lay.E = round(E, -2)
        lay.c_eff = 0.0
        notes.append(f"{bh} {sym}: corrected N'' = {', '.join(f'{x:.1f}' for x in ns)} -> mean {nbar:.1f}; "
                     f"phi' = {lay.phi_eff} deg; qc = {qc / 1000:.2f} MPa; E = {lay.E / 1000:.1f} MPa")

    # --- clay parameters
    clay = next(l for l in prof.layers if l.soil_type == COHESIVE)
    c = r["clay"]
    if c["source"] == "lab":
        clay.Cc, clay.Cs, clay.e0 = round(oed_res.Cc, 3), round(oed_res.Cs, 4), 0.918
        clay.cu = 28.5  # UDS-1 UU, lower of the two samples (D15)
    else:
        clay.Cc = round(lab.cc_terzaghi_peck(c["LL"]), 3)  # 0.009 (LL - 10)
        clay.Cs = round(clay.Cc * oed_res.Cs / oed_res.Cc, 4)  # Cs/Cc ratio from BH-1 test
        clay.e0 = round(lab.e0_saturated(c["w"], GS), 3)  # e0 = w Gs
        clay_ns = [n for d, n, rf in r["spt"] if clay.top <= d < clay.bottom]
        clay.cu = round(F1_STROUD * mean(clay_ns), 1)  # Stroud (1974)
    if bh == "BH-3":
        clay.history, clay.history_value = "NC", 1.0  # D9: softest clay, near the stream
    else:
        clay.history, clay.history_value = "POP", round(pop_kpa, 1)  # D9
    clay.undrained = False
    notes.append(f"{bh} clay: Cc = {clay.Cc}, Cs = {clay.Cs}, e0 = {clay.e0}, cu = {clay.cu} kPa, "
                 f"history = {clay.history} {clay.history_value if clay.history != 'NC' else ''}, cv = {clay.cv} m2/yr")

    d = prof.to_dict()
    d["lab"] = LAB if bh == "BH-1" else {}
    d["fines"] = {l.description: fc for l, (*_, fc) in zip(prof.layers, r["strata"]) if fc is not None}
    return d, notes


def main():
    oed = lab.analyse_oedometer(OED["p"], OED["e"], OED["stage"], "kg/cm2", OED["cv"], "cm2/s")
    # POP from BH-1: sigma'_p (Casagrande) minus sigma'_v0 at the UDS-1 mid-depth with the DESIGN WT (D7)
    bh1_tmp, _ = build("BH-1", oed, 0.0)
    p1 = SoilProfile.from_dict(bh1_tmp)
    z_s = (7.00 + 7.45) / 2
    s0 = p1.sigma_eff(z_s, p1.gwt_design)
    pop = oed.sigma_p - s0
    print(f"Oedometer: Cc = {oed.Cc:.3f}, Cs = {oed.Cs:.4f}, sigma'_p = {oed.sigma_p:.1f} kPa")
    print(f"BH-1 sigma'_v0 at {z_s:.3f} m (design WT {p1.gwt_design} m) = {s0:.1f} kPa -> "
          f"POP = {pop:.1f} kPa, OCR = {oed.sigma_p / s0:.2f}")
    out = ROOT / "examples"
    out.mkdir(exist_ok=True)
    all_notes = [f"POP = {pop:.1f} kPa (sigma'_p {oed.sigma_p:.1f} - sigma'_v0 {s0:.1f} at {z_s:.3f} m)"]
    for bh in RAW:
        d, notes = build(bh, oed, pop)
        (out / f"{bh}.json").write_text(json.dumps(d, indent=2))
        all_notes += notes
    (ROOT / "design" / "out").mkdir(exist_ok=True, parents=True)
    (ROOT / "design" / "out" / "parameters.txt").write_text("\n".join(all_notes))
    print("\n".join(all_notes))


if __name__ == "__main__":
    main()
