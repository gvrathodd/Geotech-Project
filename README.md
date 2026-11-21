# CE 402 Shallow Foundation Platform (Group 1)

A web platform for shallow-foundation design to Indian Standards, built for the CE 402
(Geotechnical Engineering, IIT Mandi) assignment. It works with **any** layered soil profile
and footing; nothing about the hostel site is hard-coded. The site data ships only as
loadable example files in `examples/`.

**Live app:** <https://ce-402-geotech-project-g1.streamlit.app>  (free hosting sleeps when idle; if you see "Yes, get this app back up", click it and wait ~30 s)

## Modules

| Module | What it does |
|---|---|
| **P1 Soil profile** | Layered profile (depths, type, moist/saturated unit weight, c′, φ′, cu, E, Cc, Cs, e0, stress history, cv, drainage); measured **and** design water table; plot of strata, σv, u, σ′v and SPT N |
| **P2 Parameter tools** | IS 2131 SPT corrections, every step shown (overburden C_N, then dilatancy); least-squares c′, φ′ from direct shear; cu from UU; oedometer Cc, Cs, Casagrande σ′p and cv with kg/cm² → kPa and cm²/s → m²/yr conversion; Cc/e0 correlations |
| **P3 Bearing capacity** | IS 6403:1981 net ultimate and net safe bearing capacity for strip, square, rectangular and circular footings; general, local and interpolated shear; every shape, depth and inclination factor and W′ displayed; effective area for eccentric loads; footing sizing; soft-underlying-layer check |
| **P4 Stress increase** | Boussinesq Δσz below the centre and corner (superposition) and the 2:1 method, plotted against depth; stress at any point |
| **P5 Settlement** | Schmertmann et al. (1978) for granular layers; 1-D consolidation of NC/OC clay in sublayers ≤ 0.5 m; time–settlement curve with user-selected drainage |
| **Extra: Liquefaction** | IS 1893 (Part 1):2016 Annex F simplified procedure (see the justification below) |
| **P8 Code** | This repository; every equation is commented with its source (`SOURCES.md`) |

All inputs and outputs are in SI units, with the unit shown next to each value. Every table, including the editable input tables, has an **Export CSV** button. The files are UTF-8 so Excel shows σ′, φ′, ° and ³ correctly.

The theme (`ui/theme.py`) targets Streamlit 1.67, so `requirements.txt` pins that version to keep the deployed look identical.

### Working with the results

- **Result tiles** at the top update live. Click one to jump to the section its value comes from
  (that card glows); the **Footing** tile opens and highlights the footing and load inputs. Tiles
  whose value changed after an edit glow gold and show the change (e.g. `+2 kPa`).
- **Click any metric** (it shows `ƒx`) for its formula, your numbers substituted and the code clause
  or reference, which is useful for hand-checking.
- **Click a section badge** (P3·a, P5·d…) to copy a link straight to that section; opening the link
  restores the tab and position.
- **Click a point** on the SPT, stress, Iz/E, oedometer or liquefaction chart to highlight its table row.
- **On this tab** (sidebar) lists every card on the current tab; **Back to results** returns to the tiles.
- **Keyboard:** `1`–`7` switch tabs, `/` jumps to the footing inputs, `?` lists shortcuts, `Esc` closes a dialog.

### Why there is a liquefaction tab

The brief lists P1–P5 and P8 only. We added a liquefaction screen because the hostel site
is in seismic zone V, 25 m from a perennial stream, with saturated loose silty sand
(BH-3, N = 6) just below the design founding level. IS 1893 (Part 1):2016 Annex F gives the
procedure for assessing such soils, and the result (FS < 1 at footing level in all three
boreholes) is one of the main reasons the design moves to a pile foundation. The tab works
for any profile and does not affect P1–P5.

## Run it locally

```bash
git clone https://github.com/gvrathodd/Geotech-Project.git
cd Geotech-Project
pip install -r requirements.txt
streamlit run app.py          # opens http://localhost:8501
python -m pytest -q           # 18 benchmark tests (IS 6403 Table 1, Newmark, Terzaghi U, hand calcs)
```

In the app, open **Project file → Example profile** in the sidebar and load `BH-1.json`,
`BH-2.json` or `BH-3.json`, or click **Blank profile** and type a new one. Use
**Download project** to save a profile as JSON and **Upload** to reload it.

## Deploy (public URL, no installation for users): Google Cloud Run

In Google Cloud Shell (it has `gcloud` built in), run:

```bash
git clone https://github.com/gvrathodd/Geotech-Project.git && cd Geotech-Project
gcloud run deploy foundation-studio --source . --region us-central1 --allow-unauthenticated   --min-instances 0 --max-instances 1 --cpu 1 --memory 1Gi --timeout 900 --cpu-throttling
gcloud artifacts repositories set-cleanup-policies cloud-run-source-deploy   --location us-central1 --policy deploy/cleanup-policy.json
```

These settings keep the app inside Cloud Run's free tier. With minimum instances at 0 it scales to
zero when idle, and with maximum instances at 1 it can never run more than one copy. CPU is only
billed during requests, and the cleanup policy keeps only the newest images. Add a small budget
alert under Billing → Budgets & alerts.

## Reproduce the hostel design

```bash
python design/build_inputs.py    # raw borehole + lab data -> examples/BH-*.json (parameter derivation)
python design/hostel_design.py   # 28 columns: footings, settlement, liquefaction, raft, CPRF, piles
python docs/make_report.py       # Word report -> docs/CE402_Group1_Report.docx
```

The outputs (CSV tables, PNG figures and summary.json) are written to `design/out/`.

## Repository layout

```
app.py                 Streamlit interface (inputs/outputs only)
geotech/               calculation core – one module per topic, each equation sourced
  profile.py  spt.py  lab.py  bearing.py  stress.py  settlement.py  liquefaction.py  piles.py
tests/                 benchmark tests
examples/              BH-1/2/3 input files (generated by design/build_inputs.py)
design/                hostel design scripts and outputs
docs/                  AI log, report generator, report
SOURCES.md             reference list for every equation
```

## Engineers of record

Group 1. AI tools were used for code and drafting (see `docs/AI_LOG.md`). Every equation,
parameter and number was checked by the group, and the group is responsible for them.
