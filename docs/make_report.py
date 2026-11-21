"""Generate the Word report from the design outputs (design/out) and docs/AI_LOG.md.

Run after design/build_inputs.py and design/hostel_design.py:
    python docs/make_report.py
Text marked [GROUP ...] must be completed or confirmed by the group.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geotech import bearing as bc  # noqa: E402
from geotech import lab, spt  # noqa: E402
from geotech.profile import SoilProfile  # noqa: E402

OUT = ROOT / "design" / "out"
DOCX = ROOT / "docs" / "CE402_Group1_Report.docx"

GROUP = dict(
    members="[GROUP: Name 1 (Roll no.), Name 2 (Roll no.), Name 3 (Roll no.), Name 4 (Roll no.), Name 5 (Roll no.)]",
    url="https://foundation-studio-237377681531.us-central1.run.app",
    repo="https://github.com/gvrathodd/Geotech-Project",
)

S = json.loads((OUT / "summary.json").read_text())
F = pd.read_csv(OUT / "footings.csv")
SI = pd.read_csv(OUT / "settlement_interaction.csv")
SO = pd.read_csv(OUT / "settlement_isolated.csv")
DI = pd.read_csv(OUT / "differential.csv")
LQ = pd.read_csv(OUT / "liquefaction.csv")
RF = pd.read_csv(OUT / "raft.csv")
PL = pd.read_csv(OUT / "piles.csv")
CP = pd.read_csv(OUT / "cprf.csv")
PZ = json.loads((OUT / "pile_zones.json").read_text())
PROF = {bh: SoilProfile.from_dict(json.loads((ROOT / "examples" / f"{bh}.json").read_text()))
        for bh in ("BH-1", "BH-2", "BH-3")}

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(10.5)
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.0)
    s.top_margin = s.bottom_margin = Cm(1.8)


def H(t, l=1):
    doc.add_heading(t, level=l)


def P(t="", bold=False, italic=False, size=None, align=None, color=None):
    p = doc.add_paragraph()
    parts = re.split(r"(\*\*[^*]+\*\*)", t)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            r = p.add_run(part[2:-2])
            r.bold = True
        else:
            r = p.add_run(part)
            r.bold = bold
        r.italic = italic
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = RGBColor(*color)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def B(t):
    p = doc.add_paragraph(style="List Bullet")
    parts = re.split(r"(\*\*[^*]+\*\*)", t)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            p.add_run(part[2:-2]).bold = True
        else:
            p.add_run(part)
    return p


def T(df: pd.DataFrame, widths=None, size=8.5, fmt=None):
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, c in enumerate(df.columns):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(str(c))
        r.bold = True
        r.font.size = Pt(size)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for i, v in enumerate(row):
            if isinstance(v, float):
                v = "–" if (math.isnan(v) or math.isinf(v)) else (fmt or "{:.2f}").format(v)
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(str(v)).font.size = Pt(size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph()
    return t


def FIG(name, caption, w=16):
    doc.add_picture(str(OUT / name), width=Cm(w))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    P(caption, italic=True, size=9, align="c")


# ============================================================== title
P("School of Civil and Environmental Engineering, IIT Mandi", bold=True, size=12, align="c")
P("CE 402 Geotechnical Engineering – Assignment", bold=True, size=14, align="c")
P("Foundation design of a G+3 students' hostel, Mandi (Zone V)\nand a web platform for shallow-foundation design",
  bold=True, size=16, align="c")
P("Group 1  (λ = 1 + g/100 = 1.01)", size=12, align="c")
P(GROUP["members"], align="c")
P(f"Platform: {GROUP['url']}\nSource code: {GROUP['repo']}", align="c")
P("Submitted: 26 November 2026", align="c")

H("Summary", 1)
P(f"The hostel's 28 columns (total service load {S['total_P']:.0f} kN, including the λ = 1.01 factor) "
  "were first designed on isolated footings at Df = 1.5 m to IS 6403:1981 with FS = 3. "
  "**Every footing passes bearing capacity**, with sizes from 1.5 m (BH-2 corners) to 3.7 m (BH-3 interior). "
  f"**Settlement does not pass.** With stress overlap from neighbouring footings included, the soft normally "
  f"consolidated clay under the east end (BH-3) gives total settlements of up to {S['s_max']:.0f} mm "
  f"(column {S['s_max_col']}) against the 75 mm limit of IS 1904:1986. The differential settlement "
  f"reaches {S['d_max']:.0f} mm ({S['d_max_pair']}; angular distortion 1/{1 / S['ang_max']:.0f}) against "
  "10 mm and 1/500. The IS 1893 Annex F check shows that the saturated sands at footing level "
  f"**liquefy in all three boreholes** (FS = {min(r[2] for r in S['liq_fail']):.2f}–"
  f"{max(r[2] for r in S['liq_fail']):.2f}). A raft fails as well ({S['raft_s_max']:.0f} mm at BH-3). "
  "A combined piled raft (CPRF) was analysed by the PDR method: the raft would carry only "
  f"{CP.raft_share.min() * 100:.1f}–{CP.raft_share.iloc[1] * 100:.1f}% of the load over the clay zones, "
  "so it was rejected. **The adopted foundation is 2 × Ø750 mm bored cast-in-situ piles per column**, "
  "socketed 2.5 m into the very dense gravel (tips 12.1–13.7 m bgl), with pile caps tied by plinth beams. "
  f"The largest pile-group settlement is {PL.s_tot.max():.1f} mm and the largest differential is "
  f"{S['pile_d_max']:.1f} mm, both within IS 1904.")

# ============================================================== 1
H("1  Scope and assumptions", 1)
B("Building: G+3 RC frame with masonry infill, 30 m × 15 m on a 5 m × 5 m grid (lines 1–7 run west to east, A–D across). "
  "Seismic zone V; perennial stream about 25 m east of the building.")
B("Loads: the brief's service loads × λ = 1.01 (group 1). Corner 656.5 kN, edge 1010 kN, interior 1464.5 kN.")
B("**Column C4** is missing from the load table, which lists 27 of the 28 columns. We assumed P = 1464.5 kN with "
  "M = 50 kN·m acting along the building length (east–west), so e = 0.034 m. The professor was informed "
  "by e-mail on 21 Nov 2026.")
B("Modules P6 and P7 are absent from the brief. Only P1–P5 and P8 are implemented, plus a liquefaction tab "
  "(see §7 for the justification).")
B("Borehole zoning as given in the brief: BH-2 for lines 1–2, BH-1 for lines 3–5, BH-3 for lines 6–7. "
  "Group 1 leads on BH-1, the only borehole with laboratory tests.")
B("Footing + backfill unit weight 20 kN/m³. Net applied pressure = (P + W_f − σv(Df)·A)/A′.")

# ============================================================== 2
H("2  Site and subsurface interpretation", 1)
P("All three boreholes show the same sequence: fill (0.5–0.9 m), silty sand SM, poorly graded sand SP, "
  "silty clay of intermediate plasticity CI, and very dense sandy gravel GW with cobbles and boulders. "
  "The GW gives SPT refusal and was proved to the end of each borehole at 15 m. The clay thickens and "
  "softens from west to east: 2.0 m and firm in BH-2 (N = 9), 4.8 m in BH-1 (N = 5–8), and "
  "6.8 m and soft in BH-3 (N = 4–8), where its top is only 2.9 m below the founding level.")
B("**Water tables.** The 24-hour readings are not equilibrium levels. They are used only for the SPT "
  "corrections, which apply to conditions at the time of testing. The **design water table** is the "
  "highest seasonal (August) level: 1.0, 1.7 and 0.6 m bgl for BH-1, BH-2 and BH-3. In BH-1 and BH-3 "
  "this is above the founding level, so W′ = 0.5.")
B("**BH-1 N = 22 at 9.0 m is excluded.** The sampler struck a cobble and recovered only gravel; the "
  "clay gives N = 5–8 above and below.")
B("The fill contains brick bats, roots and organic matter, and is removed by founding at 1.5 m. Its "
  "saturated unit weight (not reported) was taken as 18.5 kN/m³.")
FIG("profiles.png", "Figure 1 – Design soil profiles with the adopted parameters (west to east).", 16)

# ============================================================== 3
H("3  Parameter derivation (platform module P2)", 1)
H("3.1  SPT corrections – IS 2131:1981", 2)
P("The corrections are applied in the code's order: overburden first, using the effective stress at the "
  "measured (October) water table, with C_N = 0.77 log₁₀(20/p′) and p′ in kg/cm²; then dilatancy, "
  "N″ = 15 + 0.5(N′ − 15), for saturated fine or silty sand with N′ > 15. Refusal values and clay "
  "layers are not corrected.")
rows = []
for bh, p in PROF.items():
    for s in spt.correct_profile_spt(p):
        if s.refusal or s.soil_type == "Cohesive":
            continue
        rows.append([bh, s.depth, s.layer.split(" ")[0], s.N, s.sigma_eff_kpa, s.sigma_eff_kgcm2, s.CN, s.N1,
                     "yes" if s.dilatancy_applies else "no", s.N2, spt.phi_from_n(s.N2)])
T(pd.DataFrame(rows, columns=["BH", "z (m)", "Soil", "N", "σ′v (kPa)", "p′ (kg/cm²)", "C_N", "N′", "Dilat.",
                              "N″", "φ′ Wolff (°)"]))
H("3.2  Laboratory tests (BH-1)", 2)
fits = []
for lbl, tau in [("SM unsoaked", [37.0, 67.0, 97.2]), ("SM soaked 24 h", [29.8, 58.9, 87.5]),
                 ("SP soaked 24 h", [34.9, 68.3, 103.4])]:
    f = lab.fit_mohr_coulomb([50, 100, 150], tau)
    fits.append([lbl, f.c, f.phi, f.r2])
T(pd.DataFrame(fits, columns=["Direct shear", "c′ (kPa)", "φ′ (°)", "R²"]), fmt="{:.3f}")
P("The unsoaked SM gives c′ = 6.9 kPa. This intercept comes from suction (w = 10%) and vanishes on soaking "
  "(c′ = 1.0 kPa, which is fitting noise), so c′ = 0 is used for all sands. UU tests: cu = (σ1 − σ3)f/2 = "
  "28.5 kPa (UDS-1) and 36.1 kPa (UDS-2). φu ≈ 0, which confirms saturation.")
oed = lab.analyse_oedometer([0.1, 0.25, 0.5, 1, 2, 4, 8, 2, 0.5],
                            [0.914, 0.897, 0.882, 0.853, 0.779, 0.692, 0.603, 0.626, 0.649],
                            ["Loading"] * 7 + ["Unloading"] * 2)
P(f"Oedometer (UDS-1): pressures converted from kg/cm² (× 98.07). Cc = {oed.Cc:.3f} (4–8 kg/cm²), "
  f"Cs = {oed.Cs:.4f} (unloading), and the Casagrande construction gives σ′p = {oed.sigma_p:.0f} kPa "
  f"({oed.sigma_p / 98.0665:.2f} kg/cm²). A check: e0 = wGs = 0.34 × 2.70 = 0.918, the same as the reported "
  "e0, so the specimen was saturated. The Terzaghi & Peck correlation 0.009(LL − 10) = 0.306 agrees with the "
  "measured Cc. cv (cm²/s × 3155.76 = m²/yr) ranges from 3.8 to 1.4 m²/yr. **cv = 2.0 m²/yr** (the "
  "1–2 kg/cm² increment, which matches the field stress range) is adopted.")
P("**Stress history.** At the UDS-1 depth (7.225 m), σ′v0 at the design water table is 79.5 kPa, giving "
  "POP = 116.6 − 79.5 = **37 kPa** (OCR = 1.47). The seasonal water-table swing (1.0 to 3.6 m) alone "
  "produces about 25 kPa of pre-loading, which explains most of this. POP = 37 kPa is adopted for the "
  "BH-1 and BH-2 clay. BH-3 has the softest clay, lies near the stream and has no undisturbed sample, so "
  "it is treated as **normally consolidated** (conservative).")
H("3.3  Adopted design parameters", 2)
rows = []
for bh, p in PROF.items():
    for l in p.sorted_layers():
        if l.soil_type == "Granular":
            rows.append([bh, f"{l.top:g}–{l.bottom:g}", l.description[:30], l.gamma_moist, l.gamma_sat,
                         f"{l.phi_eff:.1f}", f"{l.E / 1000:.1f}", "–", "–", "–", "–"])
        else:
            rows.append([bh, f"{l.top:g}–{l.bottom:g}", l.description[:30], l.gamma_moist, l.gamma_sat, "–", "–",
                         f"{l.cu:.1f}", f"{l.Cc:.3f}/{l.Cs:.4f}", f"{l.e0:.3f}",
                         "NC" if l.history == "NC" else f"POP {l.history_value:.0f}"])
T(pd.DataFrame(rows, columns=["BH", "Depth (m)", "Layer", "γ (kN/m³)", "γsat (kN/m³)", "φ′ (°)", "E (MPa)",
                              "cu (kPa)", "Cc/Cs", "e0", "History"]), size=7.5)
P("Sand φ′ comes from the corrected N (Wolff 1989) at every borehole. This was a group decision: the remoulded "
  "lab specimens do not reflect each borehole's in-situ density (lab SM 30.0° against SPT 32.3–33.0°). "
  "[GROUP: confirm the reasoning.] E = 2.5 qc with qc/N = 0.4 MPa (SM) and 0.5 MPa (SP) (Robertson et al. "
  "1983). For BH-2 and BH-3: Cc = 0.009(LL − 10), e0 = wGs, Cs from the BH-1 Cs/Cc ratio, and cu = 4.5N "
  "(Stroud 1974).")

# ============================================================== 4
H("4  Design criteria", 1)
B("Bearing: FS = 3.0 on the net ultimate bearing capacity (IS 6403:1981), compared with the net applied pressure.")
B("**Settlement limits, IS 1904:1986 Table 1.** The building is a multistoreyed RC framed building with "
  "panel (masonry infill) walls on isolated footings, so we adopt that row of the table: maximum settlement "
  "75 mm (plastic clay; 60 mm on sand), differential settlement 0.002L = 10 mm over the 5 m span, and "
  "angular distortion 1/500. The masonry infill is what makes the frame sensitive to distortion, which is "
  "why this row applies and not the bare-frame RC row. [GROUP: verify the values and quote the table row "
  "from your copy of IS 1904.]")
B("Piles: FS = 2.5 on the ultimate capacity from static formulae (IS 2911 Part 1/Sec 2).")

# ============================================================== 5
H("5  Isolated footings (P3)", 1)
sz = F.groupby(["zone", "type"], sort=False).agg(B=("B", "first"), L=("L", "first"), P=("P", "first"),
                                                  phi=("phi", "first"), W=("W", "first"), q_nu=("q_nu", "first"),
                                                  q_ns=("q_ns", "first"), q_net=("q_net", "first"),
                                                  weak=("weak_FS", "first")).reset_index()
sz.columns = ["Zone", "Column type", "B (m)", "L (m)", "P (kN)", "φ′ (°)", "W′", "q_nu (kPa)", "q_ns (kPa)",
              "q_net (kPa)", "Soft-layer FS"]
T(sz, size=8)
r = bc.bearing_capacity(PROF["BH-1"], "Square", 2.6, None, 1.5, P=1464.5, FS=3, gamma_fill=20)
P(f"**Worked example – interior column B4 (BH-1), 2.6 m × 2.6 m, Df = 1.5 m.** Design water table "
  f"at 1.0 m, so q = σ′v(1.5 m) = {r.q:.1f} kPa and W′ = {r.W:.2f}. Bulk γ below the base = {r.gamma:.1f} kN/m³. "
  f"φ′ = {r.phi:.1f}°. General shear: Nq = {r.general.Nq:.2f}, Nγ = {r.general.Ng:.2f}. Local shear "
  f"(tan φm = 0.67 tan φ → φm = {r.local.phi:.1f}°): Nq = {r.local.Nq:.2f}, Nγ = {r.local.Ng:.2f}. "
  f"sq = 1.2, sγ = 0.8, dq = dγ = {r.dq:.3f}. q_nu(general) = {r.general.q_nu:.0f} kPa and "
  f"q_nu(local) = {r.local.q_nu:.0f} kPa. Interpolating by φ between 28° and 36° gives "
  f"q_nu = {r.q_nu:.0f} kPa, so q_ns = {r.q_ns:.0f} kPa. Net applied = (1464.5 + 20 × 2.6² × 1.5 − "
  f"{r.sigma_tot_Df:.1f} × 2.6²)/2.6² = {r.q_net_applied:.0f} kPa ≤ q_ns. OK.")
P("**C4 (eccentric):** a 2.5 × 3.0 m rectangle with its long side east–west. e = 50/1464.5 = 0.034 m, "
  "so L′ = 3.0 − 2 × 0.034 = 2.93 m. The effective area is used in all the shape factors and the γ term.")
P("All 28 footings satisfy bearing capacity, and the soft-clay check by 2:1 projection has FS ≥ 4.3. "
  "Bearing capacity is therefore **not** what governs.")

# ============================================================== 6
H("6  Settlement of isolated footings (P4, P5)", 1)
P("Sands are analysed by Schmertmann et al. (1978), with C2 = 1 for the end-of-construction value. The clay "
  "is analysed by 1-D consolidation in 0.5 m sublayers. The stress increase in the clay is the Boussinesq "
  "superposition of **all 28 footings**: at 5 m spacing, the influence zones of neighbouring footings "
  "overlap at clay depth. Treating each footing in isolation would underestimate the BH-3 consolidation "
  "by about half (see the AI audit).")
FIG("stress_C4.png", "Figure 2a – Δσz below column C4: Boussinesq centre and corner, and the 2:1 method (P4).", 8)
m = F[["col", "zone", "type", "B", "q_net"]].merge(SI[["col", "s_imm", "s_con", "s_tot", "t90"]], on="col").merge(
    SO[["col", "s_con"]].rename(columns={"s_con": "s_con_iso"}), on="col")
m = m[["col", "zone", "type", "B", "q_net", "s_imm", "s_con_iso", "s_con", "s_tot", "t90"]]
m.columns = ["Col", "Zone", "Type", "B (m)", "q_net (kPa)", "Sand (mm)", "Clay alone (mm)", "Clay + interaction (mm)",
             "Total (mm)", "t90 (yr)"]
T(m, size=7.5, fmt="{:.1f}")
FIG("plan_settlement.png", "Figure 2 – Total settlement of isolated footings, including interaction (mm).", 16)
dd = DI.sort_values("d", ascending=False).head(6).copy()
dd["ang"] = dd["ang"].map(lambda a: f"1/{1 / a:.0f}")
dd.columns = ["Adjacent pair", "Differential (mm)", "Angular distortion", "≤ 10 mm", "≤ 1/500"]
T(dd, fmt="{:.1f}")
P(f"**Verdict:** {S['n_total_fail']} of 28 columns exceed 75 mm (all of the BH-3 zone) and {S['n_diff_fail']} of "
  f"{S['n_pairs']} adjacent pairs exceed the differential or angular limit. The worst pair is across the "
  "BH-1/BH-3 boundary (lines 5–6). Consolidation in BH-3 reaches 90% in about 5 years (t90, with double "
  "drainage between SP and GW), so the damage would appear after occupation. Isolated footings are "
  "**not acceptable** (criterion 3 of the brief).")
FIG("time_settlement.png", "Figure 3 – Time–settlement for representative columns (Terzaghi, double drainage).", 12)

# ============================================================== 7
H("7  Liquefaction check (IS 1893 (Part 1):2016 Annex F)", 1)
P("The brief does not ask for this check. We added it because the site is in zone V, 25 m from a "
  "perennial stream, and has saturated loose to medium dense sands at the founding level. "
  "Inputs: a_max = Z = 0.36g (zone V), Mw = 8.0 (group decision, conservative for the Himalayan "
  "frontal region), hammer energy 60%, 150 mm borehole, design (August) water table, and fines from the "
  "borehole logs. Clay layers and SPT refusals are screened out.")
lq = LQ[LQ.status.str.startswith(("Liq", "Marg", "Safe"))][["BH", "depth", "N", "layer", "sigma_eff", "CSR",
                                                            "N1_60cs", "CRR75", "FS", "status"]].copy()
lq["layer"] = lq["layer"].str.split(" ").str[0]
lq.columns = ["BH", "z (m)", "N", "Soil", "σ′v (kPa)", "CSR", "(N1)60cs", "CRR7.5", "FS_L", "Status"]
T(lq, size=8)
FIG("liquefaction.png", "Figure 4 – Factor of safety against liquefaction.", 9)
P("The sands at and just below footing level are **liquefiable in all three boreholes**. A footing or raft "
  "resting on them would lose bearing and settle unevenly during the design earthquake. This is a second, "
  "independent reason to transfer the load below these layers.")

# ============================================================== 8
H("8  Alternative foundation", 1)
H("8.1  Raft", 2)
P(f"A 16 m × 31 m raft at 1.5 m depth (0.5 m projection) has q_net ≈ {S['raft_q_net']:.0f} kPa. Because the "
  "loaded area is large, the stress reaches the full depth of the clay with little dispersion. The flexible-raft "
  f"consolidation under the BH-3 zone is up to {S['raft_s_max']:.0f} mm, with a differential of "
  f"{S['raft_d_max']:.0f} mm between columns. A raft also rests on the liquefiable sand. **Rejected.**")
H("8.2  Combined piled raft (CPRF)", 2)
P("Poulos (2001) lists the soil profiles that are unfavourable for piled rafts: soft clay or loose sand near "
  "the surface, compressible layers at shallow depth, and soils that will consolidate. All of them occur "
  "here. We nevertheless checked the raft's load share by the Poulos–Davis–Randolph method, using the "
  "long-term raft stiffness from §8.1 over a 5 × 5 m tributary area, the pile-group stiffness from §8.3, "
  "and αrp = 0.8.")
cp = CP.copy()
cp.columns = ["Column", "Zone", "K_raft (MN/m)", "K_piles (MN/m)", "K_CPRF (MN/m)", "Raft share",
              "s piles (mm)", "s CPRF (mm)"]
cp["Raft share"] = cp["Raft share"].map(lambda v: f"{v * 100:.1f}%")
T(cp, fmt="{:.1f}")
P("Over the clay zones the raft would carry only 1–6% of the load. The piles carry practically everything, "
  "and the raft only adds cost. At BH-2 the share reaches 39%, but the sand that would provide it liquefies "
  "at 3 m, so it cannot be relied on in an earthquake. A building should also have one foundation system, "
  "not a mixture. **CPRF rejected.**")
H("8.3  Adopted: bored cast-in-situ piles (PF)", 2)
z1 = PZ["BH-3"]
P(f"Ø750 mm bored cast-in-situ RC piles (IS 2911 Part 1/Sec 2), installed with temporary casing and "
  "chiselling through cobbles and boulders, socketed 2.5 m (> 3D) into the very dense GW. The pile tips "
  f"are at {PZ['BH-2']['tip']:.1f}, {PZ['BH-1']['tip']:.1f} and {PZ['BH-3']['tip']:.1f} m bgl in the BH-2, "
  "BH-1 and BH-3 zones. Shaft friction above the gravel is ignored, because those layers are liquefiable "
  "sand and soft clay. Dragload from the re-consolidating liquefied sand (β = 0.25) is deducted from the "
  "allowable load.")
pz = pd.DataFrame([[bh, v["tip"], v["Qp"], v["Qs"], v["Qu"], v["Qa"], v["NSF"], v["Qa_net"]] for bh, v in PZ.items()],
                  columns=["Zone", "Tip (m)", "Qp (kN)", "Qs (kN)", "Qu (kN)", "Qu/2.5 (kN)", "Dragload (kN)",
                           "Qa net (kN)"])
T(pz, fmt="{:.0f}")
P("Reese & O'Neill (1989): q_p = 4310 kPa, because N60 > 75 at refusal. "
  "Shaft in GW: fs = βσ′v with β = 1.5 − 0.244√z.")
if PZ["BH-1"].get("is2911_Qu"):
    P("IS 2911 Annex B cross-check: " + ", ".join(
        f"{bh} Qu = {v['is2911_Qu']:.0f} kN" for bh, v in PZ.items()) + ".")
else:
    P("[GROUP: IS 2911 Annex B cross-check – enter Nq read from IS 2911 Fig. 1 for φ = 40° in "
      "design/hostel_design.py (NQ_IS2911) and re-run; the result is printed here.]", color=(192, 0, 0))
pl = PL.groupby(["zone", "P"], sort=False).agg(n=("n", "first"), cap=("cap", "first"), Q=("Q_per_pile", "first"),
                                               Qa=("Qa_net", "first"), u=("util", "first"),
                                               s=("s_tot", "first")).reset_index()
pl.columns = ["Zone", "P (kN)", "Piles", "Cap (m)", "Load/pile (kN)", "Qa net (kN)", "Utilisation", "Settlement (mm)"]
T(pl, fmt="{:.2f}")
P(f"**C4:** a 2-pile cap aligned east–west (pile spacing 2.25 m). The moment adds ±50/2.25 = ±22 kN, so the "
  f"heavier pile carries 775.6 + 22.2 = 797.8 kN ≤ {PZ['BH-1']['Qa_net']:.0f} kN. OK.")
P("**Settlement** (Vesic 1977 single pile × group ratio n^0.5): at most "
  f"{PL.s_tot.max():.1f} mm. The largest differential between adjacent columns is {S['pile_d_max']:.1f} mm "
  f"(1/{1 / S['pile_ang_max']:.0f}) ≤ 10 mm and 1/500. **All IS 1904 criteria are satisfied.**")
H("8.4  Recommendations", 2)
for t in [
    "Tie all pile caps in both directions with plinth beams (zone V); 2-pile caps need the transverse ties for stability.",
    "Design the piles for lateral seismic load with the pile head unsupported through the liquefiable layer "
    "(IS 2911 Part 1/Sec 2, Annex C). This needs the structural base shear, which is outside this scope.",
    "Carry out initial vertical load tests on 2 trial piles (IS 2911 Part 4) to confirm Qa before working piles are cast.",
    "Drill two more boreholes to at least 5D below the pile tips (≥ 17 m). The present boreholes stop "
    "1.3–2.9 m below the tips, and the gravel must be shown to be continuous and not a boulder layer over softer soil.",
    "Protect the stream bank against scour and lateral spreading. Keep the plinth level above the August "
    "water level and provide drainage.",
]:
    B(t)

# ============================================================== 9
H("9  The platform (P1–P5, P8)", 1)
P(f"Public URL: {GROUP['url']}  ·  GitHub: {GROUP['repo']}. Python + Streamlit. The calculation core "
  "(`geotech/`) is separate from the interface (`app.py`), and every equation is commented with its source. "
  "No site values are hard-coded: BH-1/2/3 are example JSON inputs produced from the raw data by "
  "`design/build_inputs.py`, and any profile can be typed in, uploaded or downloaded.")
for t in [
    "P1 – a layered profile with all strength, stiffness and consolidation parameters, plus measured and "
    "design water tables. It plots the strata, σv, u, σ′v and SPT N.",
    "P2 – IS 2131 corrections with every step tabulated; least-squares c′, φ′; UU cu; oedometer Cc, Cs, "
    "Casagrande σ′p and cv with unit conversion; correlations.",
    "P3 – IS 6403 for strip, square, rectangle and circle; general, local or interpolated shear; every "
    "factor and W′ displayed; effective area; footing sizing; soft-layer check.",
    "P4 – Boussinesq centre and corner (superposition) and 2:1, with Δσz plotted against depth; stress at any point.",
    "P5 – Schmertmann (1978); NC/OC consolidation in sublayers ≤ 0.5 m; time–settlement with user-selected drainage.",
    "Verification – 18 automated benchmark tests (IS 6403 Table 1 factors, Newmark influence values, "
    "Terzaghi U(Tv), and hand calculations for each module): `python -m pytest`.",
]:
    B(t)

# ============================================================== 10
H("10  References", 1)
src = (ROOT / "SOURCES.md").read_text(encoding="utf-8")
for line in src.splitlines():
    if line.startswith("| ") and not line.startswith("| Code") and not line.startswith("| Reference") \
            and not line.startswith("|---"):
        ref = line.split("|")[1].strip()
        p = doc.add_paragraph(style="List Number")
        p.add_run(ref).font.size = Pt(9)

# ============================================================== Appendix A – AI audit
doc.add_page_break()
H("Appendix A – AI audit (errors and weaknesses found in AI output)", 1)
P("[GROUP: each item below was found during the work. Re-check each one yourselves and edit the wording "
  "so it describes your own verification.]", italic=True, color=(192, 0, 0))
audit = [
    ("A1 – Wrong source and value for the Cc correlation",
     "In its first analysis the AI wrote: \"Skempton's correlation 0.009(LL − 10) gives about 0.31\".",
     "We checked the sources. Skempton (1944) gives 0.007(LL − 10) for remoulded clay; 0.009(LL − 10) is "
     "Terzaghi & Peck (1967) for undisturbed clay. For BH-3 (LL = 45), 0.007 gives Cc = 0.245 instead of "
     "0.315, which is 22% less settlement and would be unconservative.",
     "The code (`lab.py`) implements both with correct citations. The design uses 0.009(LL − 10), which "
     "matches the measured BH-1 value (0.306 against 0.296)."),
    ("A2 – IS 1904 limits taken from the wrong table row",
     "The AI's first answer: \"about 50 mm total on sand (75 mm on plastic clay), differential 0.0033L, angular "
     "distortion 1/300\". Later it quoted 0.002L and 1/500 for the same building.",
     "The two answers are inconsistent. Checking Table 1 of IS 1904:1986 [GROUP: confirm] shows that "
     "0.0033L and 1/300 are the values for steel structures. A G+3 RC frame with masonry infill falls under "
     "multistoreyed RC framed buildings with panel walls: 0.002L and 1/500.",
     "Adopted 75 mm, 0.002L = 10 mm and 1/500. The first answer would have allowed 16.5 mm of differential "
     "settlement, 65% more than permitted."),
    ("A3 – Unit inconsistency in the SPT overburden correction",
     "In its first analysis the AI gave C_N = 0.77 log₁₀(2000/σ′v), σ′ in kPa. The code uses "
     "0.77 log₁₀(20/p′), p′ in kg/cm².",
     "20 kg/cm² = 1961 kPa, not 2000 kPa. Hand calculation for BH-1 at 1.5 m (σ′ = 26.1 kPa): 1.451 with the "
     "kPa form against 1.445 with the kg/cm² form of the IS 2131 Fig. 1 curve.",
     "The code keeps the kg/cm² form (the units of the code figure) and converts kPa → kg/cm² explicitly "
     "(÷ 98.07). The error is small here, but this is exactly the kind of hidden unit change the brief warns about."),
    ("A4 – Footing interaction ignored in settlement",
     "The AI's settlement module (P5) treats one footing at a time. Applied column by column, it gives "
     "67–121 mm for the BH-3 zone.",
     "At 5 m spacing with B = 2.6–3.7 m, the Boussinesq stresses from neighbouring footings overlap "
     "strongly at clay depth (4–11 m). Superposing all 28 footings doubles the BH-3 consolidation "
     "(B6: 121 → 236 mm) and changes the corner/interior pattern of settlement.",
     "The design script superposes all footings (`stress.group_stress`). This weakness affects the result "
     "only in degree, since the footings fail either way, but the differential-settlement pattern is quite different."),
    ("A5 – Local shear and undrained flag in the first version of the bearing module",
     "The first version of `bearing.py` ignored the local-shear mode for undrained (φ = 0) layers and used "
     "redundant logic to decide 'undrained'.",
     "Code review against IS 6403 cl. 5.1.2(b): local shear uses ⅔c. On soft clay the first version "
     "overestimated q_nu by 50%.",
     "Corrected: undrained uses the user flag only, and local shear applies 2/3 cu. Benchmark tests were added."),
    ("A6 – Depth factors computed with the reduced width B′ for eccentric footings",
     "The AI's bearing module replaced B with B′ everywhere, including the depth factors (D_f/B′).",
     "Benchmark against CE 402 class notes, M3 Problem 6 (2.4 × 3.0 m footing, e = 0.40 m): the notes take "
     "D_f/B with B = 2.4 m, giving d_c = 1.166 and d_q = 1.083. The platform gave 1.250 and 1.125, which overstates "
     "q_nu. The same check showed a false 'e > B/6' warning at e = B/6 exactly, caused by floating-point rounding.",
     "The depth factors now use the actual width B (B′ only in the shape factors and the γ term); the kern check has a "
     "tolerance. The notes' Problem 6 and Q12 were added as permanent tests. The hostel design is unchanged "
     "(C4 e = 0.034 m)."),
]
for title, out, detect, fix in audit:
    P(title, bold=True)
    P("AI output: " + out, size=9.5)
    P("Detection: " + detect, size=9.5)
    P("Correction: " + fix, size=9.5)

# ============================================================== Appendix B – AI log
doc.add_page_break()
H("Appendix B – AI log", 1)
logmd = (ROOT / "docs" / "AI_LOG.md").read_text(encoding="utf-8")
table_buf = []


def flush_table():
    global table_buf
    if not table_buf:
        return
    rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table_buf if not re.match(r"^\|[-| ]+\|$", r.strip())]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    T(df, size=7.5)
    table_buf = []


for line in logmd.splitlines():
    if line.strip().startswith("|"):
        table_buf.append(line)
        continue
    flush_table()
    if line.startswith("# "):
        continue
    if line.startswith("## "):
        H(line[3:], 2)
    elif line.startswith("### "):
        H(line[4:], 3)
    elif re.match(r"^\d+\. ", line):
        doc.add_paragraph(re.sub(r"^\d+\. ", "", line), style="List Number")
    elif line.startswith("- "):
        B(line[2:])
    elif line.startswith(">"):
        P(line.lstrip("> "), italic=True, size=9)
    elif line.strip() and line.strip() != "---":
        P(line)
flush_table()

# ============================================================== Appendix C
doc.add_page_break()
H("Appendix C – Column-by-column foundation schedule (adopted pile foundation)", 1)
c = PL[["col", "zone", "P", "n", "cap", "W_cap", "Q_per_pile", "Qa_net", "util", "tip", "s_tot"]].copy()
c.columns = ["Col", "Zone", "P (kN)", "Piles", "Cap (m)", "Cap wt (kN)", "Load/pile (kN)", "Qa (kN)", "Util.",
             "Tip (m bgl)", "s (mm)"]
T(c, size=7.5, fmt="{:.1f}")

doc.save(DOCX)
print("Saved", DOCX)
