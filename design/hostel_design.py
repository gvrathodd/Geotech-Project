"""Hostel foundation design (Group 1) using the geotech package.

Run:  python design/build_inputs.py && python design/hostel_design.py
Outputs go to design/out/ (CSV tables, PNG figures, summary.json).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from geotech import bearing as bc  # noqa: E402
from geotech import liquefaction as liq  # noqa: E402
from geotech import settlement as se  # noqa: E402
from geotech import stress as stz  # noqa: E402
from geotech.profile import SoilProfile  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
OUT = ROOT / "design" / "out"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- inputs
G = 1  # group number
LAM = 1 + G / 100  # load factor from the brief
DF = 1.5  # m, minimum founding depth
FS = 3.0
GAMMA_FILL = 20.0  # kN/m3 (D5)
MODE = "auto"  # D3
C4_M = 50.0  # kN*m acting east-west (assumption sent to the professor)
C4_LB = 1.2  # L/B of the C4 rectangle, L along east-west
ROUND = 0.1  # practical size increment, m
# IS 1904:1986 Table 1 - multistoreyed RC framed building with panel walls, isolated footings (D12)
LIM_TOTAL = 75.0  # mm (plastic clay)
LIM_TOTAL_SAND = 60.0  # mm (sand / hard clay)
LIM_DIFF = 0.002  # x L
LIM_ANG = 1 / 500
SPAN = 5.0  # m
# Liquefaction (D8, D13, D16)
AMAX, MW = 0.36, 8.0

PROF = {bh: SoilProfile.from_dict(json.loads((ROOT / "examples" / f"{bh}.json").read_text()))
        for bh in ("BH-1", "BH-2", "BH-3")}
FINES = {bh: json.loads((ROOT / "examples" / f"{bh}.json").read_text()).get("fines", {}) for bh in PROF}

LINES = list(range(1, 8))  # west -> east, x = (line-1)*5
ROWS = ["A", "B", "C", "D"]  # y = index*5


def zone(line: int) -> str:
    return "BH-2" if line <= 2 else ("BH-1" if line <= 5 else "BH-3")


def ctype(r: str, n: int) -> str:
    if (r in "AD") and n in (1, 7):
        return "Corner"
    if r in "AD" or n in (1, 7):
        return "Edge"
    return "Interior"


BASE_P = {"Corner": 650.0, "Edge": 1000.0, "Interior": 1450.0}


def ceil_to(x, s=ROUND):
    return math.ceil(round(x / s, 6)) * s


# ------------------------------------------------------- 1. footing sizes
def size_all():
    cols = []
    cache = {}
    for n in LINES:
        for r in ROWS:
            name = f"{r}{n}"
            t = ctype(r, n)
            P = BASE_P[t] * LAM
            bh = zone(n)
            prof = PROF[bh]
            if name == "C4":
                key = ("C4", bh)
                if key not in cache:
                    Rs = bc.size_footing(prof, "Rectangle", P, DF, C4_LB, MB=0.0, ML=C4_M, FS=FS, mode=MODE,
                                         gamma_fill=GAMMA_FILL, step=0.05)
                    Bp = ceil_to(Rs.B)
                    cache[key] = (Bp, ceil_to(Bp * C4_LB))
                B, L = cache[key]
                R = bc.bearing_capacity(prof, "Rectangle", B, L, DF, P=P, ML=C4_M, FS=FS, mode=MODE,
                                        gamma_fill=GAMMA_FILL)
                shape = "Rectangle"
            else:
                key = (t, bh)
                if key not in cache:
                    Rs = bc.size_footing(prof, "Square", P, DF, FS=FS, mode=MODE, gamma_fill=GAMMA_FILL, step=0.05)
                    cache[key] = (ceil_to(Rs.B), None)
                B, _ = cache[key]
                L = B
                R = bc.bearing_capacity(prof, "Square", B, None, DF, P=P, FS=FS, mode=MODE, gamma_fill=GAMMA_FILL)
                shape = "Square"
            wl = bc.weak_layer_check(prof, R.B_eff, R.L_eff, DF, R.q_net_applied, FS)
            cols.append(dict(col=name, line=n, row=r, type=t + (" (eccentric)" if name == "C4" else ""),
                             zone=bh, x=(n - 1) * SPAN, y=ROWS.index(r) * SPAN, P=P, M=C4_M if name == "C4" else 0.0,
                             shape=shape, B=B, L=L, phi=R.phi, mode=R.mode_used, W=R.W, q=R.q,
                             Nc=R.general.Nc, Nq=R.general.Nq, Ng=R.general.Ng,
                             sc=R.sc, sq=R.sq, sg=R.sg, dc=R.dc, dq=R.dq, dg=R.dg,
                             q_nu=R.q_nu, q_ns=R.q_ns, q_net=R.q_net_applied, q_gross=R.q_gross_applied,
                             bc_ok=R.ok, eL=R.eL, B_eff=R.B_eff, L_eff=R.L_eff,
                             weak_layer=(wl.layer if wl else ""), weak_z=(wl.z_top if wl else np.nan),
                             weak_ds=(wl.delta_sigma if wl else np.nan), weak_FS=(wl.FS if wl else np.nan),
                             weak_ok=(wl.ok if wl else True)))
    return pd.DataFrame(cols)


# ------------------------------------------------------- 2. settlements
def settlements(df: pd.DataFrame, interaction=True):
    foot = [dict(x=r.x, y=r.y, B=(r.L if r.shape == "Rectangle" else r.B),  # L of C4 along x (east-west)
                 L=(r.B if r.shape == "Rectangle" else r.B), Df=DF, q=r.q_net) for r in df.itertuples()]
    out = []
    for i, r in enumerate(df.itertuples()):
        prof = PROF[r.zone]
        Lr = r.L if r.shape == "Rectangle" else None
        sch = se.schmertmann(prof, r.shape, r.B, Lr, DF, r.q_net, t_years=0.1, dz=0.05)
        if interaction:
            fn = (lambda z, x=r.x, y=r.y: stz.group_stress(foot, x, y, z))
        else:
            fn = se.footing_stress_fn("Boussinesq centre", r.q_net, r.shape, r.B, Lr, DF)
        con = se.consolidation(prof, fn, DF, 0.5)
        clay = con.layers[0]
        H = clay.bottom - clay.top
        out.append(dict(col=r.col, row=r.row, line=r.line, s_imm=sch.settlement * 1000, s_con=con.total * 1000,
                        s_tot=(sch.settlement + con.total) * 1000,
                        t90=se.time_for_U(0.9, H, clay.cv, "Double"),
                        ds_clay_top=fn(clay.top + 0.25), ds_clay_mid=fn((clay.top + clay.bottom) / 2)))
    return pd.DataFrame(out)


def differential(df: pd.DataFrame, s_col="s_tot"):
    pos = {(r.row, r.line): getattr(r, s_col) for r in df.itertuples()}
    rows = []
    for r in ROWS:
        for n in LINES[:-1]:
            a, b = pos[(r, n)], pos[(r, n + 1)]
            rows.append(dict(pair=f"{r}{n}-{r}{n + 1}", d=abs(a - b), ang=abs(a - b) / (SPAN * 1000)))
    for n in LINES:
        for k in range(3):
            a, b = pos[(ROWS[k], n)], pos[(ROWS[k + 1], n)]
            rows.append(dict(pair=f"{ROWS[k]}{n}-{ROWS[k + 1]}{n}", d=abs(a - b), ang=abs(a - b) / (SPAN * 1000)))
    d = pd.DataFrame(rows)
    d["d_ok"] = d["d"] <= LIM_DIFF * SPAN * 1000 + 1e-9
    d["ang_ok"] = d["ang"] <= LIM_ANG + 1e-12
    return d


# ------------------------------------------------------- 3. raft option
def raft(total_P: float, proj=0.5):
    Br, Lr = 15 + 2 * proj, 30 + 2 * proj  # B across (y), L along (x)
    A = Br * Lr
    res = []
    q_nets = {}
    for bh, prof in PROF.items():
        sig = prof.sigma_tot(DF)
        q_nets[bh] = (total_P + GAMMA_FILL * A * DF - sig * A) / A
    q_net = float(np.mean(list(q_nets.values())))
    # flexible raft: Boussinesq under each column point
    for n in LINES:
        for r in ROWS:
            x, y = (n - 1) * SPAN, ROWS.index(r) * SPAN
            prof = PROF[zone(n)]
            xc, yc = 15.0, 7.5  # raft centre
            fn = (lambda z, x=x, y=y: stz.rect_point(q_net, Lr, Br, x - xc, y - yc, z - DF) if z > DF else q_net)
            con = se.consolidation(prof, fn, DF, 0.5)
            res.append(dict(col=f"{r}{n}", row=r, line=n, zone=zone(n), s_con=con.total * 1000))
    return pd.DataFrame(res), q_net, q_nets, (Br, Lr)


# ------------------------------------------------------- 4. liquefaction
def liquefaction_all():
    rows = []
    for bh, prof in PROF.items():
        for r in liq.liquefaction(prof, AMAX, MW, energy_ratio=60, borehole_mm=150, fines=FINES[bh]):
            d = r.__dict__.copy()
            d["BH"] = bh
            rows.append(d)
    return pd.DataFrame(rows)


# ------------------------------------------------------- 5. piles (PF) and CPRF check
PILE_D = 0.75  # m (D19)
SOCKET = 2.5  # m into the very dense gravel (> 3D = 2.25 m)
CUTOFF = DF  # pile cap underside at 1.5 m
PILE_FS = 2.5  # IS 2911 static formula factor of safety
PHI_GW = 40.0  # deg, very dense sandy gravel with cobbles (SPT refusal)
NQ_IS2911 = None  # Nq read by the group from IS 2911 Fig. 1 for phi = 40 deg (None -> cross-check skipped)
EP = 5000 * math.sqrt(30) * 1000  # kPa, IS 456 Ec = 5000 sqrt(fck), M30
ES_GW = 100000.0  # kPa, very dense gravel
CAP_T, GC = 1.0, 25.0  # cap thickness (m), RCC unit weight (kN/m3)
BETA_NSF = 0.25  # dragload in reconsolidating liquefied sand (beta), conservative


def cap_weight(n):
    s = 3 * PILE_D
    a = s + PILE_D + 0.3
    if n == 2:
        return a * (PILE_D + 0.3) * CAP_T * GC, (a, PILE_D + 0.3)
    if n == 3:
        b = 0.866 * s + PILE_D + 0.3
        return a * b * CAP_T * GC, (a, b)
    side = (math.ceil(math.sqrt(n)) - 1) * s + PILE_D + 0.3
    return side * side * CAP_T * GC, (side, side)


def piles(L: pd.DataFrame, df: pd.DataFrame, raft_df: pd.DataFrame, raft_q: float):
    from geotech import piles as pl

    zone_res = {}
    for bh, prof in PROF.items():
        gw = next(l for l in prof.layers if l.description.startswith("GW"))
        tip = gw.top + SOCKET
        ignore = [(0.0, gw.top)]  # shaft neglected above the gravel (liquefiable sand, soft clay)
        ro = pl.reese_oneill(prof, PILE_D, tip, CUTOFF, 100.0, lambda z: 100.0, ignore, PILE_FS)
        isr = None
        if NQ_IS2911:
            isr = pl.is2911_static(prof, PILE_D, tip, CUTOFF, PHI_GW, NQ_IS2911, ignore_shaft=ignore, FS=PILE_FS)
        # dragload from liquefied layers (layers with FS_L < 1) reconsolidating after shaking
        liq_layers = {r.layer for r in L[(L.BH == bh) & (L.FS < 1)].itertuples()}
        nsf = 0.0
        for l in prof.sorted_layers():
            if l.description in liq_layers:
                n = 20
                h = l.thickness / n
                for k in range(n):
                    z = l.top + (k + 0.5) * h
                    if z > CUTOFF:
                        nsf += BETA_NSF * prof.sigma_eff(z) * math.pi * PILE_D * h
        Qa_net = ro.Qa - nsf
        zone_res[bh] = dict(tip=tip, gw_top=gw.top, Qp=ro.Qp, Qs=ro.Qs, Qu=ro.Qu, Qa=ro.Qa, NSF=nsf,
                            Qa_net=Qa_net, liq_layers=sorted(liq_layers),
                            is2911_Qu=(isr.Qu if isr else None), is2911_Qa=(isr.Qa if isr else None),
                            is2911_Qp=(isr.Qp if isr else None), is2911_Qs=(isr.Qs if isr else None))
    rows = []
    for r in df.itertuples():
        z = zone_res[r.zone]
        n = 2
        while True:
            Wc, dims = cap_weight(n)
            Ptot = r.P + Wc
            if Ptot / n <= z["Qa_net"] or n >= 9:
                break
            n += 1
        Qw = Ptot / n
        fp = z["Qp"] / z["Qu"]
        v = pl.vesic_settlement(Qw * fp, Qw * (1 - fp), PILE_D, z["tip"] - CUTOFF, EP, ES_GW, ES_GW,
                                L_shaft=SOCKET)
        Rs = n ** 0.5  # group settlement ratio (Fleming et al. 1992, exponent 0.5)
        s_grp = v["s"] * Rs * 1000
        rows.append(dict(col=r.col, row=r.row, line=r.line, zone=r.zone, P=r.P, n=n, cap=f"{dims[0]:.2f} x {dims[1]:.2f}",
                         W_cap=Wc, Q_per_pile=Qw, Qa_net=z["Qa_net"], util=Qw / z["Qa_net"], tip=z["tip"],
                         s_single=v["s"] * 1000, s_group=s_grp, s_tot=s_grp))
    P = pd.DataFrame(rows)
    dif = differential(P, "s_tot")
    # ---- CPRF (PDR) check for an interior column in each zone, long-term stiffness
    cprf = []
    for col in ("B2", "B4", "B6"):
        pr = P[P.col == col].iloc[0]
        s_raft = float(raft_df[raft_df.col == col].s_con.iloc[0]) / 1000
        Kr = raft_q * SPAN * SPAN / s_raft  # raft alone over the 5 x 5 m tributary area
        Kp = (pr.P + pr.W_cap) / (pr.s_group / 1000)
        res = pl.pdr(Kp, Kr, 0.8)
        cprf.append(dict(col=col, zone=pr.zone, Kr_MNm=Kr / 1000, Kp_MNm=Kp / 1000, Kpr_MNm=res["Kpr"] / 1000,
                         raft_share=res["raft_share"], s_pile_group_mm=pr.s_group,
                         s_cprf_mm=(pr.P + pr.W_cap) / res["Kpr"] * 1000))
    return zone_res, P, dif, pd.DataFrame(cprf)


# ------------------------------------------------------- figures
def fig_plan(df, s, fname, title, val="s_tot", unit="mm"):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    m = df.merge(s, on="col")
    for r in m.itertuples():
        bx = r.L if r.shape == "Rectangle" else r.B
        by = r.B
        ax.add_patch(plt.Rectangle((r.x - bx / 2, r.y - by / 2), bx, by, fill=False, lw=1))
        ax.text(r.x, r.y + 0.35, r.col, ha="center", fontsize=8, weight="bold")
        ax.text(r.x, r.y - 0.55, f"{getattr(r, val):.0f} {unit}", ha="center", fontsize=8)
    for xb, lbl in [(0, "BH-2 zone"), (12.5, "BH-1 zone"), (27.5, "BH-3 zone")]:
        pass
    ax.axvline(7.5, ls=":", c="grey")
    ax.axvline(22.5, ls=":", c="grey")
    ax.text(2.5, 17.3, "BH-2 zone (lines 1-2)", ha="center", fontsize=9)
    ax.text(15, 17.3, "BH-1 zone (lines 3-5)", ha="center", fontsize=9)
    ax.text(27.5, 17.3, "BH-3 zone (lines 6-7)", ha="center", fontsize=9)
    ax.set_xlim(-3, 33)
    ax.set_ylim(-3, 18.5)
    ax.set_aspect("equal")
    ax.set_xticks([(n - 1) * 5 for n in LINES], [str(n) for n in LINES])
    ax.set_yticks([0, 5, 10, 15], ROWS)
    ax.set_title(title)
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=160)
    plt.close(fig)


def fig_profiles():
    fig, axs = plt.subplots(1, 3, figsize=(11, 6), sharey=True)
    colors = {"Granular": "#e8c872", "Cohesive": "#7fa7d9"}
    for ax, bh in zip(axs, ["BH-2", "BH-1", "BH-3"]):
        p = PROF[bh]
        for l in p.sorted_layers():
            ax.add_patch(plt.Rectangle((0, l.top), 1, l.thickness, color=colors[l.soil_type], ec="k"))
            lbl = l.description.split(" ")[0]
            extra = (f"φ′={l.phi_eff:.1f}°, E={l.E / 1000:.0f} MPa" if l.soil_type == "Granular"
                     else f"Cc={l.Cc}, cu={l.cu:.0f} kPa")
            ax.text(0.5, (l.top + l.bottom) / 2, f"{lbl}\n{extra}", ha="center", va="center", fontsize=7.5)
        ax.axhline(p.gwt_design, c="b", ls="--", lw=1.2)
        ax.axhline(p.gwt_measured, c="b", lw=0.8)
        ax.axhline(DF, c="r", lw=1.5)
        ax.text(1.02, p.gwt_design, f"Design WT {p.gwt_design} m", fontsize=7, color="b", va="center")
        ax.text(1.02, p.gwt_measured, f"Meas. WT {p.gwt_measured} m", fontsize=7, color="b", va="center")
        ax.text(1.02, DF, "Df 1.5 m", fontsize=7, color="r", va="center")
        for s in p.spt:
            ax.text(-0.05, s.depth, (">100" if s.refusal else f"{s.N:g}"), ha="right", fontsize=7)
        ax.set_xlim(-0.35, 1.6)
        ax.set_title(bh)
        ax.set_xticks([])
    axs[0].set_ylim(15, 0)
    axs[0].set_ylabel("Depth below ground level (m)")
    fig.suptitle("Design soil profiles (parameters adopted)", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "profiles.png", dpi=160)
    plt.close(fig)


def fig_time(df, s):
    fig, ax = plt.subplots(figsize=(7, 4))
    tt = np.linspace(0, 15, 300)
    for colname in ["A1", "C4", "D7"]:
        r = df[df.col == colname].iloc[0]
        ss = s[s.col == colname].iloc[0]
        clay = next(l for l in PROF[r.zone].layers if l.soil_type == "Cohesive")
        tot, _ = se.time_settlement([(ss.s_con / 1000, clay.thickness, clay.cv, "Double")], tt)
        ax.plot(tt, (tot * 1000 + ss.s_imm), label=f"{colname} ({r.zone})")
    ax.axhline(LIM_TOTAL, c="r", ls="--", lw=1, label=f"IS 1904 limit {LIM_TOTAL:.0f} mm")
    ax.invert_yaxis()
    ax.set_xlabel("Time after loading (years)")
    ax.set_ylabel("Settlement (mm)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "time_settlement.png", dpi=160)
    plt.close(fig)


def fig_stress(df):
    r = df[df.col == "C4"].iloc[0]
    fig, ax = plt.subplots(figsize=(5, 5))
    zs = np.linspace(0.1, 10, 100)
    B = r.B
    ax.plot([stz.rect_centre(r.q_net, r.B, r.L, z) for z in zs], zs, label="Boussinesq centre")
    ax.plot([stz.rect_corner(r.q_net, r.B, r.L, z) for z in zs], zs, label="Boussinesq corner")
    ax.plot([stz.two_to_one(r.q_net, "Rectangle", r.B, r.L, z) for z in zs], zs, label="2:1")
    ax.invert_yaxis()
    ax.set_xlabel("Δσz (kPa)")
    ax.set_ylabel("Depth below base (m)")
    ax.set_title(f"C4: {r.B:.1f} × {r.L:.1f} m, q_net = {r.q_net:.0f} kPa", fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "stress_C4.png", dpi=160)
    plt.close(fig)


def fig_liq(L):
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    for bh, g in L.groupby("BH"):
        g = g[np.isfinite(g.FS)]
        ax.plot(g.FS, g.depth, "o-", label=bh)
    ax.axvline(1.0, c="r", ls="--")
    ax.invert_yaxis()
    ax.set_xlabel("FS against liquefaction (–)")
    ax.set_ylabel("Depth (m)")
    ax.set_title(f"IS 1893 Annex F, a_max = {AMAX} g, Mw = {MW}", fontsize=9)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "liquefaction.png", dpi=160)
    plt.close(fig)


def main():
    df = size_all()
    s_int = settlements(df, True)
    s_iso = settlements(df, False)
    dif = differential(s_int)
    L = liquefaction_all()
    total_P = df.P.sum()
    R, rq, rqs, rdim = raft(total_P)
    dif_raft = differential(R.assign(s_tot=R.s_con), "s_tot")
    zres, PL, dif_p, cprf = piles(L, df, R, rq)
    PL.to_csv(OUT / "piles.csv", index=False)
    cprf.to_csv(OUT / "cprf.csv", index=False)
    (OUT / "pile_zones.json").write_text(json.dumps(zres, indent=2))
    print("PILE ZONES", json.dumps(zres, indent=1))
    print(PL.round(2).to_string())
    print("pile diff max", dif_p.d.max(), dif_p.ang.max())
    print(cprf.round(3).to_string())

    df.to_csv(OUT / "footings.csv", index=False)
    s_int.to_csv(OUT / "settlement_interaction.csv", index=False)
    s_iso.to_csv(OUT / "settlement_isolated.csv", index=False)
    dif.to_csv(OUT / "differential.csv", index=False)
    L.to_csv(OUT / "liquefaction.csv", index=False)
    R.to_csv(OUT / "raft.csv", index=False)

    fig_profiles()
    fig_plan(df, s_int, "plan_settlement.png", "Isolated footings – total settlement with interaction (mm)")
    fig_time(df, s_int)
    fig_stress(df)
    fig_liq(L)

    summ = dict(
        lam=LAM, total_P=total_P, n_cols=len(df),
        bc_all_ok=bool(df.bc_ok.all()), weak_all_ok=bool(df.weak_ok.all()),
        s_max=float(s_int.s_tot.max()), s_max_col=s_int.loc[s_int.s_tot.idxmax(), "col"],
        s_min=float(s_int.s_tot.min()),
        n_total_fail=int((s_int.s_tot > LIM_TOTAL).sum()),
        d_max=float(dif.d.max()), d_max_pair=dif.loc[dif.d.idxmax(), "pair"],
        ang_max=float(dif.ang.max()), n_diff_fail=int((~dif.d_ok).sum()), n_pairs=len(dif),
        raft_q_net=rq, raft_q_nets=rqs, raft_dim=rdim, raft_s_max=float(R.s_con.max()),
        raft_s_min=float(R.s_con.min()), raft_d_max=float(dif_raft.d.max()),
        raft_ang_max=float(dif_raft.ang.max()),
        liq_n_fail=int((L.FS < 1).sum()), liq_fail=L[L.FS < 1][["BH", "depth", "FS"]].round(2).values.tolist(),
    )
    summ.update(pile_d_max=float(dif_p.d.max()), pile_ang_max=float(dif_p.ang.max()),
                pile_s_max=float(PL.s_tot.max()))
    (OUT / "summary.json").write_text(json.dumps(summ, indent=2, default=str))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    sizes = df.groupby(["zone", "type"]).agg(B=("B", "first"), L=("L", "first"), P=("P", "first"),
                                             phi=("phi", "first"), W=("W", "first"), q_nu=("q_nu", "first"),
                                             q_ns=("q_ns", "first"), q_net=("q_net", "first"),
                                             weakFS=("weak_FS", "first")).round(2)
    print(sizes)
    print(df.merge(s_int, on="col")[["col", "zone", "type", "B", "q_net", "s_imm", "s_con", "s_tot", "t90"]]
          .merge(s_iso[["col", "s_con"]].rename(columns={"s_con": "s_con_iso"}), on="col").round(1).to_string())
    print(dif.sort_values("d", ascending=False).head(8).round(4).to_string())
    print(L[["BH", "depth", "N", "layer", "sigma_eff", "CSR", "N1_60cs", "CRR75", "MSF", "FS", "status"]]
          .round(3).to_string())
    print(R.round(1).to_string())
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
