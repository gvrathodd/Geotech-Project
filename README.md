# CE 402 Shallow Foundation Platform (Group 1)

A web platform for shallow-foundation design to Indian Standards, built for the CE 402
Geotechnical Engineering assignment at IIT Mandi. It accepts **any** layered soil profile and
footing. No site values are hard-coded; the hostel boreholes are provided only as example
input files in `examples/`.

**Live app:** <https://foundation-studio-237377681531.us-central1.run.app>

No sign-in is needed. Signing in with Google is optional and lets you save projects to your account ([privacy policy](https://foundation-studio-237377681531.us-central1.run.app/?page=privacy)).

## Modules

| Module | Scope |
|---|---|
| **P1 Soil profile** | Layered profile: depths, soil type, moist and saturated unit weights, c′, φ′, cu, E, Cc, Cs, e0, stress history (NC, OCR, POP or σ′p), cv, drainage. Separate measured and design water tables. Plots of strata, σv, u, σ′v and SPT N. |
| **P2 Parameter tools** | IS 2131:1981 SPT corrections with every step shown: overburden C_N = 0.77 log₁₀(20/p′), using the measured water table, then dilatancy for saturated fine or silty sand. Least-squares c′ and φ′ from direct shear. cu from UU tests. Cc, Cs, Casagrande σ′p and cv from the oedometer (kg/cm² → kPa, cm²/s → m²/yr). Cc and e0 correlations. |
| **P3 Bearing capacity** | IS 6403:1981 net ultimate and net safe bearing capacity for strip, square, rectangular and circular footings. General, local and interpolated shear. Shape, depth and inclination factors and the water-table factor W′, all displayed. Effective area for eccentric loads. Footing sizing and a soft-underlying-layer check. |
| **P4 Stress increase** | Boussinesq Δσz below the centre and the corner of a rectangle (by superposition) and the 2:1 method, plotted against depth. |
| **P5 Settlement** | Granular layers by the strain influence factor method (Schmertmann et al. 1978). 1-D consolidation of NC and OC clay in sublayers no thicker than 0.5 m. Time–settlement curve with user-selected drainage. |
| **Liquefaction (extra)** | IS 1893 (Part 1):2016 Annex F simplified procedure. See below. |

All quantities are in SI units (kN, kPa, m, mm), with the unit beside every input and output.
Every equation in `geotech/` carries a comment naming its source, and `SOURCES.md` lists them all.

### Why a liquefaction check was added

The brief lists P1–P5 and P8 only. The hostel site, however, is in seismic zone V, 25 m from a
perennial stream, with saturated loose silty sand (BH-3, N = 6) at the founding level.
IS 1893 (Part 1):2016 Annex F gives the procedure for screening such soils. The check gives
FS < 1 at footing level in all three boreholes, which is one of the main reasons the design
moves to piles. It works for any profile and does not change P1–P5.

## Hostel design (Group 1, λ = 1.01)

- **Isolated footings** at Df = 1.5 m satisfy IS 6403 bearing capacity (FS = 3), but they fail
  IS 1904:1986. Total settlement reaches 244 mm in the BH-3 zone (soft NC clay, with footing
  interaction), and the differential settlement is 182 mm across lines 5–6.
- **Raft:** 256 mm at BH-3. Rejected.
- **Combined piled raft:** by the PDR method the raft would carry only 1–6 % of the load over the
  clay zones. Rejected.
- **Adopted foundation:** 2 × Ø750 mm bored cast-in-situ piles per column, socketed 2.5 m into
  the very dense gravel (Reese & O'Neill 1989; IS 2911 Part 1/Sec 2). Settlement ≤ 13.5 mm and
  differential ≤ 3.9 mm.
- **Assumptions:** C4 is taken as P = 1464.5 kN with M = 50 kN·m acting east–west. Only P1–P5
  and P8 are implemented. The group leads on BH-1.

Full derivation in `docs/CE402_Group1_Report.docx`.

## How to run

```bash
pip install -r requirements.txt
streamlit run app.py              # the platform, http://localhost:8501
python -m pytest -q               # 18 benchmarks: IS 6403 Table 1, Newmark, Terzaghi U(Tv), hand calculations
python design/build_inputs.py     # raw borehole + lab data -> examples/BH-*.json (parameter derivation)
python design/hostel_design.py    # 28-column design: footings, settlement, liquefaction, raft, CPRF, piles
python docs/make_report.py        # Word report
```

To use a borehole in the app, open **Project file → Example profile** in the sidebar and load
`BH-1.json`, `BH-2.json` or `BH-3.json`. You can also start from **Blank profile** and enter any
profile.

## Code layout

```
geotech/      calculation core, one module per topic, every equation sourced
              profile · spt · lab · bearing · stress · settlement · liquefaction · piles
app.py        web interface (inputs and outputs only)
design/       hostel input builder and design script
examples/     BH-1, BH-2, BH-3 input files
tests/        benchmark tests
docs/         report, AI log, deployment notes
SOURCES.md    reference list for every equation
```

## Engineers of record

Group 1. AI tools were used for code and drafting (see `docs/AI_LOG.md`). Every equation,
parameter and number was checked by the group, and the group is responsible for them.

## Licence

MIT, see [LICENSE](LICENSE). The design results are for academic use; check them independently before using them for real construction.
