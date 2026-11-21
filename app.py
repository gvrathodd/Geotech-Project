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
from ui import accounts as acc
from ui import theme as ui

ROOT = Path(__file__).parent
EXAMPLES = ROOT / "examples"

st.set_page_config(page_title="Foundation Studio · CE 402", page_icon=":material/foundation:", layout="wide")
ui.inject()


def chart(fig, height=None, key=None, select=False):
    """Render a Plotly figure with the glass template (Streamlit's own theme off).
    With select=True a click on a point reruns the app and the selected points are returned
    (list of dicts with curve_number / point_index), so the matching table row can be highlighted."""
    if height:
        fig.update_layout(height=height)
    fig.update_layout(margin=dict(t=40, l=10, r=10, b=10))
    cfg = {"displaylogo": False}
    if not select:
        st.plotly_chart(fig, width="stretch", theme=None, config=cfg, key=key)
        return []
    fig.update_traces(unselected=dict(marker=dict(opacity=0.35)), selector=dict(mode="markers"))
    fig.update_traces(unselected=dict(marker=dict(opacity=0.35)), selector=dict(mode="markers+lines"))
    ev = st.plotly_chart(fig, width="stretch", theme=None, config=cfg, key=key,
                         on_select="rerun", selection_mode="points")
    try:
        return list(ev["selection"]["points"])
    except (KeyError, TypeError, AttributeError):
        return []


def picked(points, curves=None):
    """Index of the first clicked point (optionally restricted to some traces), else None."""
    for pt in points or []:
        if curves is None or pt.get("curve_number") in curves:
            return pt.get("point_index")
    return None


HL = "background-color: rgba(46,240,168,0.30); color: #FFFFFF; font-weight: 600"
esc = html.escape


def csv_button(df: pd.DataFrame, name: str):
    """'Export CSV' under a table.  UTF-8 with BOM so Excel shows σ′, φ′, ° and ³ correctly;
    the file name carries the profile name so exports from different boreholes don't collide."""
    prof = re.sub(r"[^a-z0-9]+", "-", str(st.session_state.data.get("name", "profile")).lower()).strip("-")[:24]
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    st.download_button("Export CSV", df.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"{prof or 'profile'}_{slug}.csv", mime="text/csv",
                       icon=":material/table_view:", key=f"csv_{slug}")


def show_df(df: pd.DataFrame, csv: str, highlight=None, **kw):
    """st.dataframe followed by its Export CSV button.  `highlight` = index label of a row to
    highlight (the row matching a point clicked on the chart)."""
    if highlight is not None and highlight in df.index:
        sty = (df.style.apply(lambda r: [HL] * len(r) if r.name == highlight else [""] * len(r), axis=1)
               .format(precision=3, na_rep="–"))
        st.dataframe(sty, **kw)
    else:
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
# footing inputs of a project opened from "My projects" are applied before the widgets exist
for _k, _v in st.session_state.pop("_pending_footing", {}).items():
    st.session_state[_k] = _v
D = st.session_state.data

# ================================================================= SIDEBAR
with st.sidebar:
    ui.brand()
    ui.toc()
    acct_box = st.container()
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
    shape = st.selectbox("Shape", bc.SHAPES, index=1, key="in_shape")
    B = st.number_input("Width B (m)" if shape != "Circle" else "Diameter D (m)", 0.3, 30.0, 2.0, 0.05, key="in_B")
    L = None
    if shape == "Rectangle":
        L = st.number_input("Length L (m)", 0.3, 60.0, max(3.0, B), 0.05, key="in_L")
    Df = st.number_input("Founding depth Df (m)", 0.0, 10.0, 1.5, 0.1, key="in_Df")
    st.markdown("### Loads · service, at founding level")
    P = st.number_input("Vertical load P (kN" + ("/m)" if shape == "Strip" else ")"), 0.0, 1e6, 1000.0, 10.0, key="in_P")
    MB = st.number_input("Moment along B, M_B (kN·m)", 0.0, 1e5, 0.0, 5.0, key="in_MB",
                         help="Moment causing eccentricity in the B direction")
    ML = 0.0
    if shape != "Strip":
        ML = st.number_input("Moment along L, M_L (kN·m)", 0.0, 1e5, 0.0, 5.0, key="in_ML",
                             help="Moment causing eccentricity in the L direction")
    alpha = st.number_input("Load inclination α (°)", 0.0, 45.0, 0.0, 1.0, key="in_alpha",
                            help="Inclination of the load to the vertical")
    st.markdown("### Design options")
    FS = st.number_input("Factor of safety on q_nu (–)", 1.0, 10.0, 3.0, 0.5)
    mode_lbl = st.selectbox("Shear failure mode", ["Auto (interpolate φ 28°–36°)", "General", "Local"])
    mode = {"Auto (interpolate φ 28°–36°)": "auto", "General": "general", "Local": "local"}[mode_lbl]
    use_d = st.checkbox("Apply depth factors (compacted backfill)", True)
    g_fill = st.number_input("Footing + backfill unit weight (kN/m³)", 0.0, 30.0, 20.0, 0.5)
    ui.shortcuts_hint()

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
            ui.section("P1", "Profile drawing", "Strata, in-situ stresses at the design water table, and SPT N. "
                       "Click an SPT point to see its correction steps.", anchor="p1draw")
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
            pts = chart(fig, 620, key="ch_p1", select=bool(steps))
            i_spt = picked(pts, curves={3, 4})
            st.session_state["sel_spt"] = steps[i_spt].depth if (steps and i_spt is not None and i_spt < len(steps)) else None
            if st.session_state["sel_spt"] is not None:
                s_ = steps[i_spt]
                st.markdown(
                    f'<div class="sec-sub">Selected SPT at <b>{s_.depth:g} m</b> ({esc(s_.layer)}): N = {s_.N:g} → '
                    f'σ′v = {s_.sigma_eff_kpa:.1f} kPa, C_N = {s_.CN:.3f} → N′ = {s_.N1:.2f} → N″ = {s_.N2:.2f}. '
                    f'Row highlighted in <a href="#sec-p2a" data-fs-anchor="p2a">P2·a</a>.</div>',
                    unsafe_allow_html=True)
            st.download_button("Download Project (.json)", json.dumps({**D, **profile.to_dict()}, indent=2),
                               file_name="profile.json", mime="application/json", icon=":material/download:")

# ------------------------------------------------------------------ P2
with tabs[1]:
    with ui.card():
        ui.section("P2·a", "SPT N corrections: IS 2131:1981",
                   "Step 1, overburden: N′ = C_N·N with C_N = 0.77 log₁₀(20/p′), p′ in kg/cm² (IS 2131 Fig. 1). "
                   "Step 2, dilatancy (saturated fine/silty sand with N′ > 15): N″ = 15 + 0.5(N′ − 15). "
                   "Both steps use the measured water table.", anchor="p2a")
        c1, c2, c3 = st.columns(3)
        cn_max = c1.number_input("Upper limit on C_N (–)", 1.0, 3.0, 2.0, 0.1)
        qcn = c2.number_input("qc/N for E estimate (MPa per blow)", 0.1, 1.5, 0.4, 0.05)
        LB_for_E = (L / B) if (shape == "Rectangle" and L) else (10.0 if shape == "Strip" else 1.0)
        ui.metric(c3, "L/B used for E = (2.5…3.5)·qc", f"{LB_for_E:.2f}",
                  formula="E = [2.5 + (L/B − 1)/9] · q<sub>c</sub> &nbsp;(1 ≤ L/B ≤ 10)<br>q<sub>c</sub> = (q<sub>c</sub>/N) · N″",
                  numbers=f"Shape = {shape} → L/B = {LB_for_E:.2f} → E = {2.5 + (min(max(LB_for_E, 1), 10) - 1) / 9:.3f} · q<sub>c</sub>; "
                          f"q<sub>c</sub>/N = {qcn:.2f} MPa per blow",
                  ref="Schmertmann, Hartman &amp; Brown (1978): E = 2.5q<sub>c</sub> axisymmetric, 3.5q<sub>c</sub> plane strain; "
                      "Robertson, Campanella &amp; Wightman (1983): q<sub>c</sub>/N ratios")
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
            sel = st.session_state.get("sel_spt")
            hl = next((i for i, s in enumerate(steps) if sel is not None and abs(s.depth - sel) < 1e-9), None)
            show_df(pd.DataFrame(rows).round(3), "spt_corrections", highlight=hl, width="stretch", hide_index=True)
        else:
            st.info("No SPT records in the profile yet. Add them in P1.", icon=":material/info:")

    labd = D.get("lab", {})
    with ui.card():
        ui.section("P2·b", "Direct shear: least-squares c′ and φ′",
                   "τf = c′ + σn·tan φ′, fitted by ordinary least squares (normal equations).", anchor="p2b")
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
            x_, y_ = dd["σn (kPa)"].to_numpy(float), dd["τf (kPa)"].to_numpy(float)
            n_, Sx, Sy, Sxy, Sxx = len(x_), x_.sum(), y_.sum(), (x_ * y_).sum(), (x_ * x_).sum()
            if force0:
                f_ls = "tan φ′ = Σστ / Σσ², &nbsp;c′ = 0 (forced through the origin)"
                n_ls = f"tan φ′ = {Sxy:.1f} / {Sxx:.0f} = {f.tan_phi:.4f} → φ′ = {f.phi:.2f}°"
            else:
                f_ls = "tan φ′ = (nΣστ − ΣσΣτ) / (nΣσ² − (Σσ)²)<br>c′ = τ̄ − σ̄ · tan φ′"
                n_ls = (f"n = {n_}, Σσ = {Sx:.1f}, Στ = {Sy:.2f}, Σστ = {Sxy:.1f}, Σσ² = {Sxx:.0f}<br>"
                        f"tan φ′ = ({n_} × {Sxy:.1f} − {Sx:.1f} × {Sy:.2f}) / ({n_} × {Sxx:.0f} − {Sx:.1f}²) = {f.tan_phi:.4f}"
                        f" → φ′ = {f.phi:.2f}°<br>c′ = {Sy / n_:.3f} − {Sx / n_:.2f} × {f.tan_phi:.4f} = {f.c:.2f} kPa")
            r_ls = "Ordinary least squares (normal equations) on the Mohr–Coulomb envelope τ<sub>f</sub> = c′ + σ<sub>n</sub> tan φ′"
            yhat = f.c + f.tan_phi * x_
            ss_res, ss_tot = float(((y_ - yhat) ** 2).sum()), float(((y_ - y_.mean()) ** 2).sum())
            with cL:
                m1, m2, m3 = st.columns(3)
                ui.metric(m1, "c′ (kPa)", f"{f.c:.2f}", f_ls, n_ls, r_ls)
                ui.metric(m2, "φ′ (°)", f"{f.phi:.2f}", f_ls, n_ls, r_ls)
                ui.metric(m3, "R² (–)", f"{f.r2:.4f}", "R² = 1 − Σ(τ − τ̂)² / Σ(τ − τ̄)²",
                          f"1 − {ss_res:.3f} / {ss_tot:.2f} = {f.r2:.4f}", r_ls)
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
        ui.section("P2·c", "Unconsolidated undrained triaxial: cu", "cu = (σ1 − σ3)f / 2 for each specimen.", anchor="p2c")
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
                    ui.metric(st, f"{s['label']} · cu (kPa)", f"{cu:.2f}",
                              "c<sub>u</sub> = mean[(σ<sub>1</sub> − σ<sub>3</sub>)<sub>f</sub> / 2], φ<sub>u</sub> = 0",
                              f"({' + '.join(f'{v:g}' for v in dv)}) / (2 × {len(dv)}) = {cu:.2f} kPa",
                              "UU triaxial test, IS 2720 (Part 11):1993; φ<sub>u</sub> = 0 concept for saturated clay")

    with ui.card():
        ui.section("P2·d", "One-dimensional consolidation: Cc, Cs, σ′p, cv",
                   "Lab-sheet units are converted explicitly: 1 kg/cm² = 98.07 kPa, 1 cm²/s = 3155.76 m²/yr. "
                   "Click a test point to highlight its row.", anchor="p2d")
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
                    hl_oed = picked(chart(fg, 420, key="ch_oed", select=True), curves={0})
                load_i = [i for i, sg in enumerate(r.stage) if sg.startswith("load")]
                load_i.sort(key=lambda i: r.p_kpa[i])
                vir = load_i[-int(nv):]
                unl_i = [int(np.argmax(r.p_kpa))] + [i for i, sg in enumerate(r.stage) if sg.startswith("unload")]
                pts_txt = lambda idx: ", ".join(f"({r.p_kpa[i]:.1f} kPa, {r.e[i]:.3f})" for i in idx)
                conv = "Pressures converted: kg/cm² × 98.0665 = kPa. " if p_unit == "kg/cm2" else ""
                cc_num = (f"({r.e[vir[0]]:.3f} − {r.e[vir[1]]:.3f}) / log₁₀({r.p_kpa[vir[1]]:.1f} / {r.p_kpa[vir[0]]:.1f}) "
                          f"= {r.Cc:.3f}" if len(vir) == 2 else f"Least-squares slope through {pts_txt(vir)} = {r.Cc:.3f}")
                c_ = r.construction
                with cL:
                    m1, m2, m3 = st.columns(3)
                    ui.metric(m1, "Cc (–)", f"{r.Cc:.3f}",
                              f"C<sub>c</sub> = −Δe / Δlog<sub>10</sub>p′ on the virgin line (last {int(nv)} loading points)",
                              cc_num, "IS 2720 (Part 15):1986; Das, Principles of Geotechnical Engineering", conv)
                    ui.metric(m2, "Cs (–)", f"{r.Cs:.4f}",
                              "C<sub>s</sub> = −Δe / Δlog<sub>10</sub>p′ on the unloading branch (least squares, from the maximum load)",
                              f"Points {pts_txt(unl_i)} → C<sub>s</sub> = {r.Cs:.4f}",
                              "IS 2720 (Part 15):1986; Das, Principles of Geotechnical Engineering", conv)
                    ui.metric(m3, "σ′p (kPa)", f"{r.sigma_p:.1f}",
                              "Casagrande: at the point of maximum curvature draw the horizontal and the tangent; "
                              "their bisector meets the extended virgin line at σ′<sub>p</sub>",
                              f"Max curvature at p = {10 ** c_['xm']:.1f} kPa (e = {c_['em']:.3f}); tangent slope "
                              f"{c_['tangent_slope']:.3f}, bisector slope {c_['bisector_slope']:.3f}; virgin line "
                              f"e = {c_['virgin_intercept']:.3f} {c_['virgin_slope']:+.3f}·log₁₀p<br>→ log₁₀σ′<sub>p</sub> = "
                              f"{c_['xp']:.3f} → σ′<sub>p</sub> = {r.sigma_p:.1f} kPa ({r.sigma_p / 98.0665:.2f} kg/cm²)",
                              "Casagrande (1936); IS 2720 (Part 15):1986", conv)
                    tab = pd.DataFrame({"p (kPa)": r.p_kpa, "Stage": r.stage, "e (–)": r.e,
                                        "cv (m²/yr)": r.cv_m2yr if r.cv_m2yr else None})
                    show_df(tab.round(3), "oedometer_results", highlight=hl_oed, hide_index=True, width="stretch")
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
            ref63 = "IS 6403:1981 cl. 5.1.2"
            lay_txt = f"Layer at D<sub>f</sub> = {Df:.2f} m: {esc(R.layer)}"
            u_df = R.sigma_tot_Df - R.q
            c1, c2, c3, c4 = st.columns(4)
            ui.metric(c1, "c used (kPa)", f"{R.c:.2f}",
                      "c = c<sub>u</sub> (undrained, φ = 0)" if R.undrained else "c = c′ of the layer at the founding level",
                      f"{lay_txt} → c = {R.c:.2f} kPa", ref63)
            ui.metric(c2, "φ used (°)", f"{R.phi:.2f}",
                      "φ = 0 (undrained)" if R.undrained else "φ = φ′ of the layer at the founding level",
                      f"{lay_txt} → φ = {R.phi:.2f}°. Shear mode: {R.mode_used}", ref63)
            ui.metric(c3, "q = σ′v at Df (kPa)", f"{R.q:.2f}",
                      "q = σ′<sub>v</sub>(D<sub>f</sub>) = Σγ<sub>i</sub>h<sub>i</sub> − u &nbsp;(γ<sub>moist</sub> above, "
                      "γ<sub>sat</sub> below the design WT)",
                      f"σ<sub>v</sub>(D<sub>f</sub>) = {R.sigma_tot_Df:.2f} kPa; u = 9.81 × max({Df:.2f} − {gwt_d:.2f}, 0) = "
                      f"{u_df:.2f} kPa<br>q = {R.sigma_tot_Df:.2f} − {u_df:.2f} = {R.q:.2f} kPa",
                      "IS 6403:1981 (q = effective overburden at founding level); Terzaghi effective-stress principle")
            ui.metric(c4, "γ below base (kN/m³)", f"{R.gamma:.2f}",
                      "γ = γ<sub>sat</sub> if z<sub>w</sub> &lt; D<sub>f</sub> + B′, else γ<sub>moist</sub> "
                      "(bulk unit weight, used together with W′ — never γ′ and W′ together)",
                      f"z<sub>w</sub> = {gwt_d:.2f} m vs D<sub>f</sub> + B′ = {Df + R.B_eff:.2f} m → γ = {R.gamma:.2f} kN/m³; "
                      f"W′ = {R.W:.3f}", "IS 6403:1981 cl. 5.1.2.4")
            refe = "IS 6403:1981 effective-area method for eccentric loads; Meyerhof (1953)"
            c1, c2, c3, c4 = st.columns(4)
            ui.metric(c1, "e_B = M_B/P (m)", f"{R.eB:.3f}", "e<sub>B</sub> = M<sub>B</sub> / P",
                      f"{MB:.1f} / {P:.1f} = {R.eB:.3f} m (kern limit B/6 = {R.B / 6:.3f} m)" if P else "P = 0", refe)
            ui.metric(c2, "e_L = M_L/P (m)", f"{R.eL:.3f}", "e<sub>L</sub> = M<sub>L</sub> / P",
                      f"{ML:.1f} / {P:.1f} = {R.eL:.3f} m (kern limit L/6 = {R.L / 6:.3f} m)" if P else "P = 0", refe)
            ui.metric(c3, "B′ × L′ (m)", f"{R.B_eff:.2f} × {R.L_eff:.2f}" if shape != "Strip" else f"{R.B_eff:.3f}",
                      "B′ = B − 2e<sub>B</sub>, &nbsp;L′ = L − 2e<sub>L</sub> &nbsp;(B′ ≤ L′)",
                      f"B′ = {R.B:.3f} − 2 × {R.eB:.3f}, L′ = {R.L:.3f} − 2 × {R.eL:.3f} → {R.B_eff:.3f} × {R.L_eff:.3f} m",
                      refe, "An eccentric circle is analysed as the equal-area square." if shape == "Circle" else "")
            ui.metric(c4, "A′ (m²)", f"{R.A_eff:.3f}", "A′ = B′ · L′ &nbsp;(centric circle: πD²/4)",
                      f"A′ = {R.A_eff:.3f} m²", refe)

        with ui.card():
            ui.section("P3·b", "Every factor, IS 6403:1981",
                       f"Shape (Table 2), depth (cl. 5.1.2.2) and inclination (cl. 5.1.2.3) factors · "
                       f"water-table factor W′ = {R.W:.3f} (cl. 5.1.2.4)", anchor="p3b")
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
            g_, l_ = R.general, R.local
            if R.undrained:
                f_qnu = "q<sub>nu</sub> = c<sub>u</sub> N<sub>c</sub> s<sub>c</sub> d<sub>c</sub> i<sub>c</sub>, N<sub>c</sub> = 5.14 (⅔c<sub>u</sub> for local shear)"
                n_qnu = (f"{'⅔ × ' if mode == 'local' else ''}{R.c:.2f} × 5.14 × {R.sc:.3f} × {R.dc:.3f} × {R.ic:.3f} "
                         f"= {R.q_nu:.1f} kPa")
            else:
                t_ = min(max((R.phi - 28.0) / 8.0, 0.0), 1.0)
                f_qnu = ("q<sub>nu</sub> = c N<sub>c</sub> s<sub>c</sub> d<sub>c</sub> i<sub>c</sub> + q (N<sub>q</sub> − 1) "
                         "s<sub>q</sub> d<sub>q</sub> i<sub>q</sub> + ½ B′ γ N<sub>γ</sub> s<sub>γ</sub> d<sub>γ</sub> i<sub>γ</sub> W′"
                         "<br>local shear: c<sub>m</sub> = ⅔c, tan φ<sub>m</sub> = 0.67 tan φ")
                n_qnu = (f"General (φ = {g_.phi:.2f}°, N<sub>q</sub> = {g_.Nq:.2f}, N<sub>γ</sub> = {g_.Ng:.2f}): "
                         f"{g_.term_c:.1f} + {R.q:.2f}·({g_.Nq:.2f} − 1)·{R.sq:.2f}·{R.dq:.3f}·{R.iq:.2f} "
                         f"+ ½·{R.B_eff:.2f}·{R.gamma:.2f}·{g_.Ng:.2f}·{R.sg:.2f}·{R.dg:.3f}·{R.ig:.2f}·{R.W:.3f} "
                         f"= {g_.term_c:.1f} + {g_.term_q:.1f} + {g_.term_g:.1f} = <b>{g_.q_nu:.1f}</b> kPa<br>"
                         f"Local (φ<sub>m</sub> = {l_.phi:.2f}°): {l_.term_c:.1f} + {l_.term_q:.1f} + {l_.term_g:.1f} "
                         f"= <b>{l_.q_nu:.1f}</b> kPa<br>")
                if mode == "auto":
                    n_qnu += (f"Interpolated: t = (φ − 28)/8 = {t_:.2f} → {l_.q_nu:.1f} + {t_:.2f} × "
                              f"({g_.q_nu:.1f} − {l_.q_nu:.1f}) = <b>{R.q_nu:.1f}</b> kPa")
                else:
                    n_qnu += f"Mode selected: {R.mode_used} → q<sub>nu</sub> = <b>{R.q_nu:.1f}</b> kPa"
            r_qnu = ("IS 6403:1981 cl. 5.1.2 (general & local shear); Table 1 (N factors, Vesic Nγ); Table 2 (shape); "
                     "cl. 5.1.2.2 depth, 5.1.2.3 inclination, 5.1.2.4 W′")
            A_full = (math.pi * R.B ** 2 / 4 if shape == "Circle" else R.B * (R.L if shape != "Strip" else 1.0))
            Wf_ = g_fill * A_full * Df
            c1, c2, c3 = st.columns(3)
            ui.metric(c1, f"q_nu (kPa) · {R.mode_used.split(' (')[0]}", f"{R.q_nu:.1f}", f_qnu, n_qnu, r_qnu,
                      "Interpolation between φ = 28° (local) and 36° (general) is the textbook practice the group adopted; "
                      "IS 6403 gives no φ-based switch." if (mode == "auto" and not R.undrained) else "")
            ui.metric(c2, f"q_ns = q_nu/{FS:g} (kPa)", f"{R.q_ns:.1f}", "q<sub>ns</sub> = q<sub>nu</sub> / FS",
                      f"{R.q_nu:.1f} / {FS:g} = {R.q_ns:.1f} kPa", "IS 6403:1981; FS = 3 on the net ultimate capacity (brief)")
            ui.metric(c3, "Gross safe = q_ns + q (kPa)", f"{R.q_safe_gross:.1f}", "q<sub>s</sub> = q<sub>ns</sub> + q",
                      f"{R.q_ns:.1f} + {R.q:.2f} = {R.q_safe_gross:.1f} kPa", "IS 6403:1981 (safe bearing capacity)")
            st.caption(f"Shear mode: {R.mode_used}")
            if R.q_net_applied is not None:
                c1, c2, c3 = st.columns(3)
                ui.metric(c1, "Gross applied (kPa)", f"{R.q_gross_applied:.1f}",
                          "q<sub>gross</sub> = (P + W<sub>f</sub>) / A′, &nbsp;W<sub>f</sub> = γ<sub>f</sub> · A · D<sub>f</sub>",
                          f"W<sub>f</sub> = {g_fill:g} × {A_full:.3f} × {Df:.2f} = {Wf_:.1f} kN<br>"
                          f"({P:.1f} + {Wf_:.1f}) / {R.A_eff:.3f} = {R.q_gross_applied:.1f} kPa",
                          "Footing + backfill weight above the base (group decision D5: γ<sub>f</sub> = 20 kN/m³ default)")
                ui.metric(c2, "Net applied (kPa)", f"{R.q_net_applied:.1f}",
                          "q<sub>net</sub> = (P + W<sub>f</sub> − σ<sub>v</sub>(D<sub>f</sub>) · A) / A′",
                          f"({P:.1f} + {Wf_:.1f} − {R.sigma_tot_Df:.2f} × {A_full:.3f}) / {R.A_eff:.3f} = "
                          f"{R.q_net_applied:.1f} kPa {'≤' if R.ok else '&gt;'} q<sub>ns</sub> = {R.q_ns:.1f} kPa",
                          "Net pressure = gross pressure − total overburden removed; compared with the NET safe capacity")
                with c3:
                    st.markdown(f"**Check q_net ≤ q_ns**<br>{ui.pill(bool(R.ok))}", unsafe_allow_html=True)
            wl = bc.weak_layer_check(profile, R.B_eff, R.L_eff if shape != "Strip" else 100.0, Df,
                                     R.q_net_applied or R.q_ns, FS)
            if wl:
                st.markdown(f"**Soft underlying layer (2:1 projected area)**: {wl.layer} at {wl.z_top:.2f} m below "
                            f"the base · Δσ = {wl.delta_sigma:.1f} kPa · q_nu = {wl.q_nu_weak:.1f} kPa · "
                            f"FS = {wl.FS:.2f} &nbsp;{ui.pill(wl.ok)}", unsafe_allow_html=True)

        with ui.card():
            ui.section("P3·d", "Find the minimum size", "Smallest footing for which q_net ≤ q_ns.", anchor="p3d")
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
                   "solution below the centre. Click a curve point to highlight its row.", anchor="p4")
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
                fg.add_trace(go.Scatter(x=tbl[col], y=tbl["z below base (m)"], name=col, mode="lines+markers",
                                        line=dict(color=colr, width=3), marker=dict(size=6, color=colr)))
            fg.update_yaxes(autorange="reversed", title="z below base (m)")
            fg.update_layout(xaxis_title="Δσz (kPa)", legend=dict(orientation="h", y=-0.15))
            hl4 = picked(chart(fg, 500, key="ch_p4", select=True))
        with cR:
            if hl4 is not None:
                st.caption(f"Selected z = {tbl.iloc[hl4, 0]:.2f} m below the base (row highlighted).")
            show_df(tbl.round(3), "stress_increase", highlight=hl4, hide_index=True, height=500, width="stretch")
    with st.expander("Stress at any point (superposition)", icon=":material/my_location:"):
        c1, c2, c3 = st.columns(3)
        xp_ = c1.number_input("x from centre along B (m)", -50.0, 50.0, 0.0)
        yp_ = c2.number_input("y from centre along L (m)", -50.0, 50.0, 0.0)
        zp_ = c3.number_input("z below base (m)", 0.01, 60.0, 2.0)
        if shape in ("Square", "Rectangle"):
            v_pt = stz.rect_point(q4, B, Lr, xp_, yp_, zp_)
            ui.metric(st, "Δσz at the point (kPa)", f"{v_pt:.2f}",
                      "Δσ<sub>z</sub> = q · Σ ± I(m, n) over four corner rectangles; "
                      "I = Newmark corner factor, m = a/z, n = b/z",
                      f"q = {q4:.1f} kPa, B × L = {B:.2f} × {Lr:.2f} m, point (x, y) = ({xp_:.2f}, {yp_:.2f}) m, "
                      f"z = {zp_:.2f} m → Δσ<sub>z</sub> = {v_pt:.2f} kPa ({(v_pt / q4 * 100) if q4 else 0:.1f}% of q)",
                      "Boussinesq (1885); Newmark (1935); Das, Principles of Geotechnical Engineering")
        else:
            st.info("Available for square and rectangular footings.", icon=":material/info:")

# ------------------------------------------------------------------ P5
with tabs[4]:
    q5 = st.number_input("Net applied pressure q_net (kPa)", 0.0, 5000.0, round(max(q_def, 0.0), 2), 1.0,
                         help="Follows the net applied pressure from P3; type a value to override")
    with ui.card():
        ui.section("P5·a", "Granular layers: strain influence factor method",
                   "Schmertmann, Hartman & Brown (1978): S = C1·C2·q_net·Σ(Iz/E)·Δz. "
                   "Click the Iz or E curve to highlight that sublayer.", anchor="p5a")
        c1, c2 = st.columns(2)
        t_s = c1.number_input("Time for creep factor C2 (years)", 0.1, 100.0, 0.1, 0.1)
        dz5 = c2.number_input("Sublayer thickness for integration (m)", 0.01, 0.5, 0.1, 0.01)
        SR = se.schmertmann(profile, shape, B, L, Df, q5, t_s, dz5)
        sig0 = profile.sigma_eff(Df, gwt_d)
        LBs = 10.0 if shape == "Strip" else ((L or B) / B)
        rs = "Schmertmann, Hartman &amp; Brown (1978), J. Geotech. Eng. Div. ASCE 104(GT8)"
        sumIE = SR.settlement / (SR.C1 * SR.C2 * q5) if q5 > 0 else 0.0
        c1, c2, c3, c4, c5 = st.columns(5)
        ui.metric(c1, "C1 (–)", f"{SR.C1:.3f}", "C<sub>1</sub> = 1 − 0.5 σ′<sub>0</sub> / q<sub>net</sub> ≥ 0.5",
                  f"σ′<sub>0</sub> = σ′<sub>v</sub>(D<sub>f</sub>) = {sig0:.2f} kPa → 1 − 0.5 × {sig0:.2f} / {q5:.1f} = "
                  f"{(1 - 0.5 * sig0 / q5) if q5 else 0:.3f}" + (" → limited to 0.5" if q5 and 1 - 0.5 * sig0 / q5 < 0.5 else ""), rs)
        ui.metric(c2, "C2 (–)", f"{SR.C2:.3f}", "C<sub>2</sub> = 1 + 0.2 log<sub>10</sub>(t / 0.1 yr)",
                  f"t = {t_s:g} yr → 1 + 0.2 × log₁₀({t_s:g} / 0.1) = {SR.C2:.3f}", rs)
        ui.metric(c3, "Izp (–)", f"{SR.Izp:.3f}", "I<sub>zp</sub> = 0.5 + 0.1 √(q<sub>net</sub> / σ′<sub>vp</sub>), "
                  "σ′<sub>vp</sub> at depth D<sub>f</sub> + z<sub>p</sub>",
                  f"σ′<sub>vp</sub> = σ′<sub>v</sub>({Df + SR.zp:.2f} m) = {SR.sigma_vp:.2f} kPa → 0.5 + 0.1 × "
                  f"√({q5:.1f} / {SR.sigma_vp:.2f}) = {SR.Izp:.3f}", rs)
        ui.metric(c4, "zp / z_max (m)", f"{SR.zp:.2f} / {SR.z_infl:.2f}",
                  "L/B = 1: z<sub>p</sub> = B/2, z<sub>max</sub> = 2B, I<sub>z0</sub> = 0.1; L/B ≥ 10: z<sub>p</sub> = B, "
                  "z<sub>max</sub> = 4B, I<sub>z0</sub> = 0.2; linear in between",
                  f"B = {B:.2f} m, L/B = {LBs:.2f} → z<sub>p</sub> = {SR.zp:.2f} m, z<sub>max</sub> = {SR.z_infl:.2f} m, "
                  f"I<sub>z0</sub> = {SR.Iz0:.3f}", rs)
        ui.metric(c5, "Settlement (mm)", f"{SR.settlement * 1000:.1f}",
                  "S = C<sub>1</sub> C<sub>2</sub> q<sub>net</sub> Σ (I<sub>z</sub> / E) Δz &nbsp;(granular sublayers only)",
                  f"{SR.C1:.3f} × {SR.C2:.3f} × {q5:.1f} kPa × {sumIE:.3e} m³/kN = {SR.settlement * 1000:.1f} mm "
                  f"({len(SR.rows)} sublayers of {dz5:g} m; {SR.skipped_cohesive:.2f} m of clay left to consolidation)", rs)
        if SR.skipped_cohesive > 0:
            st.info(f"{SR.skipped_cohesive:.2f} m of cohesive soil lies inside the influence zone. Its settlement "
                    "is computed by consolidation below, not by Schmertmann.", icon=":material/info:")
        if SR.rows:
            sdf_ = pd.DataFrame(SR.rows)
            sdf_["ds"] = sdf_["ds"] * 1000
            sdf_.columns = ["z below base (m)", "Depth (m bgl)", "Layer", "Iz (–)", "E (kPa)", "Δs (mm)", "Note"]
            fgI = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("Iz (–)", "E (kPa)"))
            fgI.add_trace(go.Scatter(x=sdf_["Iz (–)"], y=sdf_["z below base (m)"], name="Iz", fill="tozerox", mode="lines+markers",
                                     marker=dict(size=4, color=ui.EMERALD),
                                     line=dict(color=ui.EMERALD, width=3), fillcolor="rgba(52,211,153,0.15)"), 1, 1)
            fgI.add_trace(go.Scatter(x=sdf_["E (kPa)"], y=sdf_["z below base (m)"], name="E", line_shape="hv", mode="lines+markers",
                                     marker=dict(size=4, color=ui.GOLD),
                                     line=dict(color=ui.GOLD, width=3)), 1, 2)
            fgI.update_yaxes(autorange="reversed", title_text="z below base (m)", row=1, col=1)
            fgI.update_layout(showlegend=False)
            hl5 = picked(chart(fgI, 340, key="ch_iz", select=True))
            with st.expander("Sublayer table", icon=":material/table_rows:", expanded=hl5 is not None):
                if hl5 is not None:
                    st.caption(f"Selected sublayer at z = {sdf_.iloc[hl5, 0]:.3f} m below the base (row highlighted).")
                show_df(sdf_.round(4), "schmertmann_sublayers", highlight=hl5, hide_index=True, width="stretch")

    with ui.card():
        ui.section("P5·b", "Cohesive layers: one-dimensional consolidation",
                   "NC and OC clay in sublayers no thicker than 0.5 m (Terzaghi).", anchor="p5b")
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
            f_con = ("NC: s = C<sub>c</sub>H/(1+e<sub>0</sub>) · log(σ′<sub>f</sub>/σ′<sub>0</sub>)<br>"
                     "OC, σ′<sub>f</sub> ≤ σ′<sub>p</sub>: s = C<sub>s</sub>H/(1+e<sub>0</sub>) · log(σ′<sub>f</sub>/σ′<sub>0</sub>)<br>"
                     "OC, σ′<sub>f</sub> &gt; σ′<sub>p</sub>: s = C<sub>s</sub>H/(1+e<sub>0</sub>) · log(σ′<sub>p</sub>/σ′<sub>0</sub>) "
                     "+ C<sub>c</sub>H/(1+e<sub>0</sub>) · log(σ′<sub>f</sub>/σ′<sub>p</sub>)")
            cols = st.columns(max(1, len(CR.per_layer)))
            for col, (k, v) in zip(cols, CR.per_layer.items()):
                rws = [r_ for r_ in CR.rows if k.startswith(r_.layer)]
                r0 = rws[0] if rws else None
                cases = {c: sum(1 for r_ in rws if r_.case == c) for c in ("NC", "OC (sf <= sp)", "OC (sf > sp)")}
                ex = (f"<br>Top sublayer: H = {r0.H:.3f} m, σ′<sub>0</sub> = {r0.sigma0:.1f}, σ′<sub>p</sub> = {r0.sigma_p:.1f}, "
                      f"Δσ = {r0.d_sigma:.1f} kPa ({esc(r0.case)}) → s = {r0.s * 1000:.2f} mm" if r0 else "")
                ui.metric(col, f"{k} (mm)", f"{v * 1000:.1f}", f_con,
                          f"{len(rws)} sublayers, stress by {smeth}; NC: {cases['NC']}, OC (σ′<sub>f</sub> ≤ σ′<sub>p</sub>): "
                          f"{cases['OC (sf <= sp)']}, OC (σ′<sub>f</sub> &gt; σ′<sub>p</sub>): {cases['OC (sf > sp)']}; "
                          f"Σs = {v * 1000:.1f} mm{ex}",
                          "Terzaghi 1-D consolidation; Das, Principles of Geotechnical Engineering (consolidation settlement)")
        else:
            st.info("No cohesive layer with Cc > 0 lies below the base.", icon=":material/info:")

    lay_sc = []
    if CR.rows:
        with ui.card():
            ui.section("P5·c", "Time–settlement", "Terzaghi 1-D consolidation. Drainage is selected per layer.", anchor="p5c")
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
        lim = c4.number_input("Permissible total (mm), IS 1904 value", 0.0, 500.0, 75.0, 5.0)
        ui.metric(c1, "Sand, Schmertmann (mm)", f"{SR.settlement * 1000:.1f}", "S<sub>i</sub> from P5·a",
                  f"{SR.settlement * 1000:.1f} mm", "Schmertmann, Hartman &amp; Brown (1978)")
        ui.metric(c2, "Consolidation (mm)", f"{CR.total * 1000:.1f}", "S<sub>c</sub> = Σ over cohesive layers (P5·b)",
                  " + ".join(f"{v * 1000:.1f}" for v in CR.per_layer.values()) + f" = {CR.total * 1000:.1f} mm"
                  if CR.per_layer else "No cohesive layer below the base", "Terzaghi 1-D consolidation")
        ui.metric(c3, "Total (mm)", f"{total * 1000:.1f}", "S = S<sub>i</sub> + S<sub>c</sub>",
                  f"{SR.settlement * 1000:.1f} + {CR.total * 1000:.1f} = {total * 1000:.1f} mm "
                  f"({'≤' if total * 1000 <= lim else '&gt;'} permissible {lim:g} mm)",
                  "Permissible values: IS 1904:1986 Table 1")
        st.markdown(f"Total settlement against the permissible value &nbsp;{ui.pill(total * 1000 <= lim, 'WITHIN LIMIT', 'EXCEEDS LIMIT')}",
                    unsafe_allow_html=True)

# ------------------------------------------------------------- Liquefaction
LR = []
with tabs[5]:
    with ui.card():
        ui.section("Extra", "Liquefaction triggering: IS 1893 (Part 1):2016 Annex F",
                   "Not part of the P1–P5 brief. It is included because shallow saturated sands in high "
                   "seismic zones must be screened. CSR = 0.65 (a_max/g)(σv/σ′v) r_d; CRR from (N1)60cs "
                   "(Youd et al. 2001); FS = CRR·MSF/CSR. Click a point to highlight its row.", anchor="liq")
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
            hl_liq = None
            with cR:
                if len(fin):
                    fg = go.Figure(go.Scatter(x=fin["FS_L"], y=fin["Depth (m)"], mode="markers+lines", name="FS_L",
                                              line=dict(color=ui.EMERALD, width=3),
                                              marker=dict(size=11, color=[ui.DANGER if v < 1 else ui.EMERALD
                                                                          for v in fin["FS_L"]])))
                    fg.add_vline(x=1.0, line_dash="dash", line_color=ui.GOLD)
                    fg.update_yaxes(autorange="reversed", title="Depth (m)")
                    fg.update_layout(xaxis_title="FS against liquefaction (–)")
                    pi_ = picked(chart(fg, 320, key="ch_liq", select=True))
                    hl_liq = fin.index[pi_] if pi_ is not None and pi_ < len(fin) else None
            show_df(ldf_.round(3), "liquefaction", highlight=hl_liq, hide_index=True, width="stretch")
        else:
            st.info("No SPT records in the profile yet.", icon=":material/info:")

# ----------------------------------------------------------------- Sources
with tabs[6]:
    with ui.card():
        src = ROOT / "SOURCES.md"
        st.markdown(src.read_text(encoding="utf-8") if src.exists() else "See README.md")

# ------------------------------------------------------------- My projects (optional sign-in)
FOOT_KEYS = ["in_shape", "in_B", "in_L", "in_Df", "in_P", "in_MB", "in_ML", "in_alpha"]
with acct_box:
    with st.expander("My projects", icon=":material/cloud:", expanded=False):
        if not acc.auth_configured():
            st.caption("Guest mode. Sign-in is not configured on this server; use Download Project (P1) "
                       "to keep a copy of your inputs.")
        elif not acc.user_email():
            st.caption("Sign in to save projects to your account. Everything works without signing in.")
            st.button("Sign In with Google", on_click=st.login, icon=":material/login:", width="stretch")
        else:
            email = acc.user_email()
            st.caption(f"Signed in as {email}")
            try:
                nm = st.text_input("Project name", D.get("name", "Untitled"), key="acct_name")
                if st.button("Save Current Project", type="primary", width="stretch", icon=":material/save:"):
                    data = {**D, **profile.to_dict(),
                            "footing": {k: st.session_state[k] for k in FOOT_KEYS if k in st.session_state}}
                    acc.save_project(email, nm, data)
                    st.toast(f"Saved “{nm}”", icon=":material/check_circle:")
                saved = acc.list_projects(email)
                if saved:
                    labels = {p_["id"]: f'{p_["name"]} · {p_["updated"][:16].replace("T", " ")}' for p_ in saved}
                    pick_ = st.selectbox("Saved projects", list(labels), format_func=labels.get, key="acct_pick")
                    c1, c2 = st.columns(2)
                    if c1.button("Open", width="stretch", icon=":material/folder_open:"):
                        d_ = acc.load_project(email, pick_)
                        if d_:
                            st.session_state["_pending_footing"] = d_.pop("footing", {})
                            load_into_state(d_)
                            st.rerun()
                    with c2.popover("Delete", icon=":material/delete:", width="stretch"):
                        st.caption(f"Delete “{labels[pick_]}”? This cannot be undone.")
                        if st.button("Delete Permanently", type="primary", width="stretch"):
                            acc.delete_project(email, pick_)
                            st.rerun()
                else:
                    st.caption("No saved projects yet.")
            except Exception as ex:  # noqa: BLE001
                st.error(f"Project storage is unavailable ({type(ex).__name__}). Check that Firestore is "
                         "enabled for this project.", icon=":material/error:")
            st.button("Sign Out", on_click=st.logout, width="stretch", icon=":material/logout:")

# ------------------------------------------------------------- summary strip
def _delta(key, val, unit="", digits=0):
    """Change chip text for a tile whose value differs from the previous run ('' if unchanged)."""
    prev = st.session_state.get("_tiles_prev", {})
    if key not in prev or prev[key] == val:
        return ""
    if isinstance(val, (int, float)) and isinstance(prev[key], (int, float)):
        d = val - prev[key]
        return f"{d:+.{digits}f} {unit}".strip() if round(d, digits) != 0 else ""
    return "changed"


with summary:
    cur, items = {}, []
    dims = (f"{B:.2f} m wide" if shape == "Strip" else f"Ø {B:.2f} m" if shape == "Circle"
            else f"{B:.2f} × {(L or B):.2f} m")
    foot = f"{shape} {dims}"
    mom = f" · M {MB:g}/{ML:g} kN·m" if (MB or ML) else ""
    cur["footing"] = foot + f"|{Df}|{P}|{MB}|{ML}|{alpha}"
    items.append(ui.tile("Footing", foot, sub=f"Df {Df:.2f} m · P {P:g} kN{'/m' if shape == 'Strip' else ''}{mom}",
                         ic="activity", text=True, state="gold",
                         inputs=["in_shape", "in_B", "in_L", "in_Df", "in_P", "in_MB", "in_ML", "in_alpha"],
                         delta=_delta("footing", cur["footing"])))
    if R is not None:
        lay_name = R.layer.split("(")[0].strip()[:34]
        cur["layer"] = lay_name
        items.append(ui.tile("Founding layer", lay_name, sub=f"φ {R.phi:.1f}° · W′ {R.W:.2f}",
                             ic="layers", text=True, go_to=(2, "p3a", "P3 Bearing · inputs resolved from the profile"),
                             delta=_delta("layer", lay_name)))
        cur["qns"] = round(R.q_ns)
        items.append(ui.tile("Net safe capacity", f"{R.q_ns:.0f}", "kPa", f"q_nu {R.q_nu:.0f} kPa · FS {FS:g}",
                             ic="gauge", state="gold", go_to=(2, "p3c", "P3 Bearing · capacity vs applied pressure"),
                             delta=_delta("qns", cur["qns"], "kPa")))
        if R.q_net_applied is not None:
            cur["qnet"] = round(R.q_net_applied)
            items.append(ui.tile("Net applied", f"{R.q_net_applied:.0f}", "kPa",
                                 "Bearing check passes" if R.ok else "Bearing check fails",
                                 ic="check" if R.ok else "x", state="pass" if R.ok else "fail",
                                 go_to=(2, "p3c", "P3 Bearing · capacity vs applied pressure"),
                                 delta=_delta("qnet", cur["qnet"], "kPa")))
    cur["settle"] = round(total * 1000)
    items.append(ui.tile("Total settlement", f"{total * 1000:.0f}", "mm",
                         f"sand {SR.settlement * 1000:.0f} · clay {CR.total * 1000:.0f} mm", ic="arrow-down",
                         state="pass" if total * 1000 <= lim else "fail",
                         go_to=(4, "p5d", "P5 Settlement · summary"), delta=_delta("settle", cur["settle"], "mm")))
    fs_vals = [r.FS for r in LR if math.isfinite(r.FS)]
    if fs_vals:
        mfs = min(fs_vals)
        cur["liq"] = round(mfs, 2)
        items.append(ui.tile("Liquefaction, min FS", f"{mfs:.2f}", "", "IS 1893 Annex F",
                             ic="waves", state="pass" if mfs >= 1 else "fail",
                             go_to=(5, "liq", "Liquefaction check"), delta=_delta("liq", cur["liq"], "", 2)))
    ui.tiles(items, intro="_tiles_prev" not in st.session_state)
    st.session_state["_tiles_prev"] = cur
