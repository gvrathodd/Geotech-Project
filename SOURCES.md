# Sources of every equation

Each equation in `geotech/` carries a comment naming its source. This table lists them by
module. Clause numbers are quoted as the group read them; check them against your own copy of
each code before relying on them.

## Indian Standards

| Code | Used for | Where in code |
|---|---|---|
| IS 2131:1981 – Method for standard penetration test for soils | Overburden correction C_N (Fig. 1 curve, C_N = 0.77 log₁₀(20/p′), p′ in kg/cm²), then dilatancy correction N″ = 15 + 0.5(N′ − 15) for saturated fine/silty sand with N′ > 15 | `spt.py` |
| IS 6403:1981 – Determination of bearing capacity of shallow foundations | Net ultimate bearing capacity (general and local shear, cl. 5.1.2), Table 1 factors Nc, Nq, Nγ, Table 2 shape factors, depth factors (cl. 5.1.2.2), inclination factors (cl. 5.1.2.3), water-table factor W′ (cl. 5.1.2.4), effective area for eccentric loads, net safe bearing capacity q_nu/FS | `bearing.py` |
| IS 1904:1986 – Design and construction of foundations in soils: general requirements | Table 1 permissible total settlement, differential settlement and angular distortion | `design/hostel_design.py` (limits), report §4 |
| IS 1893 (Part 1):2016 – Criteria for earthquake resistant design of structures | Zone factor Z (Table 3); Annex F liquefaction (simplified procedure) | `liquefaction.py` |
| IS 2911 (Part 1/Sec 2):2010 – Bored cast in-situ concrete piles | Annex B static formula (cross-check); factor of safety 2.5 | `piles.py` |
| IS 456:2000 – Plain and reinforced concrete | Ec = 5000√fck for pile shortening | `design/hostel_design.py` |
| IS 2720 (Part 15):1986 – Determination of consolidation properties | Casagrande construction for σ′p | `lab.py` |

## Papers and textbooks

| Reference | Used for | Where in code |
|---|---|---|
| Terzaghi, K. (1943), *Theoretical Soil Mechanics* – effective stress principle; 1-D consolidation theory | σ′ = σ − u; U(Tv) series U = 1 − Σ 2/M² e^(−M²Tv); Tv = cv t/H²dr | `profile.py`, `settlement.py` |
| Das, B. M., *Principles of Geotechnical Engineering* (chapters on in-situ stresses, stress in a soil mass, consolidation, shear strength) | Consolidation settlement of NC/OC clay (three cases); Tv–U approximations; Newmark/Boussinesq rectangle and circle; Mohr–Coulomb; UU test | `settlement.py`, `stress.py`, `lab.py` |
| Das, B. M., *Principles of Foundation Engineering* (chapters on shallow-foundation settlement, drilled shafts, pile settlement) | 2:1 method; Reese & O'Neill drilled shafts; Vesic (1977) pile settlement; SPT correlations | `stress.py`, `piles.py`, `spt.py` |
| Boussinesq, J. (1885); Newmark, N. M. (1935) Univ. Illinois Eng. Expt. Station Bull. 338 | Point-load solution integrated over a rectangle (corner influence factor) | `stress.py` |
| Schmertmann, J. H., Hartman, J. P. & Brown, P. R. (1978) "Improved strain influence factor diagrams", *J. Geotech. Eng. Div.* ASCE 104(GT8), 1131–1135 | Iz diagram, Izp = 0.5 + 0.1√(Δp/σ′vp), C1, C2, E = 2.5qc / 3.5qc | `settlement.py`, `spt.py` |
| Peck, R. B., Hanson, W. E. & Thornburn, T. H. (1974) *Foundation Engineering*, 2nd ed. | C_N = 0.77 log₁₀(20/p′) (the IS 2131 Fig. 1 curve) | `spt.py` |
| Wolff, T. F. (1989) "Pile capacity prediction using parameter functions", ASCE GSP 23 | φ′ = 27.1 + 0.3N − 0.00054N² | `spt.py` |
| Robertson, P. K., Campanella, R. G. & Wightman, A. (1983) "SPT-CPT correlations", *J. Geotech. Eng.* 109(11) | qc/N ratios by grain size | `spt.py` |
| Stroud, M. A. (1974) "The standard penetration test in insensitive clays and soft rocks", Proc. ESOPT, Stockholm | cu = f₁N | `spt.py` |
| Terzaghi, K. & Peck, R. B. (1967) *Soil Mechanics in Engineering Practice*, 2nd ed. | Cc = 0.009(LL − 10) | `lab.py` |
| Skempton, A. W. (1944) "Notes on the compressibility of clays", QJGS 100 | Cc = 0.007(LL − 10), remoulded | `lab.py` |
| Casagrande, A. (1936) "The determination of the pre-consolidation load and its practical significance", Proc. 1st ICSMFE | σ′p construction | `lab.py` |
| Meyerhof, G. G. (1953) "The bearing capacity of foundations under eccentric and inclined loads", Proc. 3rd ICSMFE | Effective width B′ = B − 2e | `bearing.py` |
| Vesic, A. S. (1973) "Analysis of ultimate loads of shallow foundations", *JSMFD* ASCE 99(SM1) | Nγ = 2(Nq + 1) tan φ | `bearing.py` |
| Youd, T. L. et al. (2001) "Liquefaction resistance of soils: NCEER/NSF workshops", *JGGE* 127(10) | CSR, r_d, (N1)60cs, CRR7.5, C_N, C_R, C_B, fines corrections, MSF | `liquefaction.py` |
| Seed, H. B. & Idriss, I. M. (1971) "Simplified procedure for evaluating soil liquefaction potential", *JSMFD* 97(SM9) | CSR = 0.65 (a_max/g)(σv/σ′v) r_d | `liquefaction.py` |
| Reese, L. C. & O'Neill, M. W. (1989) *Drilled Shafts: Construction Procedures and Design Methods*, FHWA-IF-99-025 | Drilled shaft tip q_p = 57.5 N60 ≤ 4310 kPa; β method | `piles.py` |
| Vesic, A. S. (1977) *Design of Pile Foundations*, NCHRP Synthesis 42 | Pile settlement s_e1 + s_e2 + s_e3 | `piles.py` |
| Randolph, M. F. (1983) "Design of piled raft foundations", Cambridge Univ. CUED/D-Soils TR143; Poulos, H. G. (2001) "Piled raft foundations: design and applications", *Géotechnique* 51(2), 95–113 | PDR piled-raft stiffness and load share; conditions unfavourable for piled rafts | `piles.py`, report §8 |
| Fleming, W. G. K. et al. (1992) *Piling Engineering*, 2nd ed. | Group settlement ratio R_s = n^0.5 | `design/hostel_design.py` |
| Bowles, J. E. (1996) *Foundation Analysis and Design*, 5th ed. | Two-layer (weak underlying layer) projected-area check | `bearing.py` |
