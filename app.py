"""CE 402 Shallow Foundation Platform - Streamlit interface.

All calculations live in the `geotech` package (each equation carries its source).
This file only collects inputs, calls the package and displays results with units.
Nothing about any particular site is hard-coded: example profiles are JSON files in
`examples/` and any profile can be typed in or uploaded.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from geotech import CM2S_TO_M2YR, KGCM2_TO_KPA
from geotech import bearing as bc
from geotech import lab
from geotech import liquefaction as liq
from geotech import settlement as se
from geotech import spt as sptmod
from geotech import stress as stz
from geotech.profile import COHESIVE, GRANULAR, HISTORY_MODES, Layer, SoilProfile, SPTRecord

ROOT = Path(__file__).parent
EXAMPLES = ROOT / "examples"

st.set_page_config(page_title="CE 402 Shallow Foundation Platform", page_icon="🏗️", layout="wide")

# ----------------------------------------------------------------- columns
LAYER_COLS = [
    ("top", "Top (m)"), ("bottom", "Bottom (m)"), ("description", "Description"),
    ("soil_type", "Type"), ("gamma_moist", "γ moist (kN/m³)"), ("gamma_sat", "γ sat (kN/m³)"),
    ("c_eff", "c′ (kPa)"), ("phi_eff", "φ′ (°)"), ("undrained", "Undrained (φ=0, use cu)"),
    ("cu", "cu (kPa)"), ("E", "E (kPa)"), ("Cc", "Cc (–)"), ("Cs", "Cs (–)"), ("e0", "e0 (–)"),
    ("history", "Stress history"), ("history_value", "OCR (–) / POP (kPa) / σ′p (kPa)"),
    ("cv", "cv (m²/yr)"), ("drainage", "Drainage"), ("dilatancy", "Fine/silty sand (dilatancy)"),
]
SPT_COLS = [("depth", "Depth (m)"), ("N", "N (blows/300 mm)"), ("refusal", "Refusal")]
DEFAULT_LAYER = dict(Layer(0, 1).__dict__)


def layers_to_df(layers: list[dict]) -> pd.DataFrame:
    rows = []
    for l in layers:
        full = {**DEFAULT_LAYER, **l}
        rows.append({lab_: full[k] for k, lab_ in LAYER_COLS})
    return pd.DataFrame(rows, columns=[c for _, c in LAYER_COLS])


def df_to_layers(df: pd.DataFrame) -> list[Layer]:
    out = []
    for _, r in df.iterrows():
        if pd.isna(r["Top (m)"]) or pd.isna(r["Bottom (m)"]):
            continue
        d = {}
        for k, c in LAYER_COLS:
            v = r[c]
            if isinstance(v, float) and math.isnan(v):
                v = DEFAULT_LAYER[k]
            if v is None:
                v = DEFAULT_LAYER[k]
            d[k] = v
        for k in ("top", "bottom", "gamma_moist", "gamma_sat", "c_eff", "phi_eff", "cu", "E", "Cc", "Cs",
                  "e0", "history_value", "cv"):
            d[k] = float(d[k])
        d["undrained"] = bool(d["undrained"])
        d["dilatancy"] = bool(d["dilatancy"])
        d["description"] = str(d["description"])
        out.append(Layer(**d))
    return out


def spt_to_df(spt: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{c: s.get(k, False if k == "refusal" else None) for k, c in SPT_COLS} for s in spt],
                        columns=[c for _, c in SPT_COLS])


def df_to_spt(df: pd.DataFrame) -> list[SPTRecord]:
    out = []
    for _, r in df.iterrows():
        if pd.isna(r["Depth (m)"]) or pd.isna(r["N (blows/300 mm)"]):
            continue
        out.append(SPTRecord(float(r["Depth (m)"]), float(r["N (blows/300 mm)"]), bool(r["Refusal"])))
    return out


def load_into_state(d: dict):
    st.session_state.data = d
    st.session_state.ver = st.session_state.get("ver", 0) + 1


def blank_project() -> dict:
    return {"name": "New profile", "gwt_measured": 3.0, "gwt_design": 2.0,
            "layers": [dict(top=0.0, bottom=3.0, description="Sand", soil_type=GRANULAR),
                       dict(top=3.0, bottom=10.0, description="Clay", soil_type=COHESIVE, gamma_moist=18.0,
                            gamma_sat=18.5, phi_eff=0.0, cu=30.0, undrained=True, Cc=0.3, Cs=0.04, e0=0.9)],
            "spt": [dict(depth=1.5, N=10, refusal=False)], "lab": {}, "fines": {}}


if "data" not in st.session_state:
    first = sorted(EXAMPLES.glob("*.json"))
    load_into_state(json.loads(first[0].read_text()) if first else blank_project())

ver = st.session_state.ver
D = st.session_state.data

# ================================================================= SIDEBAR
with st.sidebar:
    st.title("CE 402 Foundation Platform")
    st.caption("IS 6403:1981 · IS 2131:1981 · IS 1904:1986 · IS 1893 (Part 1):2016 — SI units")
    with st.expander("📂 Project file", expanded=False):
        ex_files = sorted(p.name for p in EXAMPLES.glob("*.json"))
        choice = st.selectbox("Example profile", ["—"] + ex_files, key="ex_choice")
        c1, c2 = st.columns(2)
        if c1.button("Load example", disabled=choice == "—", width="stretch"):
            load_into_state(json.loads((EXAMPLES / choice).read_text()))
            st.rerun()
        if c2.button("Blank profile", width="stretch"):
            load_into_state(blank_project())
            st.rerun()
        up = st.file_uploader("Upload project (.json)", type="json")
        if up is not None and st.button("Load uploaded file"):
            load_into_state(json.loads(up.read()))
            st.rerun()

    st.subheader("Footing")
    shape = st.selectbox("Shape", bc.SHAPES, index=1)
    B = st.number_input("Width B (m)" if shape != "Circle" else "Diameter D (m)", 0.3, 30.0, 2.0, 0.05)
    L = None
    if shape == "Rectangle":
        L = st.number_input("Length L (m)", 0.3, 60.0, max(3.0, B), 0.05)
    Df = st.number_input("Founding depth Df (m)", 0.0, 10.0, 1.5, 0.1)
    st.subheader("Loads (service, at founding level)")
    P = st.number_input("Vertical load P (kN" + ("/m)" if shape == "Strip" else ")"), 0.0, 1e6, 1000.0, 10.0)
    MB = st.number_input("Moment causing eccentricity along B, M_B (kN·m)", 0.0, 1e5, 0.0, 5.0)
    ML = 0.0
    if shape not in ("Strip",):
        ML = st.number_input("Moment causing eccentricity along L, M_L (kN·m)", 0.0, 1e5, 0.0, 5.0)
    alpha = st.number_input("Load inclination to vertical α (°)", 0.0, 45.0, 0.0, 1.0)
    st.subheader("Design options")
    FS = st.number_input("Factor of safety on q_nu (–)", 1.0, 10.0, 3.0, 0.5)
    mode_lbl = st.selectbox("Shear failure mode", ["Auto (interpolate φ 28°–36°)", "General", "Local"])
    mode = {"Auto (interpolate φ 28°–36°)": "auto", "General": "general", "Local": "local"}[mode_lbl]
    use_d = st.checkbox("Apply depth factors (compacted backfill)", True)
    g_fill = st.number_input("Unit weight of footing + backfill (kN/m³)", 0.0, 30.0, 20.0, 0.5)

# ================================================================== TABS
st.header(D.get("name", "Soil profile"))
tabs = st.tabs(["P1 Soil profile", "P2 Parameter tools", "P3 Bearing capacity", "P4 Stress increase",
                "P5 Settlement", "Extra: Liquefaction", "Sources & help"])

# ------------------------------------------------------------------ P1
with tabs[0]:
    c1, c2, c3 = st.columns([2, 1, 1])
    D["name"] = c1.text_input("Profile name", D.get("name", ""), key=f"name{ver}")
    gwt_m = c2.number_input("Measured water table (m bgl)", 0.0, 100.0, float(D.get("gwt_measured", 3.0)), 0.1,
                            key=f"gwm{ver}", help="Level at the time of SPT/boring – used for IS 2131 corrections")
    gwt_d = c3.number_input("Design water table (m bgl)", 0.0, 100.0, float(D.get("gwt_design", 2.0)), 0.1,
                            key=f"gwd{ver}", help="Level used for bearing capacity, settlement and liquefaction")
    st.markdown("**Layers** – add/delete rows freely. Units are given in every column heading.")
    ldf = st.data_editor(
        layers_to_df(D.get("layers", [])), num_rows="dynamic", key=f"layers{ver}", width="stretch",
        column_config={
            "Type": st.column_config.SelectboxColumn(options=list((GRANULAR, COHESIVE)), required=True),
            "Stress history": st.column_config.SelectboxColumn(options=list(HISTORY_MODES),
                                                               help="NC; OCR; POP (kPa); σ′p (kPa) constant"),
            "Drainage": st.column_config.SelectboxColumn(options=["Double", "Top only", "Bottom only"]),
            "Description": st.column_config.TextColumn(width="medium"),
        })
    st.markdown("**SPT records** (observed N; tick *Refusal* when 50 blows gave < 300 mm)")
    sdf = st.data_editor(spt_to_df(D.get("spt", [])), num_rows="dynamic", key=f"spt{ver}")

    layers = df_to_layers(ldf)
    profile = SoilProfile(layers=layers, gwt_measured=gwt_m, gwt_design=gwt_d, spt=df_to_spt(sdf),
                          name=D.get("name", ""))
    msgs = profile.validate()
    for m in msgs:
        st.warning(m)

    if layers:
        zmax = profile.depth
        zz = np.linspace(0, zmax, 301)
        fig = make_subplots(rows=1, cols=3, shared_yaxes=True, column_widths=[0.28, 0.42, 0.30],
                            subplot_titles=("Strata", "In-situ stresses (design WT)", "SPT N"))
        colors = {GRANULAR: "#e8c872", COHESIVE: "#7fa7d9"}
        for l in profile.sorted_layers():
            fig.add_shape(type="rect", x0=0, x1=1, y0=l.top, y1=l.bottom, row=1, col=1,
                          fillcolor=colors.get(l.soil_type, "#ccc"), line=dict(color="#555", width=1))
            fig.add_annotation(x=0.5, y=(l.top + l.bottom) / 2, text=l.description[:28], showarrow=False,
                               row=1, col=1, font=dict(size=10, color="#111"))
        for wt, nm, dash in [(gwt_m, "Measured WT", "solid"), (gwt_d, "Design WT", "dash")]:
            if wt <= zmax:
                for col in (1, 2):
                    fig.add_shape(type="line", x0=0, x1=1, xref=f"x{col if col > 1 else ''} domain",
                                  y0=wt, y1=wt, row=1, col=col, line=dict(color="#1f5fbf", dash=dash, width=2))
                fig.add_annotation(x=1.0, y=wt, text=f"▽ {nm} {wt:.2f} m", showarrow=False, xanchor="right",
                                   yanchor="bottom", row=1, col=1, font=dict(size=10, color="#1f5fbf"))
        S = np.array([profile.stresses(z, gwt_d) for z in zz])
        for i, (nm, col) in enumerate([("σv (kPa)", "#444"), ("u (kPa)", "#1f5fbf"), ("σ′v (kPa)", "#c0392b")]):
            fig.add_trace(go.Scatter(x=S[:, i], y=zz, name=nm, line=dict(color=col)), row=1, col=2)
        steps = sptmod.correct_profile_spt(profile)
        if steps:
            fig.add_trace(go.Scatter(x=[s.N for s in steps], y=[s.depth for s in steps], mode="markers+lines",
                                     name="N observed"), row=1, col=3)
            fig.add_trace(go.Scatter(x=[s.N2 for s in steps], y=[s.depth for s in steps], mode="markers",
                                     name="N corrected (IS 2131)", marker_symbol="diamond"), row=1, col=3)
        fig.update_yaxes(autorange="reversed", title_text="Depth below ground (m)", row=1, col=1)
        fig.update_xaxes(visible=False, range=[0, 1], row=1, col=1)
        fig.update_xaxes(title_text="Stress (kPa)", row=1, col=2)
        fig.update_xaxes(title_text="N (blows/300 mm)", row=1, col=3)
        fig.update_layout(height=620, margin=dict(t=40, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.08))
        st.plotly_chart(fig, width="stretch")

    st.download_button("💾 Download project (.json)",
                       json.dumps({**D, **profile.to_dict()}, indent=2), file_name="profile.json",
                       mime="application/json")

# ------------------------------------------------------------------ P2
with tabs[1]:
    st.subheader("SPT N corrections – IS 2131:1981")
    st.caption("Step 1 overburden: N′ = C_N·N, C_N = 0.77 log₁₀(20/p′), p′ in kg/cm² (IS 2131 Fig. 1). "
               "Step 2 dilatancy (saturated fine/silty sand, N′ > 15): N″ = 15 + 0.5(N′ − 15). "
               "Uses the **measured** water table.")
    c1, c2, c3 = st.columns(3)
    cn_max = c1.number_input("Upper limit on C_N (–)", 1.0, 3.0, 2.0, 0.1)
    qcn = c2.number_input("qc/N for E estimate (MPa per blow)", 0.1, 1.5, 0.4, 0.05)
    LB_for_E = (L / B) if (shape == "Rectangle" and L) else (10.0 if shape == "Strip" else 1.0)
    c3.metric("L/B used for E = (2.5…3.5)·qc", f"{LB_for_E:.2f}")
    steps = sptmod.correct_profile_spt(profile, cn_max)
    if steps:
        rows = []
        for s in steps:
            qc, E = sptmod.e_from_n(s.N2, qcn, LB_for_E)
            rows.append({"Depth (m)": s.depth, "Layer": s.layer, "N (obs.)": s.N,
                         "σ′v (kPa)": s.sigma_eff_kpa, "p′ (kg/cm²)": s.sigma_eff_kgcm2,
                         "C_N (–)": s.CN, "N′ = C_N·N": s.N1, "Below meas. WT": s.below_wt,
                         "Dilatancy applied": s.dilatancy_applies, "N″ (corrected)": s.N2,
                         "φ′ from N″ (°) [Wolff 1989]": sptmod.phi_from_n(s.N2) if s.soil_type == GRANULAR else None,
                         "qc (kPa)": qc if s.soil_type == GRANULAR else None,
                         "E (kPa)": E if s.soil_type == GRANULAR else None, "Note": s.note})
        st.dataframe(pd.DataFrame(rows).round(3), width="stretch", hide_index=True)
    else:
        st.info("No SPT records in the profile.")

    labd = D.get("lab", {})
    st.subheader("Direct shear – least-squares fit of c′ and φ′")
    st.caption("τf = c′ + σn·tan φ′ fitted by ordinary least squares (normal equations).")
    ds_sets = labd.get("direct_shear", [{"label": "Test 1", "sigma_n": [50, 100, 150], "tau": [None, None, None]}])
    names = [d["label"] for d in ds_sets]
    pick = st.selectbox("Data set", names, key=f"dspick{ver}")
    dset = ds_sets[names.index(pick)]
    dsdf = st.data_editor(pd.DataFrame({"σn (kPa)": dset["sigma_n"], "τf (kPa)": dset["tau"]}),
                          num_rows="dynamic", key=f"ds{ver}{pick}")
    force0 = st.checkbox("Force c′ = 0", False)
    dd = dsdf.dropna()
    if len(dd) >= 2:
        f = lab.fit_mohr_coulomb(dd["σn (kPa)"], dd["τf (kPa)"], force0)
        m1, m2, m3 = st.columns(3)
        m1.metric("c′ (kPa)", f"{f.c:.2f}")
        m2.metric("φ′ (°)", f"{f.phi:.2f}")
        m3.metric("R² (–)", f"{f.r2:.4f}")
        xs = np.linspace(0, max(dd["σn (kPa)"]) * 1.1, 50)
        fg = go.Figure([go.Scatter(x=dd["σn (kPa)"], y=dd["τf (kPa)"], mode="markers", name="test"),
                        go.Scatter(x=xs, y=f.c + f.tan_phi * xs, name="fit")])
        fg.update_layout(height=320, xaxis_title="σn (kPa)", yaxis_title="τf (kPa)", margin=dict(t=10))
        st.plotly_chart(fg, width="stretch")
        if f.c > 3 and "unsoak" in pick.lower():
            st.warning("Cohesion intercept in unsoaked sand is apparent (suction) – do not rely on it in design.")

    st.subheader("Unconsolidated undrained triaxial – cu")
    uu = labd.get("uu", [{"label": "Sample", "deviator": [None, None, None]}])
    for k, s in enumerate(uu):
        udf = st.data_editor(pd.DataFrame({"σ3 (kPa)": s.get("sigma3", [None] * len(s["deviator"])),
                                           "(σ1−σ3)f (kPa)": s["deviator"]}), key=f"uu{ver}{k}",
                             num_rows="dynamic")
        dv = udf["(σ1−σ3)f (kPa)"].dropna()
        if len(dv):
            cu, _ = lab.cu_from_uu(dv)
            st.write(f"**{s['label']}**: cu = (σ1−σ3)f / 2 = **{cu:.2f} kPa** (mean of {len(dv)} specimens)")

    st.subheader("One-dimensional consolidation – Cc, Cs, σ′p (Casagrande), cv")
    oed = labd.get("oedometer", {"p": [], "e": [], "stage": [], "cv": []})
    u1, u2 = st.columns(2)
    p_unit = u1.selectbox("Pressure unit in the lab sheet", ["kg/cm2", "kPa"], key=f"pu{ver}")
    cv_unit = u2.selectbox("cv unit in the lab sheet", ["cm2/s", "m2/yr"], key=f"cvu{ver}")
    odf = st.data_editor(pd.DataFrame({"Pressure": oed.get("p", []), "Stage": oed.get("stage", []),
                                       "Void ratio e (–)": oed.get("e", []), "cv": oed.get("cv", [])}),
                         num_rows="dynamic", key=f"oed{ver}",
                         column_config={"Stage": st.column_config.SelectboxColumn(options=["Loading", "Unloading"])})
    nv = st.number_input("Points on the virgin line (last loading points)", 2, 5, 2)
    od = odf.dropna(subset=["Pressure", "Void ratio e (–)", "Stage"])
    if (od["Stage"] == "Loading").sum() >= 3:
        try:
            r = lab.analyse_oedometer(od["Pressure"], od["Void ratio e (–)"], od["Stage"], p_unit,
                                      [None if pd.isna(v) else float(v) for v in od["cv"]], cv_unit, nv)
            m1, m2, m3 = st.columns(3)
            m1.metric("Cc (–)", f"{r.Cc:.3f}")
            m2.metric("Cs (–)", f"{r.Cs:.4f}")
            m3.metric("σ′p Casagrande (kPa)", f"{r.sigma_p:.1f}")
            st.caption(f"Pressures converted to kPa (1 kg/cm² = {KGCM2_TO_KPA} kPa); cv converted to m²/yr "
                       f"(1 cm²/s = {CM2S_TO_M2YR:.2f} m²/yr).")
            tab = pd.DataFrame({"p (kPa)": r.p_kpa, "Stage": r.stage, "e (–)": r.e,
                                "cv (m²/yr)": r.cv_m2yr if r.cv_m2yr else None})
            st.dataframe(tab.round(3), hide_index=True)
            c = r.construction
            fg = go.Figure()
            fg.add_trace(go.Scatter(x=r.p_kpa, y=r.e, mode="markers+lines", name="test"))
            xx = np.linspace(c["xm"] - 0.6, c["xm"] + 0.8, 20)
            fg.add_trace(go.Scatter(x=10 ** xx, y=c["em"] + c["tangent_slope"] * (xx - c["xm"]), name="tangent",
                                    line=dict(dash="dot")))
            fg.add_trace(go.Scatter(x=10 ** xx, y=[c["em"]] * len(xx), name="horizontal", line=dict(dash="dot")))
            fg.add_trace(go.Scatter(x=10 ** xx, y=c["em"] + c["bisector_slope"] * (xx - c["xm"]), name="bisector",
                                    line=dict(dash="dash")))
            xv = np.linspace(c["xp"] - 0.3, np.log10(max(r.p_kpa)), 20)
            fg.add_trace(go.Scatter(x=10 ** xv, y=c["virgin_intercept"] + c["virgin_slope"] * xv, name="virgin line"))
            fg.add_trace(go.Scatter(x=[r.sigma_p], y=[c["ep"]], mode="markers", marker=dict(size=12, symbol="x"),
                                    name="σ′p"))
            fg.update_xaxes(type="log", title="p (kPa)")
            fg.update_layout(height=380, yaxis_title="e (–)", margin=dict(t=10))
            st.plotly_chart(fg, width="stretch")
        except Exception as ex:  # noqa: BLE001
            st.error(f"Oedometer analysis failed: {ex}")
    with st.expander("Correlations (when no consolidation test exists)"):
        LL = st.number_input("Liquid limit LL (%)", 0.0, 200.0, 45.0)
        w = st.number_input("Natural water content w (%)", 0.0, 200.0, 35.0)
        Gs = st.number_input("Specific gravity Gs (–)", 2.0, 3.0, 2.70)
        st.write(f"Cc = 0.009(LL − 10) = **{lab.cc_terzaghi_peck(LL):.3f}** (Terzaghi & Peck 1967, undisturbed); "
                 f"Cc = 0.007(LL − 10) = {lab.cc_skempton(LL):.3f} (Skempton 1944, remoulded); "
                 f"e0 = w·Gs (S = 1) = **{lab.e0_saturated(w / 100, Gs):.3f}**")

# ------------------------------------------------------------------ P3
with tabs[2]:
    st.subheader("Bearing capacity – IS 6403:1981")
    if not layers:
        st.error("Enter at least one layer in P1.")
        st.stop()
    try:
        R = bc.bearing_capacity(profile, shape, B, L, Df, P=P, MB=MB, ML=ML, alpha_deg=alpha, FS=FS, mode=mode,
                                use_depth_factors=use_d, gamma_fill=g_fill)
    except ValueError as ex:
        st.error(f"{ex} – P4/P5 use the net pressure entered on their own tabs.")
        R = None
if R is not None:
    with tabs[2]:
        for w_ in R.warnings:
            st.warning(w_)
        st.markdown(f"Founding layer: **{R.layer}** · {'undrained, φ = 0' if R.undrained else 'drained'} · "
                    f"design WT = {gwt_d:.2f} m bgl")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("c used (kPa)", f"{R.c:.2f}")
        c2.metric("φ used (°)", f"{R.phi:.2f}")
        c3.metric("q = σ′v at Df (kPa)", f"{R.q:.2f}")
        c4.metric("γ below base (kN/m³)", f"{R.gamma:.2f}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("e_B = M_B/P (m)", f"{R.eB:.3f}")
        c2.metric("e_L = M_L/P (m)", f"{R.eL:.3f}")
        c3.metric("B′ × L′ (m)", f"{R.B_eff:.3f} × {R.L_eff:.3f}" if shape != "Strip" else f"{R.B_eff:.3f}")
        c4.metric("A′ (m²)", f"{R.A_eff:.3f}")
        fac = pd.DataFrame({
            "Factor": ["Shape s", "Depth d", "Inclination i"],
            "c-term": [R.sc, R.dc, R.ic], "q-term": [R.sq, R.dq, R.iq], "γ-term": [R.sg, R.dg, R.ig]})
        st.markdown(f"**Shape / depth / inclination factors** (IS 6403 Table 2, cl. 5.1.2.2, 5.1.2.3) · "
                    f"**Water-table factor W′ = {R.W:.3f}** (cl. 5.1.2.4)")
        st.dataframe(fac.round(4), hide_index=True)
        rows = []
        for t in (R.general, R.local):
            rows.append({"Mode": t.mode, "c or c_m (kPa)": t.c, "φ or φ_m (°)": t.phi, "Nc": t.Nc, "Nq": t.Nq,
                         "Nγ": t.Ng, "c·Nc·s·d·i (kPa)": t.term_c, "q(Nq−1)·s·d·i (kPa)": t.term_q,
                         "½Bγ·Nγ·s·d·i·W′ (kPa)": t.term_g, "q_nu (kPa)": t.q_nu})
        st.markdown("**Bearing capacity factors and terms** (IS 6403 Table 1; local shear: c_m = ⅔c, "
                    "tan φ_m = 0.67 tan φ)")
        st.dataframe(pd.DataFrame(rows).round(3), hide_index=True)
        c1, c2, c3 = st.columns(3)
        c1.metric(f"q_nu (kPa) – {R.mode_used}", f"{R.q_nu:.1f}")
        c2.metric(f"q_ns = q_nu/{FS:g} (kPa)", f"{R.q_ns:.1f}")
        c3.metric("Gross safe = q_ns + q (kPa)", f"{R.q_safe_gross:.1f}")
        if R.q_net_applied is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric("Gross applied (P + W_f)/A′ (kPa)", f"{R.q_gross_applied:.1f}")
            c2.metric("Net applied (kPa)", f"{R.q_net_applied:.1f}")
            c3.metric("Check q_net ≤ q_ns", "OK ✅" if R.ok else "NOT OK ❌")
            st.caption("Net applied = (P + W_footing+backfill − σv,total(Df)·A)/A′ — compared with the NET safe capacity.")
        wl = bc.weak_layer_check(profile, R.B_eff, R.L_eff if shape != "Strip" else 100.0, Df,
                                 R.q_net_applied or R.q_ns, FS)
        if wl:
            st.markdown(f"**Underlying soft layer check (2:1 projected area)** – {wl.layer} at {wl.z_top:.2f} m below "
                        f"base: Δσ = {wl.delta_sigma:.1f} kPa, q_nu = {wl.q_nu_weak:.1f} kPa, FS = {wl.FS:.2f} "
                        f"{'✅' if wl.ok else '❌'}")
        st.divider()
        st.markdown("**Find the minimum size** that satisfies q_net ≤ q_ns")
        c1, c2 = st.columns(2)
        lb_ratio = c1.number_input("L/B for rectangle (–)", 1.0, 10.0, 1.5, 0.1) if shape == "Rectangle" else 1.0
        stepB = c2.number_input("Size increment (m)", 0.01, 0.5, 0.05, 0.01)
        if st.button("Size footing"):
            Rs = bc.size_footing(profile, shape, P, Df, lb_ratio, MB, ML, FS, mode, step=stepB,
                                 use_depth_factors=use_d, gamma_fill=g_fill, alpha_deg=alpha)
            st.success(f"B = {Rs.B:.2f} m" + (f", L = {Rs.L:.2f} m" if shape == "Rectangle" else "") +
                       f" → q_net = {Rs.q_net_applied:.1f} kPa ≤ q_ns = {Rs.q_ns:.1f} kPa")

# ------------------------------------------------------------------ P4
with tabs[3]:
    st.subheader("Vertical stress increase Δσz below the footing")
    q_def = float(R.q_net_applied) if (R is not None and R.q_net_applied) else 100.0
    c1, c2, c3 = st.columns(3)
    q4 = c1.number_input("Net pressure q (kPa)", 0.0, 5000.0, round(max(q_def, 0.0), 2), 1.0,
                         help="Defaults to the net applied pressure from P3")
    zmax4 = c2.number_input("Depth below base (m)", 0.5, 60.0, max(4 * B, 5.0), 0.5)
    dz4 = c3.number_input("Step (m)", 0.05, 2.0, 0.25, 0.05)
    Lr = L if shape == "Rectangle" else B
    zs = np.arange(dz4, zmax4 + 1e-9, dz4)
    tbl = pd.DataFrame(stz.profile_table(q4, shape, B, Lr, zs))
    tbl.columns = ["z below base (m)", "Boussinesq centre (kPa)", "Boussinesq corner (kPa)", "2:1 (kPa)"]
    fg = go.Figure()
    for col in tbl.columns[1:]:
        fg.add_trace(go.Scatter(x=tbl[col], y=tbl["z below base (m)"], name=col))
    fg.update_yaxes(autorange="reversed", title="z below base (m)")
    fg.update_layout(height=500, xaxis_title="Δσz (kPa)", margin=dict(t=10))
    st.plotly_chart(fg, width="stretch")
    st.dataframe(tbl.round(3), hide_index=True, height=280)
    st.caption("Corner: Newmark (1935) integration of Boussinesq; centre = 4 × corner of (B/2 × L/2) by "
               "superposition; 2:1: q·B·L/((B+z)(L+z)). Circle: closed-form centre solution.")
    with st.expander("Stress at any point (superposition)"):
        c1, c2, c3 = st.columns(3)
        xp_ = c1.number_input("x from centre along B (m)", -50.0, 50.0, 0.0)
        yp_ = c2.number_input("y from centre along L (m)", -50.0, 50.0, 0.0)
        zp_ = c3.number_input("z below base (m)", 0.01, 60.0, 2.0)
        if shape in ("Square", "Rectangle"):
            st.write(f"Δσz = **{stz.rect_point(q4, B, Lr, xp_, yp_, zp_):.2f} kPa**")
        else:
            st.info("Available for square and rectangular footings.")

# ------------------------------------------------------------------ P5
with tabs[4]:
    st.subheader("Settlement")
    q5 = st.number_input("Net applied pressure q_net (kPa)", 0.0, 5000.0, round(max(q_def, 0.0), 2), 1.0,
                         key="q5", help="Defaults to the net applied pressure from P3")
    st.markdown("#### Granular layers – strain influence factor method (Schmertmann et al. 1978)")
    c1, c2 = st.columns(2)
    t_s = c1.number_input("Time for creep factor C2 (years)", 0.1, 100.0, 0.1, 0.1)
    dz5 = c2.number_input("Sublayer thickness for integration (m)", 0.01, 0.5, 0.1, 0.01)
    SR = se.schmertmann(profile, shape, B, L, Df, q5, t_s, dz5)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("C1 (–)", f"{SR.C1:.3f}")
    c2.metric("C2 (–)", f"{SR.C2:.3f}")
    c3.metric("Izp (–)", f"{SR.Izp:.3f}")
    c4.metric("zp / z_max (m)", f"{SR.zp:.2f} / {SR.z_infl:.2f}")
    c5.metric("Settlement (mm)", f"{SR.settlement * 1000:.1f}")
    if SR.skipped_cohesive > 0:
        st.info(f"{SR.skipped_cohesive:.2f} m of cohesive soil inside the influence zone is handled by "
                "consolidation below, not by Schmertmann.")
    if SR.rows:
        sdf_ = pd.DataFrame(SR.rows)
        sdf_["ds"] = sdf_["ds"] * 1000
        sdf_.columns = ["z below base (m)", "Depth (m bgl)", "Layer", "Iz (–)", "E (kPa)", "Δs (mm)", "Note"]
        fgI = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("Iz", "E (kPa)"))
        fgI.add_trace(go.Scatter(x=sdf_["Iz (–)"], y=sdf_["z below base (m)"], name="Iz"), 1, 1)
        fgI.add_trace(go.Scatter(x=sdf_["E (kPa)"], y=sdf_["z below base (m)"], name="E", line_shape="hv"), 1, 2)
        fgI.update_yaxes(autorange="reversed", title_text="z below base (m)", row=1, col=1)
        fgI.update_layout(height=330, margin=dict(t=30), showlegend=False)
        st.plotly_chart(fgI, width="stretch")
        with st.expander("Sublayer table"):
            st.dataframe(sdf_.round(4), hide_index=True)

    st.markdown("#### Cohesive layers – one-dimensional consolidation (sublayers ≤ 0.5 m)")
    c1, c2 = st.columns(2)
    smeth = c1.selectbox("Stress increase method", ["Boussinesq centre", "Boussinesq corner", "2:1"])
    hsub = c2.number_input("Maximum sublayer thickness (m)", 0.05, 0.5, 0.5, 0.05)
    CR = se.consolidation(profile, se.footing_stress_fn(smeth, q5, shape, B, L, Df), Df, hsub)
    if CR.rows:
        cdf = pd.DataFrame([r.__dict__ for r in CR.rows])
        cdf["s"] = cdf["s"] * 1000
        cdf = cdf[["layer", "top", "bottom", "H", "z_mid", "sigma0", "sigma_p", "d_sigma", "sigma_f", "case",
                   "Cc", "Cs", "e0", "s"]]
        cdf.columns = ["Layer", "Top (m)", "Bottom (m)", "H (m)", "z mid (m)", "σ′0 (kPa)", "σ′p (kPa)",
                       "Δσ (kPa)", "σ′0+Δσ (kPa)", "Case", "Cc", "Cs", "e0", "s (mm)"]
        st.dataframe(cdf.round(3), hide_index=True, height=300)
        for k, v in CR.per_layer.items():
            st.write(f"{k}: **{v * 1000:.1f} mm**")
    else:
        st.info("No cohesive layer with Cc > 0 below the base.")

    st.markdown("#### Time – settlement (Terzaghi 1-D consolidation)")
    lay_sc = []
    if CR.rows:
        for lay in CR.layers:
            key = f"{lay.description} ({lay.top:g}-{lay.bottom:g} m)"
            H = lay.bottom - max(lay.top, Df)
            c1, c2, c3 = st.columns(3)
            c1.write(f"**{lay.description}** H = {H:.2f} m, Sc = {CR.per_layer[key] * 1000:.1f} mm")
            cvv = c2.number_input("cv (m²/yr)", 0.001, 1000.0, float(lay.cv), key=f"cv_{key}")
            drn = c3.selectbox("Drainage", ["Double", "Top only", "Bottom only"],
                               index=["Double", "Top only", "Bottom only"].index(lay.drainage)
                               if lay.drainage in ("Double", "Top only", "Bottom only") else 0, key=f"dr_{key}")
            lay_sc.append((CR.per_layer[key], H, cvv, "Double" if drn == "Double" else "Single"))
        tmax = st.number_input("Plot up to (years)", 0.1, 200.0, 20.0, 1.0)
        tt = np.linspace(0, tmax, 400)
        tot, parts = se.time_settlement(lay_sc, tt)
        fgt = go.Figure()
        fgt.add_trace(go.Scatter(x=tt, y=(tot + SR.settlement) * 1000, name="Total (immediate + consolidation)"))
        fgt.add_trace(go.Scatter(x=tt, y=tot * 1000, name="Consolidation", line=dict(dash="dash")))
        fgt.update_yaxes(autorange="reversed", title="Settlement (mm)")
        fgt.update_layout(height=380, xaxis_title="Time (years)", margin=dict(t=10))
        st.plotly_chart(fgt, width="stretch")
        rows = []
        for (Sc, H, cvv, drn), lay in zip(lay_sc, CR.layers):
            rows.append({"Layer": lay.description, "Hdr (m)": se.drainage_path(H, drn),
                         "t50 (yr)": se.time_for_U(0.5, H, cvv, drn), "t90 (yr)": se.time_for_U(0.9, H, cvv, drn)})
        st.dataframe(pd.DataFrame(rows).round(3), hide_index=True)

    st.markdown("#### Summary")
    total = SR.settlement + CR.total
    c1, c2, c3 = st.columns(3)
    c1.metric("Granular (Schmertmann) (mm)", f"{SR.settlement * 1000:.1f}")
    c2.metric("Consolidation (mm)", f"{CR.total * 1000:.1f}")
    c3.metric("Total (mm)", f"{total * 1000:.1f}")
    lim = st.number_input("Permissible total settlement (mm) – enter the IS 1904 value you adopt", 0.0, 500.0,
                          75.0, 5.0)
    st.write("Check:", "OK ✅" if total * 1000 <= lim else "Exceeds limit ❌")

# ------------------------------------------------------------- Liquefaction
with tabs[5]:
    st.subheader("Liquefaction triggering – IS 1893 (Part 1):2016 Annex F (simplified procedure)")
    st.caption("Not part of the P1–P5 brief: added because shallow saturated sands in high seismic zones must be "
               "screened. CSR = 0.65 (a_max/g)(σv/σ′v) r_d; CRR from (N1)60cs (Youd et al. 2001); FS = CRR·MSF/CSR.")
    c1, c2, c3, c4 = st.columns(4)
    amax = c1.number_input("a_max / g (–)", 0.01, 1.0, 0.36, 0.01, help="e.g. zone factor Z (IS 1893 Table 3)")
    Mw = c2.number_input("Moment magnitude Mw (–)", 5.0, 9.0, 7.5, 0.1)
    ER = c3.number_input("Hammer energy ratio (%)", 30.0, 100.0, 60.0, 5.0)
    dbh = c4.number_input("Borehole diameter (mm)", 60.0, 250.0, 150.0, 5.0)
    gl = [l.description for l in profile.sorted_layers() if l.soil_type == GRANULAR]
    fines0 = D.get("fines", {})
    fdf = st.data_editor(pd.DataFrame({"Layer": gl, "Fines content FC (%)": [fines0.get(g_, 0.0) for g_ in gl]}),
                         key=f"fines{ver}", disabled=["Layer"], hide_index=True)
    fines = dict(zip(fdf["Layer"], fdf["Fines content FC (%)"]))
    LR = liq.liquefaction(profile, amax, Mw, energy_ratio=ER, borehole_mm=dbh, fines=fines)
    if LR:
        ldf_ = pd.DataFrame([r.__dict__ for r in LR])
        ldf_.columns = ["Depth (m)", "N", "Layer", "FC (%)", "σv (kPa)", "σ′v (kPa)", "r_d", "CSR", "C_N", "C_R",
                        "(N1)60", "α", "β", "(N1)60cs", "CRR7.5", "MSF", "FS_L", "Status"]
        st.dataframe(ldf_.round(3), hide_index=True, width="stretch")
        fin = ldf_[np.isfinite(ldf_["FS_L"])]
        if len(fin):
            fg = go.Figure(go.Scatter(x=fin["FS_L"], y=fin["Depth (m)"], mode="markers+lines", name="FS_L"))
            fg.add_vline(x=1.0, line_dash="dash")
            fg.update_yaxes(autorange="reversed", title="Depth (m)")
            fg.update_layout(height=320, xaxis_title="FS against liquefaction (–)", margin=dict(t=10))
            st.plotly_chart(fg, width="stretch")
    else:
        st.info("No SPT records.")

# ----------------------------------------------------------------- Sources
with tabs[6]:
    src = ROOT / "SOURCES.md"
    st.markdown(src.read_text(encoding="utf-8") if src.exists() else "See README.md")
