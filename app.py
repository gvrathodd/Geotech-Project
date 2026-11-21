"""CE 402 Shallow Foundation Platform ("Foundation Studio") - Streamlit interface.

All calculations live in the `geotech` package (each equation carries its source).
This file only collects inputs, calls the package and displays results with units.
Nothing about any particular site is hard-coded: example profiles are JSON files in
`examples/` and any profile can be typed in or uploaded.  Visual theme: `ui/theme.py`.
"""
from __future__ import annotations

import html
import json
import math
import re
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
from ui import theme as ui

ROOT = Path(__file__).parent
EXAMPLES = ROOT / "examples"

st.set_page_config(page_title="Foundation Studio · CE 402", page_icon=":material/foundation:", layout="wide")
ui.inject()


def chart(fig, height=None):
    """Render a Plotly figure with the glass template (Streamlit's own theme off)."""
    if height:
        fig.update_layout(height=height)
    fig.update_layout(margin=dict(t=40, l=10, r=10, b=10))
    st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False})


def csv_button(df: pd.DataFrame, name: str):
    """'Export CSV' under a table.  UTF-8 with BOM so Excel shows σ′, φ′, ° and ³ correctly;
    the file name carries the profile name so exports from different boreholes don't collide."""
    prof = re.sub(r"[^a-z0-9]+", "-", str(st.session_state.data.get("name", "profile")).lower()).strip("-")[:24]
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    st.download_button("Export CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{prof or 'profile'}_{slug}.csv", mime="text/csv",
                       icon=":material/table_view:", key=f"csv_{slug}")


def show_df(df: pd.DataFrame, csv: str, **kw):
    """st.dataframe followed by its Export CSV button."""
    st.dataframe(df, **kw)
    csv_button(df, csv)


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
            if v is None or (isinstance(v, float) and math.isnan(v)):
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
    ui.brand()
    with st.expander("Project file", icon=":material/folder_open:", expanded=False):
        ex_files = sorted(p.name for p in EXAMPLES.glob("*.json"))
        choice = st.selectbox("Example profile", ["—"] + ex_files, key="ex_choice")
        c1, c2 = st.columns(2)
        if c1.button("Load Example", disabled=choice == "—", width="stretch"):
            load_into_state(json.loads((EXAMPLES / choice).read_text()))
            st.rerun()
        if c2.button("Blank Profile", width="stretch"):
            load_into_state(blank_project())
            st.rerun()
        up = st.file_uploader("Upload project (.json)", type="json")
        if up is not None and st.button("Load Uploaded File", width="stretch"):
            load_into_state(json.loads(up.read()))
            st.rerun()

    st.markdown("### Footing")
    shape = st.selectbox("Shape", bc.SHAPES, index=1)
    B = st.number_input("Width B (m)" if shape != "Circle" else "Diameter D (m)", 0.3, 30.0, 2.0, 0.05)
    L = None
    if shape == "Rectangle":
        L = st.number_input("Length L (m)", 0.3, 60.0, max(3.0, B), 0.05)
    Df = st.number_input("Founding depth Df (m)", 0.0, 10.0, 1.5, 0.1)
    st.markdown("### Loads · service, at founding level")
    P = st.number_input("Vertical load P (kN" + ("/m)" if shape == "Strip" else ")"), 0.0, 1e6, 1000.0, 10.0)
    MB = st.number_input("Moment along B, M_B (kN·m)", 0.0, 1e5, 0.0, 5.0,
                         help="Moment causing eccentricity in the B direction")
    ML = 0.0
    if shape != "Strip":
        ML = st.number_input("Moment along L, M_L (kN·m)", 0.0, 1e5, 0.0, 5.0,
                             help="Moment causing eccentricity in the L direction")
    alpha = st.number_input("Load inclination α (°)", 0.0, 45.0, 0.0, 1.0, help="Inclination of the load to the vertical")
    st.markdown("### Design options")
    FS = st.number_input("Factor of safety on q_nu (–)", 1.0, 10.0, 3.0, 0.5)
    mode_lbl = st.selectbox("Shear failure mode", ["Auto (interpolate φ 28°–36°)", "General", "Local"])
    mode = {"Auto (interpolate φ 28°–36°)": "auto", "General": "general", "Local": "local"}[mode_lbl]
    use_d = st.checkbox("Apply depth factors (compacted backfill)", True)
    g_fill = st.number_input("Footing + backfill unit weight (kN/m³)", 0.0, 30.0, 20.0, 0.5)

# ================================================================== HERO
ui.hero("Foundation", "Studio",
        f"Shallow-foundation design for <b>any layered profile</b>, step by step, to Indian Standards. "
        f"Current profile: <b>{html.escape(str(D.get('name', 'Soil profile')))}</b>.",
        ["IS 6403:1981", "IS 2131:1981", "IS 1904:1986", "IS 1893-1:2016", "SI units"],
        "CE 402 Geotechnical Engineering · IIT Mandi")
summary = st.container()

tabs = st.tabs(["P1 · Soil profile", "P2 · Parameters", "P3 · Bearing", "P4 · Stress", "P5 · Settlement",
                "Liquefaction", "Sources"])

# ------------------------------------------------------------------ P1
with tabs[0]:
    with ui.card():
        ui.section("P1", "Soil profile & water tables",
                   "The measured level drives the IS 2131 corrections; the design level drives bearing, "
                   "settlement and liquefaction.", anchor="p1")
        c1, c2, c3 = st.columns([2, 1, 1])
        D["name"] = c1.text_input("Profile name", D.get("name", ""), key=f"name{ver}")
        gwt_m = c2.number_input("Measured water table (m bgl)", 0.0, 100.0, float(D.get("gwt_measured", 3.0)), 0.1,
                                key=f"gwm{ver}", help="Level at the time of SPT/boring")
        gwt_d = c3.number_input("Design water table (m bgl)", 0.0, 100.0, float(D.get("gwt_design", 2.0)), 0.1,
                                key=f"gwd{ver}", help="e.g. highest seasonal level")
        st.markdown("**Layers**: add or delete rows freely. Units are given in every column heading.")
        ldf = st.data_editor(
            layers_to_df(D.get("layers", [])), num_rows="dynamic", key=f"layers{ver}", width="stretch",
            column_config={
                "Type": st.column_config.SelectboxColumn(options=list((GRANULAR, COHESIVE)), required=True),
                "Stress history": st.column_config.SelectboxColumn(options=list(HISTORY_MODES),
                                                                   help="NC; OCR; POP (kPa); σ′p (kPa) constant"),
                "Drainage": st.column_config.SelectboxColumn(options=["Double", "Top only", "Bottom only"]),
                "Description": st.column_config.TextColumn(width="medium"),
            })
        csv_button(ldf, "layers")
        st.markdown("**SPT records**: observed N. Tick *Refusal* when 50 blows gave less than 300 mm.")
        sdf = st.data_editor(spt_to_df(D.get("spt", [])), num_rows="dynamic", key=f"spt{ver}")
        csv_button(sdf, "spt_records")

    layers = df_to_layers(ldf)
    profile = SoilProfile(layers=layers, gwt_measured=gwt_m, gwt_design=gwt_d, spt=df_to_spt(sdf),
                          name=D.get("name", ""))
    for m in profile.validate():
        st.warning(m, icon=":material/warning:")

    if layers:
        with ui.card():
            ui.section("P1", "Profile drawing", "Strata, in-situ stresses at the design water table, and SPT N.")
            zmax = profile.depth
            zz = np.linspace(0, zmax, 301)
            fig = make_subplots(rows=1, cols=3, shared_yaxes=True, column_widths=[0.28, 0.42, 0.30],
                                subplot_titles=("Strata", "In-situ stresses (kPa)", "SPT N"))
            for l in profile.sorted_layers():
                fig.add_shape(type="rect", x0=0, x1=1, y0=l.top, y1=l.bottom, row=1, col=1,
                              fillcolor=ui.SOIL_COLORS.get(l.soil_type, "rgba(255,255,255,0.1)"),
                              line=dict(color="rgba(255,255,255,0.25)", width=1))
                fig.add_annotation(x=0.5, y=(l.top + l.bottom) / 2, text=l.description[:28], showarrow=False,
                                   row=1, col=1, font=dict(size=11, color=ui.TEXT))
            for wt, nm, dash in [(gwt_m, "Measured WT", "solid"), (gwt_d, "Design WT", "dash")]:
                if wt <= zmax:
                    for col in (1, 2):
                        fig.add_shape(type="line", x0=0, x1=1, xref=f"x{col if col > 1 else ''} domain",
                                      y0=wt, y1=wt, row=1, col=col, line=dict(color=ui.WATER, dash=dash, width=2))
                    fig.add_annotation(x=1.0, y=wt, text=f"▽ {nm} {wt:.2f} m", showarrow=False, xanchor="right",
                                       yanchor="bottom", row=1, col=1, font=dict(size=10, color=ui.WATER))
            S = np.array([profile.stresses(z, gwt_d) for z in zz])
            for i, (nm, col) in enumerate([("σv (kPa)", "#E5E7EB"), ("u (kPa)", ui.WATER), ("σ′v (kPa)", ui.GOLD)]):
                fig.add_trace(go.Scatter(x=S[:, i], y=zz, name=nm, line=dict(color=col, width=2.5)), row=1, col=2)
            steps = sptmod.correct_profile_spt(profile)
            if steps:
                fig.add_trace(go.Scatter(x=[s.N for s in steps], y=[s.depth for s in steps], mode="markers+lines",
                                         name="N observed", line=dict(color=ui.EMERALD)), row=1, col=3)
                fig.add_trace(go.Scatter(x=[s.N2 for s in steps], y=[s.depth for s in steps], mode="markers",
                                         name="N corrected (IS 2131)", marker=dict(symbol="diamond", size=9,
                                                                                    color=ui.GOLD)), row=1, col=3)
            fig.update_yaxes(autorange="reversed", title_text="Depth below ground (m)", row=1, col=1)
            fig.update_xaxes(visible=False, range=[0, 1], row=1, col=1)
            fig.update_xaxes(title_text="Stress (kPa)", row=1, col=2)
            fig.update_xaxes(title_text="N (blows/300 mm)", row=1, col=3)
            fig.update_layout(legend=dict(orientation="h", y=-0.08))
            chart(fig, 620)
            st.download_button("Download Project (.json)", json.dumps({**D, **profile.to_dict()}, indent=2),
                               file_name="profile.json", mime="application/json", icon=":material/download:")

# ------------------------------------------------------------------ P2
with tabs[1]:
    with ui.card():
        ui.section("P2·a", "SPT N corrections: IS 2131:1981",
                   "Step 1, overburden: N′ = C_N·N with C_N = 0.77 log₁₀(20/p′), p′ in kg/cm² (IS 2131 Fig. 1). "
                   "Step 2, dilatancy (saturated fine/silty sand with N′ > 15): N″ = 15 + 0.5(N′ − 15). "
                   "Both steps use the measured water table.")
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
                g = s.soil_type == GRANULAR
                rows.append({"Depth (m)": s.depth, "Layer": s.layer, "N (obs.)": s.N,
                             "σ′v (kPa)": s.sigma_eff_kpa, "p′ (kg/cm²)": s.sigma_eff_kgcm2,
                             "C_N (–)": s.CN, "N′ = C_N·N": s.N1, "Below meas. WT": s.below_wt,
                             "Dilatancy applied": s.dilatancy_applies, "N″ (corrected)": s.N2,
                             "φ′ from N″ (°) [Wolff 1989]": sptmod.phi_from_n(s.N2) if g else None,
                             "qc (kPa)": qc if g else None, "E (kPa)": E if g else None, "Note": s.note})
            show_df(pd.DataFrame(rows).round(3), "spt_corrections", width="stretch", hide_index=True)
        else:
            st.info("No SPT records in the profile yet. Add them in P1.", icon=":material/info:")

    labd = D.get("lab", {})
    with ui.card():
        ui.section("P2·b", "Direct shear: least-squares c′ and φ′",
                   "τf = c′ + σn·tan φ′, fitted by ordinary least squares (normal equations).")
        ds_sets = labd.get("direct_shear", [{"label": "Test 1", "sigma_n": [50, 100, 150], "tau": [None, None, None]}])
        names = [d["label"] for d in ds_sets]
        cL, cR = st.columns([1, 1.3])
        with cL:
            pick = st.selectbox("Data set", names, key=f"dspick{ver}")
            dset = ds_sets[names.index(pick)]
            dsdf = st.data_editor(pd.DataFrame({"σn (kPa)": dset["sigma_n"], "τf (kPa)": dset["tau"]}),
                                  num_rows="dynamic", key=f"ds{ver}{pick}", width="stretch")
            csv_button(dsdf, f"direct_shear_{pick}")
            force0 = st.checkbox("Force c′ = 0", False)
        dd = dsdf.dropna()
        if len(dd) >= 2:
            f = lab.fit_mohr_coulomb(dd["σn (kPa)"], dd["τf (kPa)"], force0)
            with cL:
                m1, m2, m3 = st.columns(3)
                m1.metric("c′ (kPa)", f"{f.c:.2f}")
                m2.metric("φ′ (°)", f"{f.phi:.2f}")
                m3.metric("R² (–)", f"{f.r2:.4f}")
                if f.c > 3 and "unsoak" in pick.lower():
                    st.warning("This cohesion intercept in unsoaked sand comes from suction. Do not rely on it "
                               "in design; use the soaked test instead.", icon=":material/warning:")
            with cR:
                xs = np.linspace(0, max(dd["σn (kPa)"]) * 1.1, 50)
                fg = go.Figure([go.Scatter(x=dd["σn (kPa)"], y=dd["τf (kPa)"], mode="markers", name="test",
                                           marker=dict(size=11, color=ui.GOLD)),
                                go.Scatter(x=xs, y=f.c + f.tan_phi * xs, name="fit", line=dict(color=ui.EMERALD, width=3))])
                fg.update_layout(xaxis_title="σn (kPa)", yaxis_title="τf (kPa)")
                chart(fg, 330)

    with ui.card():
        ui.section("P2·c", "Unconsolidated undrained triaxial: cu", "cu = (σ1 − σ3)f / 2 for each specimen.")
        uu = labd.get("uu", [{"label": "Sample", "deviator": [None, None, None]}])
        cols = st.columns(max(1, len(uu)))
        for k, s in enumerate(uu):
            with cols[k]:
                udf = st.data_editor(pd.DataFrame({"σ3 (kPa)": s.get("sigma3", [None] * len(s["deviator"])),
                                                   "(σ1−σ3)f (kPa)": s["deviator"]}), key=f"uu{ver}{k}",
                                     num_rows="dynamic", width="stretch")
                csv_button(udf, f"uu_{s['label']}")
                dv = udf["(σ1−σ3)f (kPa)"].dropna()
                if len(dv):
                    cu, _ = lab.cu_from_uu(dv)
                    st.metric(f"{s['label']} · cu (kPa)", f"{cu:.2f}")

    with ui.card():
        ui.section("P2·d", "One-dimensional consolidation: Cc, Cs, σ′p, cv",
                   "Lab-sheet units are converted explicitly: 1 kg/cm² = 98.07 kPa, 1 cm²/s = 3155.76 m²/yr.")
        oed = labd.get("oedometer", {"p": [], "e": [], "stage": [], "cv": []})
        u1, u2, u3 = st.columns(3)
        p_unit = u1.selectbox("Pressure unit in the lab sheet", ["kg/cm2", "kPa"], key=f"pu{ver}")
        cv_unit = u2.selectbox("cv unit in the lab sheet", ["cm2/s", "m2/yr"], key=f"cvu{ver}")
        nv = u3.number_input("Points on the virgin line (–)", 2, 5, 2)
        cL, cR = st.columns([1, 1.3])
        with cL:
            odf = st.data_editor(pd.DataFrame({"Pressure": oed.get("p", []), "Stage": oed.get("stage", []),
                                               "Void ratio e (–)": oed.get("e", []), "cv": oed.get("cv", [])}),
                                 num_rows="dynamic", key=f"oed{ver}", width="stretch",
                                 column_config={"Stage": st.column_config.SelectboxColumn(options=["Loading", "Unloading"])})
            csv_button(odf, "oedometer_input")
        od = odf.dropna(subset=["Pressure", "Void ratio e (–)", "Stage"])
        if (od["Stage"] == "Loading").sum() >= 3:
            try:
                r = lab.analyse_oedometer(od["Pressure"], od["Void ratio e (–)"], od["Stage"], p_unit,
                                          [None if pd.isna(v) else float(v) for v in od["cv"]], cv_unit, nv)
                with cL:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Cc (–)", f"{r.Cc:.3f}")
                    m2.metric("Cs (–)", f"{r.Cs:.4f}")
                    m3.metric("σ′p (kPa)", f"{r.sigma_p:.1f}")
                    tab = pd.DataFrame({"p (kPa)": r.p_kpa, "Stage": r.stage, "e (–)": r.e,
                                        "cv (m²/yr)": r.cv_m2yr if r.cv_m2yr else None})
                    show_df(tab.round(3), "oedometer_results", hide_index=True, width="stretch")
                with cR:
                    c = r.construction
                    fg = go.Figure()
                    fg.add_trace(go.Scatter(x=r.p_kpa, y=r.e, mode="markers+lines", name="test",
                                            line=dict(color=ui.EMERALD, width=3), marker=dict(size=8)))
                    xx = np.linspace(c["xm"] - 0.6, c["xm"] + 0.8, 20)
                    fg.add_trace(go.Scatter(x=10 ** xx, y=c["em"] + c["tangent_slope"] * (xx - c["xm"]), name="tangent",
                                            line=dict(dash="dot", color=ui.MUTED)))
                    fg.add_trace(go.Scatter(x=10 ** xx, y=[c["em"]] * len(xx), name="horizontal",
                                            line=dict(dash="dot", color=ui.MUTED)))
                    fg.add_trace(go.Scatter(x=10 ** xx, y=c["em"] + c["bisector_slope"] * (xx - c["xm"]),
                                            name="bisector", line=dict(dash="dash", color=ui.TEAL)))
                    xv = np.linspace(c["xp"] - 0.3, np.log10(max(r.p_kpa)), 20)
                    fg.add_trace(go.Scatter(x=10 ** xv, y=c["virgin_intercept"] + c["virgin_slope"] * xv,
                                            name="virgin line", line=dict(color=ui.GOLD)))
                    fg.add_trace(go.Scatter(x=[r.sigma_p], y=[c["ep"]], mode="markers", name="σ′p (Casagrande)",
                                            marker=dict(size=15, symbol="x", color=ui.GOLD_SOFT)))
                    fg.update_xaxes(type="log", title="p (kPa)")
                    fg.update_layout(yaxis_title="e (–)")
                    chart(fg, 420)
            except Exception as ex:  # noqa: BLE001
                st.error(f"The oedometer analysis failed: {ex}. Check that the pressures increase on loading.",
                         icon=":material/error:")
        with st.expander("Correlations, for clay with no consolidation test", icon=":material/functions:"):
            c1, c2, c3 = st.columns(3)
            LL = c1.number_input("Liquid limit LL (%)", 0.0, 200.0, 45.0)
            w = c2.number_input("Natural water content w (%)", 0.0, 200.0, 35.0)
            Gs = c3.number_input("Specific gravity Gs (–)", 2.0, 3.0, 2.70)
            st.markdown(f"Cc = 0.009(LL − 10) = **{lab.cc_terzaghi_peck(LL):.3f}** (Terzaghi & Peck 1967, undisturbed) · "
                        f"Cc = 0.007(LL − 10) = {lab.cc_skempton(LL):.3f} (Skempton 1944, remoulded) · "
                        f"e0 = w·Gs (S = 1) = **{lab.e0_saturated(w / 100, Gs):.3f}**")

# ------------------------------------------------------------------ P3
R = None
with tabs[2]:
    if not layers:
        st.error("Enter at least one layer in P1 to compute bearing capacity.", icon=":material/error:")
    else:
        try:
            R = bc.bearing_capacity(profile, shape, B, L, Df, P=P, MB=MB, ML=ML, alpha_deg=alpha, FS=FS, mode=mode,
                                    use_depth_factors=use_d, gamma_fill=g_fill)
        except ValueError as ex:
            st.error(f"{ex}. Reduce the moment or enlarge the footing. P4 and P5 use the net pressure entered "
                     "on their own tabs.", icon=":material/error:")
if R is not None:
    with tabs[2]:
        for w_ in R.warnings:
            st.warning(w_, icon=":material/warning:")
        with ui.card():
            ui.section("P3·a", "Inputs resolved from the profile",
                       f"Founding layer: {R.layer} · {'undrained, φ = 0' if R.undrained else 'drained'} · "
                       f"design WT {gwt_d:.2f} m bgl", anchor="p3a")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("c used (kPa)", f"{R.c:.2f}")
            c2.metric("φ used (°)", f"{R.phi:.2f}")
            c3.metric("q = σ′v at Df (kPa)", f"{R.q:.2f}")
            c4.metric("γ below base (kN/m³)", f"{R.gamma:.2f}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("e_B = M_B/P (m)", f"{R.eB:.3f}")
            c2.metric("e_L = M_L/P (m)", f"{R.eL:.3f}")
            c3.metric("B′ × L′ (m)", f"{R.B_eff:.2f} × {R.L_eff:.2f}" if shape != "Strip" else f"{R.B_eff:.3f}")
            c4.metric("A′ (m²)", f"{R.A_eff:.3f}")

        with ui.card():
            ui.section("P3·b", "Every factor, IS 6403:1981",
                       f"Shape (Table 2), depth (cl. 5.1.2.2) and inclination (cl. 5.1.2.3) factors · "
                       f"water-table factor W′ = {R.W:.3f} (cl. 5.1.2.4)")
            fac = pd.DataFrame({"Factor": ["Shape s", "Depth d", "Inclination i"],
                                "c-term": [R.sc, R.dc, R.ic], "q-term": [R.sq, R.dq, R.iq], "γ-term": [R.sg, R.dg, R.ig]})
            show_df(fac.round(4), "bearing_factors", hide_index=True, width="stretch")
            rows = []
            for t in (R.general, R.local):
                rows.append({"Mode": t.mode, "c or c_m (kPa)": t.c, "φ or φ_m (°)": t.phi, "Nc": t.Nc, "Nq": t.Nq,
                             "Nγ": t.Ng, "c·Nc·s·d·i (kPa)": t.term_c, "q(Nq−1)·s·d·i (kPa)": t.term_q,
                             "½Bγ·Nγ·s·d·i·W′ (kPa)": t.term_g, "q_nu (kPa)": t.q_nu})
            st.caption("Bearing capacity factors (IS 6403 Table 1). Local shear: c_m = ⅔c, tan φ_m = 0.67 tan φ.")
            show_df(pd.DataFrame(rows).round(3), "bearing_terms", hide_index=True, width="stretch")

        with ui.card():
            ui.section("P3·c", "Capacity vs applied pressure",
                       "Net applied = (P + W_footing+backfill − σv,total(Df)·A)/A′, compared with the net safe capacity.", anchor="p3c")
            c1, c2, c3 = st.columns(3)
            c1.metric(f"q_nu (kPa) · {R.mode_used.split(' (')[0]}", f"{R.q_nu:.1f}")
            c2.metric(f"q_ns = q_nu/{FS:g} (kPa)", f"{R.q_ns:.1f}")
            c3.metric("Gross safe = q_ns + q (kPa)", f"{R.q_safe_gross:.1f}")
            st.caption(f"Shear mode: {R.mode_used}")
            if R.q_net_applied is not None:
                c1, c2, c3 = st.columns(3)
                c1.metric("Gross applied (kPa)", f"{R.q_gross_applied:.1f}")
                c2.metric("Net applied (kPa)", f"{R.q_net_applied:.1f}")
                with c3:
                    st.markdown(f"**Check q_net ≤ q_ns**<br>{ui.pill(bool(R.ok))}", unsafe_allow_html=True)
            wl = bc.weak_layer_check(profile, R.B_eff, R.L_eff if shape != "Strip" else 100.0, Df,
                                     R.q_net_applied or R.q_ns, FS)
            if wl:
                st.markdown(f"**Soft underlying layer (2:1 projected area)**: {wl.layer} at {wl.z_top:.2f} m below "
                            f"the base · Δσ = {wl.delta_sigma:.1f} kPa · q_nu = {wl.q_nu_weak:.1f} kPa · "
                            f"FS = {wl.FS:.2f} &nbsp;{ui.pill(wl.ok)}", unsafe_allow_html=True)

        with ui.card():
            ui.section("P3·d", "Find the minimum size", "Smallest footing for which q_net ≤ q_ns.")
            c1, c2, c3 = st.columns([1, 1, 1])
            lb_ratio = c1.number_input("L/B for rectangle (–)", 1.0, 10.0, 1.5, 0.1) if shape == "Rectangle" else 1.0
            stepB = c2.number_input("Size increment (m)", 0.01, 0.5, 0.05, 0.01)
            with c3:
                st.write("")
                go_size = st.button("Size Footing", type="primary", width="stretch", icon=":material/straighten:")
            if go_size:
                Rs = bc.size_footing(profile, shape, P, Df, lb_ratio, MB, ML, FS, mode, step=stepB,
                                     use_depth_factors=use_d, gamma_fill=g_fill, alpha_deg=alpha)
                st.success(f"B = {Rs.B:.2f} m" + (f", L = {Rs.L:.2f} m" if shape == "Rectangle" else "") +
                           f" gives q_net = {Rs.q_net_applied:.1f} kPa ≤ q_ns = {Rs.q_ns:.1f} kPa",
                           icon=":material/check_circle:")

# ------------------------------------------------------------------ P4
q_def = float(R.q_net_applied) if (R is not None and R.q_net_applied) else 100.0
with tabs[3]:
    with ui.card():
        ui.section("P4", "Vertical stress increase Δσz below the footing",
                   "Corner: Newmark (1935) integration of Boussinesq. Centre: 4 × the corner value for "
                   "(B/2 × L/2), by superposition. 2:1 method: q·B·L/((B+z)(L+z)). Circle: closed-form "
                   "solution below the centre.")
        c1, c2, c3 = st.columns(3)
        q4 = c1.number_input("Net pressure q (kPa)", 0.0, 5000.0, round(max(q_def, 0.0), 2), 1.0,
                             help="Defaults to the net applied pressure from P3")
        zmax4 = c2.number_input("Depth below base (m)", 0.5, 60.0, max(4 * B, 5.0), 0.5)
        dz4 = c3.number_input("Step (m)", 0.05, 2.0, 0.25, 0.05)
        Lr = L if shape == "Rectangle" else B
        zs = np.arange(dz4, zmax4 + 1e-9, dz4)
        tbl = pd.DataFrame(stz.profile_table(q4, shape, B, Lr, zs))
        tbl.columns = ["z below base (m)", "Boussinesq centre (kPa)", "Boussinesq corner (kPa)", "2:1 (kPa)"]
        cL, cR = st.columns([1.4, 1])
        with cL:
            fg = go.Figure()
            for col, colr in zip(tbl.columns[1:], [ui.EMERALD, ui.GOLD, ui.TEAL]):
                fg.add_trace(go.Scatter(x=tbl[col], y=tbl["z below base (m)"], name=col, line=dict(color=colr, width=3)))
            fg.update_yaxes(autorange="reversed", title="z below base (m)")
            fg.update_layout(xaxis_title="Δσz (kPa)", legend=dict(orientation="h", y=-0.15))
            chart(fg, 500)
        with cR:
            show_df(tbl.round(3), "stress_increase", hide_index=True, height=500, width="stretch")
    with st.expander("Stress at any point (superposition)", icon=":material/my_location:"):
        c1, c2, c3 = st.columns(3)
        xp_ = c1.number_input("x from centre along B (m)", -50.0, 50.0, 0.0)
        yp_ = c2.number_input("y from centre along L (m)", -50.0, 50.0, 0.0)
        zp_ = c3.number_input("z below base (m)", 0.01, 60.0, 2.0)
        if shape in ("Square", "Rectangle"):
            st.metric("Δσz at the point (kPa)", f"{stz.rect_point(q4, B, Lr, xp_, yp_, zp_):.2f}")
        else:
            st.info("Available for square and rectangular footings.", icon=":material/info:")

# ------------------------------------------------------------------ P5
with tabs[4]:
    q5 = st.number_input("Net applied pressure q_net (kPa)", 0.0, 5000.0, round(max(q_def, 0.0), 2), 1.0,
                         key="q5", help="Defaults to the net applied pressure from P3")
    with ui.card():
        ui.section("P5·a", "Granular layers: strain influence factor method",
                   "Schmertmann, Hartman & Brown (1978): S = C1·C2·q_net·Σ(Iz/E)·Δz.")
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
            st.info(f"{SR.skipped_cohesive:.2f} m of cohesive soil lies inside the influence zone. Its settlement "
                    "is computed by consolidation below, not by Schmertmann.", icon=":material/info:")
        if SR.rows:
            sdf_ = pd.DataFrame(SR.rows)
            sdf_["ds"] = sdf_["ds"] * 1000
            sdf_.columns = ["z below base (m)", "Depth (m bgl)", "Layer", "Iz (–)", "E (kPa)", "Δs (mm)", "Note"]
            fgI = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("Iz (–)", "E (kPa)"))
            fgI.add_trace(go.Scatter(x=sdf_["Iz (–)"], y=sdf_["z below base (m)"], name="Iz", fill="tozerox",
                                     line=dict(color=ui.EMERALD, width=3), fillcolor="rgba(52,211,153,0.15)"), 1, 1)
            fgI.add_trace(go.Scatter(x=sdf_["E (kPa)"], y=sdf_["z below base (m)"], name="E", line_shape="hv",
                                     line=dict(color=ui.GOLD, width=3)), 1, 2)
            fgI.update_yaxes(autorange="reversed", title_text="z below base (m)", row=1, col=1)
            fgI.update_layout(showlegend=False)
            chart(fgI, 340)
            with st.expander("Sublayer table", icon=":material/table_rows:"):
                show_df(sdf_.round(4), "schmertmann_sublayers", hide_index=True, width="stretch")

    with ui.card():
        ui.section("P5·b", "Cohesive layers: one-dimensional consolidation",
                   "NC and OC clay in sublayers no thicker than 0.5 m (Terzaghi).")
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
            show_df(cdf.round(3), "consolidation_sublayers", hide_index=True, height=300, width="stretch")
            cols = st.columns(max(1, len(CR.per_layer)))
            for col, (k, v) in zip(cols, CR.per_layer.items()):
                col.metric(f"{k} (mm)", f"{v * 1000:.1f}")
        else:
            st.info("No cohesive layer with Cc > 0 lies below the base.", icon=":material/info:")

    lay_sc = []
    if CR.rows:
        with ui.card():
            ui.section("P5·c", "Time–settlement", "Terzaghi 1-D consolidation. Drainage is selected per layer.")
            for lay in CR.layers:
                key = f"{lay.description} ({lay.top:g}-{lay.bottom:g} m)"
                H = lay.bottom - max(lay.top, Df)
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**{lay.description}**<br><span style='color:#9DB8AA'>H = {H:.2f} m · "
                            f"Sc = {CR.per_layer[key] * 1000:.1f} mm</span>", unsafe_allow_html=True)
                cvv = c2.number_input("cv (m²/yr)", 0.001, 1000.0, float(lay.cv), key=f"cv_{key}")
                drn = c3.selectbox("Drainage", ["Double", "Top only", "Bottom only"],
                                   index=["Double", "Top only", "Bottom only"].index(lay.drainage)
                                   if lay.drainage in ("Double", "Top only", "Bottom only") else 0, key=f"dr_{key}")
                lay_sc.append((CR.per_layer[key], H, cvv, "Double" if drn == "Double" else "Single"))
            tmax = st.number_input("Plot up to (years)", 0.1, 200.0, 20.0, 1.0)
            tt = np.linspace(0, tmax, 400)
            tot, parts = se.time_settlement(lay_sc, tt)
            fgt = go.Figure()
            fgt.add_trace(go.Scatter(x=tt, y=(tot + SR.settlement) * 1000, name="Total (immediate + consolidation)",
                                     line=dict(color=ui.EMERALD, width=3.5), fill="tozeroy",
                                     fillcolor="rgba(52,211,153,0.08)"))
            fgt.add_trace(go.Scatter(x=tt, y=tot * 1000, name="Consolidation", line=dict(dash="dash", color=ui.GOLD, width=2.5)))
            fgt.update_yaxes(autorange="reversed", title="Settlement (mm)")
            fgt.update_layout(xaxis_title="Time (years)", legend=dict(orientation="h", y=-0.2))
            chart(fgt, 400)
            rows = []
            for (Sc, H, cvv, drn), lay in zip(lay_sc, CR.layers):
                rows.append({"Layer": lay.description, "Hdr (m)": se.drainage_path(H, drn),
                             "t50 (yr)": se.time_for_U(0.5, H, cvv, drn), "t90 (yr)": se.time_for_U(0.9, H, cvv, drn)})
            show_df(pd.DataFrame(rows).round(3), "consolidation_times", hide_index=True, width="stretch")

    total = SR.settlement + CR.total
    with ui.card():
        ui.section("P5·d", "Settlement summary", anchor="p5d")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Sand, Schmertmann (mm)", f"{SR.settlement * 1000:.1f}")
        c2.metric("Consolidation (mm)", f"{CR.total * 1000:.1f}")
        c3.metric("Total (mm)", f"{total * 1000:.1f}")
        lim = c4.number_input("Permissible total (mm), IS 1904 value", 0.0, 500.0, 75.0, 5.0)
        st.markdown(f"Total settlement against the permissible value &nbsp;{ui.pill(total * 1000 <= lim, 'WITHIN LIMIT', 'EXCEEDS LIMIT')}",
                    unsafe_allow_html=True)

# ------------------------------------------------------------- Liquefaction
LR = []
with tabs[5]:
    with ui.card():
        ui.section("Extra", "Liquefaction triggering: IS 1893 (Part 1):2016 Annex F",
                   "Not part of the P1–P5 brief. It is included because shallow saturated sands in high "
                   "seismic zones must be screened. CSR = 0.65 (a_max/g)(σv/σ′v) r_d; CRR from (N1)60cs "
                   "(Youd et al. 2001); FS = CRR·MSF/CSR.", anchor="liq")
        c1, c2, c3, c4 = st.columns(4)
        amax = c1.number_input("a_max / g (–)", 0.01, 1.0, 0.36, 0.01, help="e.g. zone factor Z (IS 1893 Table 3)")
        Mw = c2.number_input("Moment magnitude Mw (–)", 5.0, 9.0, 7.5, 0.1)
        ER = c3.number_input("Hammer energy ratio (%)", 30.0, 100.0, 60.0, 5.0)
        dbh = c4.number_input("Borehole diameter (mm)", 60.0, 250.0, 150.0, 5.0)
        gl = [l.description for l in profile.sorted_layers() if l.soil_type == GRANULAR]
        fines0 = D.get("fines", {})
        cL, cR = st.columns([1, 1.3])
        with cL:
            fdf = st.data_editor(pd.DataFrame({"Layer": gl, "Fines content FC (%)": [fines0.get(g_, 0.0) for g_ in gl]}),
                                 key=f"fines{ver}", disabled=["Layer"], hide_index=True, width="stretch")
            csv_button(fdf, "fines_content")
        fines = dict(zip(fdf["Layer"], fdf["Fines content FC (%)"]))
        LR = liq.liquefaction(profile, amax, Mw, energy_ratio=ER, borehole_mm=dbh, fines=fines)
        if LR:
            ldf_ = pd.DataFrame([r.__dict__ for r in LR])
            ldf_.columns = ["Depth (m)", "N", "Layer", "FC (%)", "σv (kPa)", "σ′v (kPa)", "r_d", "CSR", "C_N", "C_R",
                            "(N1)60", "α", "β", "(N1)60cs", "CRR7.5", "MSF", "FS_L", "Status"]
            fin = ldf_[np.isfinite(ldf_["FS_L"])]
            with cR:
                if len(fin):
                    fg = go.Figure(go.Scatter(x=fin["FS_L"], y=fin["Depth (m)"], mode="markers+lines", name="FS_L",
                                              line=dict(color=ui.EMERALD, width=3),
                                              marker=dict(size=11, color=[ui.DANGER if v < 1 else ui.EMERALD
                                                                          for v in fin["FS_L"]])))
                    fg.add_vline(x=1.0, line_dash="dash", line_color=ui.GOLD)
                    fg.update_yaxes(autorange="reversed", title="Depth (m)")
                    fg.update_layout(xaxis_title="FS against liquefaction (–)")
                    chart(fg, 320)
            show_df(ldf_.round(3), "liquefaction", hide_index=True, width="stretch")
        else:
            st.info("No SPT records in the profile yet.", icon=":material/info:")

# ----------------------------------------------------------------- Sources
with tabs[6]:
    with ui.card():
        src = ROOT / "SOURCES.md"
        st.markdown(src.read_text(encoding="utf-8") if src.exists() else "See README.md")

# ------------------------------------------------------------- summary strip
with summary:
    items = []
    if R is not None:
        items.append(ui.tile("Founding layer", R.layer.split("(")[0].strip()[:34], sub=f"φ {R.phi:.1f}° · W′ {R.W:.2f}",
                             ic="layers", text=True, go_to=(2, "p3a", "P3 Bearing · inputs resolved from the profile")))
        items.append(ui.tile("Net safe capacity", f"{R.q_ns:.0f}", "kPa", f"q_nu {R.q_nu:.0f} kPa · FS {FS:g}", ic="gauge", state="gold",
                             go_to=(2, "p3c", "P3 Bearing · capacity vs applied pressure")))
        if R.q_net_applied is not None:
            items.append(ui.tile("Net applied", f"{R.q_net_applied:.0f}", "kPa",
                                 "Bearing check passes" if R.ok else "Bearing check fails",
                                 ic="check" if R.ok else "x", state="pass" if R.ok else "fail",
                                 go_to=(2, "p3c", "P3 Bearing · capacity vs applied pressure")))
    items.append(ui.tile("Total settlement", f"{total * 1000:.0f}", "mm",
                         f"sand {SR.settlement * 1000:.0f} · clay {CR.total * 1000:.0f} mm", ic="arrow-down",
                         state="pass" if total * 1000 <= lim else "fail",
                         go_to=(4, "p5d", "P5 Settlement · summary")))
    fs_vals = [r.FS for r in LR if math.isfinite(r.FS)]
    if fs_vals:
        mfs = min(fs_vals)
        items.append(ui.tile("Liquefaction, min FS", f"{mfs:.2f}", "", "IS 1893 Annex F",
                             ic="waves", state="pass" if mfs >= 1 else "fail",
                             go_to=(5, "liq", "Liquefaction check")))
    ui.tiles(items)
