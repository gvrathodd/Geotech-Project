# AI Log – CE 402 Geotechnical Assignment (Group 1)

Format required by the brief: for each working session – date, tool, purpose, key prompts
(verbatim), and what we accepted, changed or rejected, with the reason.

> The group edits this file. Entries marked **[GROUP TO COMPLETE]** need the group's own
> words (who reviewed, what they checked, why they accepted/rejected).

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
| 1 | Reading of the brief: two halves (platform P1–P5, P8 + hostel design), traps in the data (BH-1 N = 22 at 9.0 m struck a cobble; units kg/cm² and cm²/s; design vs measured water table; BH-3 soft clay near footing level) | Accepted | Checked against the PDF tables ourselves **[GROUP TO COMPLETE: who checked]** |
| 2 | Claimed three gaps: C4 load missing (27 of 28 columns listed), P6/P7 missing, borehole allocation blank | Accepted only after verification | We asked the AI to *confirm* first; it extracted the PDF text layer and searched for "C4", "P6", "P7" – confirmed |
| 3 | E-mail draft to the professor | Changed | We rewrote the wording; we chose 50 kN·m for the C4 moment. AI pointed out "about X axis" is ambiguous (the brief defines no axes) and Z would be torsion; we changed it to "acting along the building length (east–west)" |
| 4 | Preliminary numbers (φ′ ≈ 30° soaked SM, cu ≈ 28.5 / 36 kPa, Cc ≈ 0.29, σ′p ≈ 110–125 kPa) | Pending verification | To be checked by hand calculation before use **[GROUP TO COMPLETE]** |
| 5 | AI quoted IS 1904:1986 Table 1 limits "from memory" | **Not accepted yet** | Must be checked against the code copy – the brief requires us to find and cite them ourselves |
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
| D3 | Local vs general shear | User selects; "auto" interpolates linearly between local (φ ≤ 28°) and general (φ ≥ 36°) | **Accepted** (alternatives offered: N-based rule; user must choose) | IS 6403 gives no φ-based switch; interpolation avoids a jump in capacity at one φ value. Both results are still displayed. **[GROUP: add your reasoning]** |
| D4 | γ in the Nγ term and W′ | Bulk γ (γsat if water table within B below base) × W′ (IS 6403); q uses effective overburden – never γ′ and W′ together | | |
| D5 | Net applied pressure | q_net = (P + W_footing+backfill − σv,total(Df)·A)/A′, γ footing+backfill = 20 kN/m³ | **Accepted 20 kN/m³** (alternatives: P/A only; 24 kN/m³) | Average of RCC (25) and compacted backfill (~18); editable in the app |
| D6 | Schmertmann | E entered per layer; Iz shape interpolated between L/B = 1 and 10; clay layers skipped (done by consolidation) | | |
| D7 | Consolidation σ′0 | Uses the design water table | **Accepted – design (highest, August)** (alternatives: measured; mean of Aug & May) | Lowest σ′0 gives the largest settlement (conservative); consistent with the bearing check |
| D8 | Liquefaction (beyond the brief) | Add IS 1893 (Part 1):2016 Annex F simplified procedure | **Accepted – library + app tab + design check** (asked twice; confirmed "with proper justification in report, readme and wherever else needed") | Zone V, stream 25 m away, loose saturated silty sand in BH-3 (N = 6) |
| D9 | Clay stress history | POP = 37 kPa (BH-1 σ′p 116.6 − σ′v0 79.5 kPa at 7.225 m) for BH-1/BH-2; NC for BH-3 | **Accepted** (alternatives: POP everywhere; NC everywhere) | BH-3 clay is the softest (N = 4–6), near the stream, no undisturbed sample |
| D10 | Sand φ′ | AI recommended lab φ′ (soaked DS: SM 30.0°, SP 34.4°) for BH-1/2 and SPT for BH-3 | **Changed by group: SPT correlation (Wolff 1989) everywhere, c′ = 0** | **[GROUP: write your reason – e.g. lab specimens were remoulded, SPT reflects in-situ density at each borehole]** Lab values kept as a cross-check (SM: SPT 32.3–33.0° vs lab 30.0°) |
| D11 | Sand E (Schmertmann) | E = 2.5 qc, qc/N = 0.4 MPa (SM), 0.5 MPa (SP) on corrected N | **Accepted** | Robertson et al. (1983) ranges |
| D12 | IS 1904 limits | Multistoreyed RC framed building with panel walls, isolated footings: 75 mm (plastic clay), 0.002L, 1/500 | **Accepted – values to be verified in our copy of IS 1904:1986 Table 1** | RC frame with masonry infill = panel walls; clay governs settlement |
| D13 | a_max for liquefaction | Z = 0.36 | **Accepted** | Conservative; hostel = important occupancy |
| D14 | BH-1 N = 22 at 9.0 m | Exclude | **Accepted** | Sampler struck a cobble, gravel recovered; N = 5–8 above and below |
| D15 | cv and cu | cv = 2.0 m²/yr all clays; cu 28.5 (BH-1 UU), 4.5N (Stroud) for BH-2/BH-3 | **Accepted** | Lab where available |
| D16 | Mw | AI recommended 7.5 | **Changed by group: Mw = 8.0** | **[GROUP: reason – e.g. conservative for the Himalayan frontal thrust region]** |
| D17 | Alternative foundation | AI recommended bored piles under all columns | Group asked: "CPRF and PF are taught and footing, raft etc are taught, what will work for project?" → AI explained Poulos (2001) unfavourable conditions for CPRF; **group asked to analyse CPRF too before rejecting it** | PDR analysis: raft share 1.2 % (BH-3), 5.7 % (BH-1), 39 % (BH-2) → CPRF rejected, **PF adopted** |
| D18 | Pile capacity method | Reese & O'Neill (SPT) | **Changed by group: both Reese & O'Neill and IS 2911 Annex B as cross-check** | Group to read Nq from IS 2911 Fig. 1 (AI explained how to read a log-scale chart) |
| D19 | Pile diameter | AI recommended 600 mm | **Changed by group: 750 mm** | **[GROUP: reason – e.g. fewer piles, better lateral capacity in Zone V]** |
