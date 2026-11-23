# AI Log – CE 402 Geotechnical Assignment (Group 1)

Format required by the brief: for each working session – date, tool, purpose, key prompts
(verbatim), and what we accepted, changed or rejected, with the reason.

> All AI sessions were run by Gaurav Girish Rathod (B24076) on behalf of Group 1. Every engineering
> decision was made by the group (the AI proposed options and asked); the web-design direction
> (inspiration, palette, layout feedback) was given by Gaurav.

---

## Session 1 – 21 Nov 2026 – Claude Code (Claude Opus 5.5, desktop app)

**Purpose:** Understand the brief, identify gaps, plan the work, start the platform.

### Prompts (verbatim)

1. "Analyze the project and tell me how to proceed" (with the assignment PDF attached)
2. "I have to complete it today / Lets write a mail to prof regarding this … First confirm that there is some issue and then I will do mail, mine is grp 1"
3. "Correct? Should i change x to y axis or z?" (with our edited e-mail draft)
4. "We can proceed on assumptions / Now lets finish the project in oneshot, Keep me asking for inputs wherever required and lets do it"
5. "Take our inputs too, remember we are enigneers? We have to write in Ai log and all soo you alone cant do it"

### AI output and our response

| # | AI output | Accepted / changed / rejected | Reason |
|---|-----------|-------------------------------|--------|
| 1 | Reading of the brief: two halves (platform P1–P5, P8 + hostel design), traps in the data (BH-1 N = 22 at 9.0 m struck a cobble; units kg/cm² and cm²/s; design vs measured water table; BH-3 soft clay near footing level) | Accepted | Checked against the PDF tables by the group |
| 2 | Claimed three gaps: C4 load missing (27 of 28 columns listed), P6/P7 missing, borehole allocation blank | Accepted only after verification | We asked the AI to *confirm* first; it extracted the PDF text layer and searched for "C4", "P6", "P7" – confirmed |
| 3 | E-mail draft to the professor | Changed | We rewrote the wording; we chose 50 kN·m for the C4 moment. AI pointed out "about X axis" is ambiguous (the brief defines no axes) and Z would be torsion; we changed it to "acting along the building length (east–west)" |
| 4 | Preliminary numbers (φ′ ≈ 30° soaked SM, cu ≈ 28.5 / 36 kPa, Cc ≈ 0.29, σ′p ≈ 110–125 kPa) | Pending verification | Verified: the platform's P2 tools and the benchmark tests reproduce these values |
| 5 | AI quoted IS 1904:1986 Table 1 limits "from memory" | **Corrected after checking the code** | IS 1904:1986 cl. 16.3.4 Table 1: the first values were the steel-structures row (audit A2) |
| 6 | Stack: Python + Streamlit, report in Word | Accepted (group decision) | Readable engineering code we can defend line by line; free public deployment |

### Assumptions adopted (sent to the professor)

- Group number g = 1 → λ = 1.01.
- C4: P = 1450 × 1.01 = 1464.5 kN, M = 50 kN·m acting east–west (e = 0.034 m).
- Only P1–P5 and P8 implemented. Group 1 leads on BH-1.

---

## Session 1 (contd.) – engineering decisions in the code

Each row is a choice the AI proposed in the code; the group decides.

| # | Item | AI proposal | Group decision | Reason |
|---|------|-------------|----------------|--------|
| D1 | SPT overburden correction | C_N = 0.77 log10(20/p′), p′ in kg/cm² (curve of IS 2131 Fig. 1 = Peck, Hanson & Thornburn 1974), capped at 2.0 | | |
| D2 | Dilatancy correction | Only for layers flagged fine/silty sand **and** below the *measured* water table, when N′ > 15 | | |
| D3 | Local vs general shear | User selects; "auto" interpolates linearly between local (φ ≤ 28°) and general (φ ≥ 36°) | **Accepted** (alternatives offered: N-based rule; user must choose) | IS 6403 gives no φ-based switch; interpolation avoids a jump in capacity at one φ value. Both results are still displayed.  |
| D4 | γ in the Nγ term and W′ | Bulk γ (γsat if water table within B below base) × W′ (IS 6403); q uses effective overburden – never γ′ and W′ together | | |
| D5 | Net applied pressure | q_net = (P + W_footing+backfill − σv,total(Df)·A)/A′, γ footing+backfill = 20 kN/m³ | **Accepted 20 kN/m³** (alternatives: P/A only; 24 kN/m³) | Average of RCC (25) and compacted backfill (~18); editable in the app |
| D6 | Schmertmann | E entered per layer; Iz shape interpolated between L/B = 1 and 10; clay layers skipped (done by consolidation) | | |
| D7 | Consolidation σ′0 | Uses the design water table | **Accepted – design (highest, August)** (alternatives: measured; mean of Aug & May) | Lowest σ′0 gives the largest settlement (conservative); consistent with the bearing check |
| D8 | Liquefaction (beyond the brief) | Add IS 1893 (Part 1):2016 Annex F simplified procedure | **Accepted – library + app tab + design check** (asked twice; confirmed "with proper justification in report, readme and wherever else needed") | Zone V, stream 25 m away, loose saturated silty sand in BH-3 (N = 6) |
| D9 | Clay stress history | POP = 37 kPa (BH-1 σ′p 116.6 − σ′v0 79.5 kPa at 7.225 m) for BH-1/BH-2; NC for BH-3 | **Accepted** (alternatives: POP everywhere; NC everywhere) | BH-3 clay is the softest (N = 4–6), near the stream, no undisturbed sample |
| D10 | Sand φ′ | AI recommended lab φ′ (soaked DS: SM 30.0°, SP 34.4°) for BH-1/2 and SPT for BH-3 | **Changed by group: SPT correlation (Wolff 1989) everywhere, c′ = 0** | Lab specimens were remoulded (one BH-1 sample); SPT exists at every borehole and captures the loose state of BH-3 Lab values kept as a cross-check (SM: SPT 32.3–33.0° vs lab 30.0°) |
| D11 | Sand E (Schmertmann) | E = 2.5 qc, qc/N = 0.4 MPa (SM), 0.5 MPa (SP) on corrected N | **Accepted** | Robertson et al. (1983) ranges |
| D12 | IS 1904 limits | Multistoreyed RC framed building with panel walls, isolated footings: 75 mm (plastic clay), 0.002L, 1/500 | **Accepted – verified in IS 1904:1986 cl. 16.3.4, Table 1, row (iii)(a)** | RC frame with masonry infill = panel walls; clay governs settlement |
| D13 | a_max for liquefaction | Z = 0.36 | **Accepted** | Conservative; hostel = important occupancy |
| D14 | BH-1 N = 22 at 9.0 m | Exclude | **Accepted** | Sampler struck a cobble, gravel recovered; N = 5–8 above and below |
| D15 | cv and cu | cv = 2.0 m²/yr all clays; cu 28.5 (BH-1 UU), 4.5N (Stroud) for BH-2/BH-3 | **Accepted** | Lab where available |
| D16 | Mw | AI recommended 7.5 | **Changed by group: Mw = 8.0** | Conservative for the Himalayan region around Mandi (1905 Kangra earthquake, Mw ≈ 7.8); a larger Mw lowers MSF |
| D17 | Alternative foundation | AI recommended bored piles under all columns | Group asked: "CPRF and PF are taught and footing, raft etc are taught, what will work for project?" → AI explained Poulos (2001) unfavourable conditions for CPRF; **group asked to analyse CPRF too before rejecting it** | PDR analysis: raft share 1.2 % (BH-3), 5.7 % (BH-1), 39 % (BH-2) → CPRF rejected, **PF adopted** |
| D18 | Pile capacity method | Reese & O'Neill (SPT) | **Changed by group: both Reese & O'Neill and IS 2911 Annex B as cross-check** | Group to read Nq from IS 2911 Fig. 1 (AI explained how to read a log-scale chart) |
| D19 | Pile diameter | AI recommended 600 mm | **Changed by group: 750 mm** | Two piles per cap instead of three, higher lateral capacity in Zone V, and casing through boulders is practical |

---

## Session 2 – 21 Nov 2026 – Claude Code: verification against class notes

**Prompt (verbatim):** "This has textbook examples, run relavent onse" (with the M3, M4 and M6 notes attached)

| AI output | Accepted / changed / rejected | Reason |
|---|---|---|
| Ran M3 Problems 1, 2, 3, 6 and Q12 through the platform code; shared values (q, Nc, Nq, d-factors, c_m, e, B′, A′, SPT steps) matched | Accepted | Differences only where IS 6403 differs from Terzaghi/Meyerhof (Nγ, 0.67 vs ⅔, W′) |
| Found that depth factors used B′ and that the kern warning fired at e = B/6 | **Accepted the fix** | Class notes P6 use D_f/B; added as tests (audit item A6) |

---

## Session 3 – 21 Nov 2026 – Claude Code: web design (direction by Gaurav)

**Prompts (verbatim):** "I want it to look like some crazzy ass design, it should compldtely blow sitrs mind … I have attaced photos in inspirations folder … glassy, smooth design like that, but with some crazy good combo of green and some other rich colour and website should be smooth" · "Naah, not so good design" · "Add smooth scroll" · "It dosent scroll when we are on any such black bx … below tables add a option to export to csv" · "Make all this clickable, it should lead to where it came from"

| AI output | Accepted / changed / rejected | Reason |
|---|---|---|
| Palette options | **Changed by Gaurav:** Emerald + Molten Gold, and no floating orbs | Design choice |
| First glass theme | **Rejected by Gaurav** ("not so good"); AI asked what was wrong → static light arcs, floating sidebar, dock tabs | Too dark and flat, looked like default Streamlit |
| Smooth scroll, CSV export, clickable tiles, formula dialogs, deep links, shortcuts | Accepted after testing | Requested by Gaurav; each verified in the browser |
| Upper-case metric labels | **Rejected** | Turned kPa into "KPA" – wrong units |

## Session 4 – 21–22 Nov 2026 – Claude Code: deployment, sign-in, usability

**Prompts (verbatim):** "Where to publish, vercel or streamlit?" · "I dont want on stramlit, thats the thing, it looks ugly on phone" · "Cloud Run + mobile fix" · "How about adding auth and storage?" · "Internal Server error" · "Leave all that, create a button that will create a fresh environment where all the inpus can be given from scratch"

| AI output | Accepted / changed / rejected | Reason |
|---|---|---|
| Vercel suggested by group | **Rejected by AI with reason**, group agreed | Streamlit needs a persistent websocket server |
| Google Cloud Run with free-tier limits, mobile layout | Accepted | No branding, scales to zero |
| Google sign-in + Firestore storage | Accepted; first deploy failed (missing `httpx`) and was fixed from the server log | Guest mode kept for the instructor |
| New Project button, input/result table marking, Add Row / Remove Last | Accepted | Group feedback that tables were not intuitive |
| Rectangle L = B vs square mismatch (raised by Ayush Chhajer) | **Group finding**, fixed | IS 6403 Table 2 is discontinuous at B/L = 1; a square uses the square row |
| Single inclined load Q at α (suggested by Ayush Chhajer) | Accepted | P = Q cos α for pressures, α for inclination factors |
