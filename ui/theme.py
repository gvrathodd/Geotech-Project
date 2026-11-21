"""Liquid-glass visual theme for the Streamlit app: neon emerald + molten gold light arcs
behind frosted glass on near-black.

Presentation only: nothing here affects a calculation.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ------------------------------------------------------------------ tokens
EMERALD = "#2EF0A8"
EMERALD_DEEP = "#0FB981"
MINT = "#8CFFD5"
GOLD = "#FFB627"
GOLD_SOFT = "#FFD27A"
AMBER = "#FF8A00"
TEAL = "#2DD4BF"
INK = "#030806"
TEXT = "#EEF8F2"
MUTED = "#A7C2B5"
DANGER = "#FF6B8B"

SOIL_COLORS = {"Granular": "rgba(255,182,39,0.45)", "Cohesive": "rgba(45,212,191,0.38)"}
WATER = "#7DD3FC"

# ------------------------------------------------------------------ icons (Lucide, MIT)
ICONS = {
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "waves": '<path d="M2 6c.6.5 1.2 1 2.5 1C7 7 7 5 9.5 5c2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>'
             '<path d="M2 12c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>'
             '<path d="M2 18c.6.5 1.2 1 2.5 1 2.5 0 2.5-2 5-2 2.6 0 2.4 2 5 2 2.5 0 2.5-2 5-2 1.3 0 1.9.5 2.5 1"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "arrow-up-right": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
}


def icon(name: str, size: int = 18) -> str:
    return (f'<svg aria-hidden="true" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            f'{ICONS[name]}</svg>')


CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800;900&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  color-scheme: dark;
  --ink: #030806;
  --text: #EEF8F2;
  --muted: #A7C2B5;
  --emerald: #2EF0A8;
  --mint: #8CFFD5;
  --gold: #FFB627;
  --gold-soft: #FFD27A;
  --amber: #FF8A00;
  --danger: #FF6B8B;
  --glass: linear-gradient(160deg, rgba(255,255,255,0.115) 0%, rgba(255,255,255,0.04) 45%, rgba(255,255,255,0.07) 100%);
  --glass-hi: linear-gradient(160deg, rgba(255,255,255,0.17) 0%, rgba(255,255,255,0.07) 100%);
  --rim-grad: linear-gradient(135deg, rgba(140,255,213,0.85) 0%, rgba(255,255,255,0.10) 28%, rgba(255,255,255,0.04) 60%, rgba(255,210,122,0.80) 100%);
  --rim: inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -1px 0 rgba(255,255,255,0.05);
  --lift: 0 30px 70px -30px rgba(0,0,0,0.9), 0 0 0 1px rgba(255,255,255,0.02);
  --blur: blur(30px) saturate(190%);
  --frost: linear-gradient(180deg, #FFFFFF 0%, #DFF6EA 100%);
  --ease: cubic-bezier(.22,.9,.24,1);
  --spring: cubic-bezier(.34,1.56,.64,1);
}

/* =================== canvas: two huge light arcs (static) =================== */
html, body { background: var(--ink); }
.stApp {
  background:
    radial-gradient(120% 70% at 50% 120%, rgba(255,138,0,0.10), transparent 60%),
    linear-gradient(180deg, #020604 0%, #030907 50%, #050805 100%);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}
.stApp::before, .stApp::after {
  content: ""; position: fixed; z-index: 0; pointer-events: none; border-radius: 50%;
}
/* emerald arc, lower-left */
.stApp::before {
  width: 155vmax; height: 155vmax; left: -48vmax; top: 52vh;
  background:
    radial-gradient(circle at 50% 0%, rgba(46,240,168,0.30) 0%, rgba(46,240,168,0.08) 22%, transparent 46%),
    radial-gradient(closest-side, transparent 93%, rgba(46,240,168,0.16) 98.5%, transparent 100%);
  box-shadow: 0 0 0 1.5px rgba(160,255,220,0.75), 0 -6px 30px rgba(46,240,168,0.65), 0 -30px 120px rgba(46,240,168,0.35),
              inset 0 30px 120px rgba(46,240,168,0.30);
}
/* molten-gold arc, upper-right */
.stApp::after {
  width: 110vmax; height: 110vmax; right: -76vmax; top: -62vmax;
  background:
    radial-gradient(circle at 18% 70%, rgba(255,182,39,0.26) 0%, rgba(255,138,0,0.08) 25%, transparent 48%),
    radial-gradient(closest-side, transparent 93%, rgba(255,182,39,0.14) 98.5%, transparent 100%);
  box-shadow: 0 0 0 1.5px rgba(255,220,150,0.70), 0 0 34px rgba(255,170,40,0.55), 0 0 140px rgba(255,138,0,0.30),
              inset 0 0 120px rgba(255,170,40,0.22);
}
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: transparent !important; position: relative; z-index: 1; }
@media (pointer: fine) { html { overscroll-behavior: none; } }
header[data-testid="stHeader"] { background: transparent !important; height: 0; }
#MainMenu, [data-testid="stAppDeployButton"], [data-testid="stStatusWidget"], footer, [data-testid="stDecoration"] { display: none !important; }
.block-container { padding-top: 1.6rem; max-width: 1400px; }

h1, h2, h3, h4 { font-family: 'Outfit', sans-serif !important; letter-spacing: -0.015em; text-wrap: balance; color: var(--text); }
p, li, label { text-wrap: pretty; }
code { font-family: 'JetBrains Mono', monospace !important; color: var(--mint) !important;
       background: rgba(46,240,168,0.10) !important; border-radius: 6px; }
::selection { background: rgba(46,240,168,0.35); }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 99px; border: 2px solid transparent; background-clip: padding-box; }

/* =================== glass recipe =================== */
[class*="st-key-glass"], div[data-testid="stExpander"] details, [data-testid="stMetric"], .tile, .stTabs [role="tablist"] {
  position: relative;
  background: var(--glass) !important;
  border: 1px solid rgba(255,255,255,0.06) !important;
  box-shadow: var(--rim), var(--lift);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
}
/* gradient light rim (mint -> gold), drawn with a masked pseudo-element */
[class*="st-key-glass"]::before, [data-testid="stMetric"]::before, .tile::before, .stTabs [role="tablist"]::before,
div[data-testid="stExpander"] details::before {
  content: ""; position: absolute; inset: -1px; border-radius: inherit; padding: 1px; pointer-events: none;
  background: var(--rim-grad);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude; opacity: .55;
  transition: opacity .35s var(--ease);
}
[class*="st-key-glass"] {
  border-radius: 32px !important; padding: 1.5rem 1.6rem 1.3rem !important;
  animation: rise .75s var(--ease) both;
}
[class*="st-key-glass"]:hover::before { opacity: .9; }
div[data-testid="stExpander"] details { border-radius: 24px !important; }
div[data-testid="stExpander"] summary:hover { color: var(--mint); }

/* metrics */
[data-testid="stMetric"] {
  border-radius: 24px; padding: 15px 18px 13px;
  transition: transform .45s var(--spring), box-shadow .3s var(--ease);
}
[data-testid="stMetric"]:hover { transform: translateY(-4px); box-shadow: var(--rim), var(--lift), 0 18px 40px -18px rgba(46,240,168,0.45); }
[data-testid="stMetric"]:hover::before { opacity: 1; }
[data-testid="stMetricLabel"] p { font-size: .82rem !important; color: var(--muted) !important; font-weight: 600; }
[data-testid="stMetric"] { container-type: inline-size; }
[data-testid="stMetricValue"] { font-family: 'Outfit', sans-serif; font-weight: 700; font-size: clamp(1.15rem, 13cqi, 1.85rem) !important;
  font-variant-numeric: tabular-nums; color: #fff; text-shadow: 0 0 24px rgba(46,240,168,0.25); }

/* =================== floating glass sidebar =================== */
section[data-testid="stSidebar"] { background: transparent !important; border: none !important; box-shadow: none !important; }
section[data-testid="stSidebar"] > div:first-child {
  margin: 14px 0 14px 14px; height: calc(100vh - 28px); border-radius: 30px; overflow: hidden auto;
  background: linear-gradient(170deg, rgba(20,48,36,0.62), rgba(6,16,11,0.72)) !important;
  border: 1px solid rgba(255,255,255,0.09);
  box-shadow: var(--rim), 0 30px 80px -30px rgba(0,0,0,0.9);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
}
[data-testid="stSidebarContent"], [data-testid="stSidebarUserContent"] { background: transparent !important; }
section[data-testid="stSidebar"] h3 {
  font-size: .8rem !important; letter-spacing: .08em; color: var(--gold-soft) !important; margin-top: 1.2rem;
  display: flex; align-items: center; gap: 8px; }
section[data-testid="stSidebar"] h3::before { content: ""; width: 18px; height: 2px; border-radius: 2px;
  background: linear-gradient(90deg, var(--emerald), var(--gold)); box-shadow: 0 0 10px var(--emerald); }

/* =================== floating dock tabs =================== */
.stTabs [role="tablist"] {
  position: sticky; top: 12px; z-index: 100;
  gap: 4px; padding: 7px; border-radius: 999px; width: fit-content; max-width: 100%; margin: 0 auto;
  overflow-x: auto; scrollbar-width: none;
  background: linear-gradient(160deg, rgba(30,60,46,0.55), rgba(8,18,13,0.65)) !important;
}
.stTabs [role="tablist"]::-webkit-scrollbar { display: none; }
.stTabs [data-testid="stTab"] {
  position: relative; flex: 0 0 auto !important; width: auto !important;
  height: auto; padding: 10px 20px; border-radius: 999px; background: transparent; white-space: nowrap;
  color: var(--muted); font-family: 'Outfit', sans-serif; font-weight: 500; border: none !important; cursor: pointer;
  transition: background-color .35s var(--ease), color .35s var(--ease), box-shadow .35s var(--ease), transform .35s var(--spring);
}
.stTabs [data-testid="stTab"]::after, .stTabs [data-testid="stTab"]::before { display: none !important; }
.stTabs [data-testid="stTab"] p { font-size: .98rem; margin: 0; white-space: nowrap; }
.stTabs [data-testid="stTab"] > div, .stTabs [data-testid="stTab"] [data-testid="stMarkdownContainer"] { white-space: nowrap; }
.stTabs [data-testid="stTab"]:hover { color: #fff; background: rgba(255,255,255,0.08); }
.stTabs [data-testid="stTab"]:active { transform: scale(.96); }
/* react-aria's SelectionIndicator becomes the frosted pill and slides between tabs */
.stTabs .react-aria-SelectionIndicator {
  position: absolute !important; inset: 0 !important; height: auto !important; width: auto !important;
  border-radius: 999px; background: var(--frost) !important; z-index: 0;
  box-shadow: 0 0 0 1px rgba(255,255,255,0.7), 0 8px 26px -6px rgba(46,240,168,0.75), 0 0 40px -8px rgba(255,182,39,0.45);
  transition: translate .45s var(--ease), width .45s var(--ease) !important;
}
.stTabs [data-testid="stTab"] [data-testid="stMarkdownContainer"] { position: relative; z-index: 1; }
.stTabs [data-testid="stTab"][aria-selected="true"] { background: transparent !important; }
.stTabs [data-testid="stTab"][aria-selected="true"]:hover { background: transparent !important; }
.stTabs [data-testid="stTab"][aria-selected="true"] p { color: #052016 !important; font-weight: 700; }
.stTabs [data-testid="stTabPanel"] { padding-top: 1.6rem; animation: panel .55s var(--ease) both; }

/* =================== inputs =================== */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
  background: rgba(255,255,255,0.06) !important; border-radius: 14px !important;
  border-color: rgba(255,255,255,0.12) !important;
  transition: border-color .25s var(--ease), box-shadow .25s var(--ease), background-color .25s var(--ease);
}
[data-baseweb="input"]:hover, [data-baseweb="select"] > div:hover { background: rgba(255,255,255,0.09) !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within {
  border-color: var(--emerald) !important; box-shadow: 0 0 0 3px rgba(46,240,168,0.25), 0 0 24px -6px rgba(46,240,168,0.6) !important; }
input, textarea { font-variant-numeric: tabular-nums; }
[data-testid="stWidgetLabel"] p { color: var(--muted); font-weight: 500; }

/* =================== buttons =================== */
.stButton > button, .stDownloadButton > button {
  border-radius: 999px !important; border: 1px solid rgba(255,255,255,0.16) !important;
  background: var(--glass-hi) !important; color: #fff !important; font-weight: 600; box-shadow: var(--rim);
  transition: transform .35s var(--spring), border-color .25s var(--ease), box-shadow .25s var(--ease);
  touch-action: manipulation;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  transform: translateY(-2px); border-color: rgba(140,255,213,0.7) !important;
  box-shadow: var(--rim), 0 12px 34px -12px rgba(46,240,168,0.8); }
.stButton > button:active, .stDownloadButton > button:active { transform: translateY(0) scale(.97); }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
  background: linear-gradient(110deg, #2EF0A8 0%, #B5FFE2 42%, #FFD27A 72%, #FFB627 100%) !important;
  color: #04170F !important; border: none !important; font-weight: 700;
  box-shadow: 0 10px 34px -10px rgba(46,240,168,0.9), 0 6px 30px -12px rgba(255,182,39,0.8), inset 0 1px 0 rgba(255,255,255,0.8); }
button:focus-visible, [role="tab"]:focus-visible, a:focus-visible, summary:focus-visible {
  outline: 2px solid var(--gold) !important; outline-offset: 3px; }

/* =================== tables & alerts =================== */
[data-testid="stDataFrame"], [data-testid="stDataEditor"] {
  border-radius: 18px; overflow: hidden; box-shadow: 0 0 0 1px rgba(255,255,255,0.07), 0 18px 40px -24px rgba(0,0,0,0.9);
}
[data-testid="stAlertContainer"] { border-radius: 18px !important; backdrop-filter: blur(16px);
  border: 1px solid rgba(255,210,122,0.25); }
[data-testid="stPlotlyChart"] { border-radius: 22px; overflow: hidden; }
hr { border-color: rgba(255,255,255,0.08) !important; }

/* =================== hero =================== */
.hero { position: relative; padding: 18px 4px 8px; animation: rise .9s var(--ease) both; }
.hero-kicker { display: inline-flex; align-items: center; gap: 10px; padding: 8px 16px 8px 11px; border-radius: 999px;
  background: var(--glass); border: 1px solid rgba(255,255,255,0.12); box-shadow: var(--rim);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
  font: 500 .84rem 'Inter', sans-serif; color: #D8EDE2; }
.hero-kicker .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--emerald);
  box-shadow: 0 0 0 4px rgba(46,240,168,0.2), 0 0 16px var(--emerald); animation: pulse 2.6s ease-in-out infinite; }
.hero h1.hero-title { font: 900 clamp(3.2rem, 8.4vw, 7rem)/0.92 'Outfit', sans-serif !important; letter-spacing: -0.045em;
  margin: 22px 0 14px; padding: 0; color: #fff; text-shadow: 0 0 60px rgba(46,240,168,0.22); }
.grad { background: linear-gradient(100deg, #2EF0A8 0%, #B5FFE2 32%, #FFD27A 64%, #FF8A00 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent; text-shadow: none;
  filter: drop-shadow(0 0 28px rgba(255,182,39,0.35)); }
.hero-sub { color: #C3D9CD; font-size: 1.08rem; max-width: 780px; margin: 0; }
.hero-sub b { color: #fff; font-weight: 600; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.chip { padding: 7px 13px; border-radius: 999px; font: 500 .8rem 'JetBrains Mono', monospace; color: var(--gold-soft);
  background: rgba(255,182,39,0.09); border: 1px solid rgba(255,210,122,0.30); backdrop-filter: blur(10px);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.12); }
.horizon { position: relative; height: 2px; margin: 26px 0 24px; border-radius: 2px; overflow: hidden;
  background: linear-gradient(90deg, transparent 0%, rgba(46,240,168,0.9) 30%, rgba(255,210,122,0.95) 70%, transparent 100%);
  box-shadow: 0 0 18px rgba(46,240,168,0.55), 0 0 40px rgba(255,182,39,0.35); }
.horizon::after { content: ""; position: absolute; inset: 0; width: 30%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.95), transparent);
  animation: sweep 5.5s var(--ease) infinite; }

/* =================== result tiles =================== */
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 16px; margin: 0 0 30px; }
.tile { min-width: 0; padding: 18px 18px 16px; border-radius: 30px;
  transition: transform .5s var(--spring), box-shadow .35s var(--ease);
  animation: rise .8s var(--ease) both; }
.tile:nth-child(1) { animation-delay: .05s; } .tile:nth-child(2) { animation-delay: .12s; }
.tile:nth-child(3) { animation-delay: .19s; } .tile:nth-child(4) { animation-delay: .26s; }
.tile:nth-child(5) { animation-delay: .33s; } .tile:nth-child(6) { animation-delay: .40s; }
.tile:hover { transform: translateY(-6px) scale(1.015); box-shadow: var(--rim), var(--lift), 0 24px 50px -22px rgba(46,240,168,0.6); }
.tile:hover::before { opacity: 1; }
.tile .ic { width: 42px; height: 42px; border-radius: 50%; display: grid; place-items: center; margin-bottom: 14px;
  color: #04170F; background: linear-gradient(135deg, #2EF0A8, #B5FFE2);
  box-shadow: 0 0 22px -2px rgba(46,240,168,0.75), inset 0 1px 0 rgba(255,255,255,0.7); }
.tile .lbl { font: 600 .82rem 'Inter', sans-serif; color: var(--muted); }
.tile .val { font: 800 2.1rem/1.1 'Outfit', sans-serif; font-variant-numeric: tabular-nums; color: #fff; margin-top: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; letter-spacing: -0.02em; }
.tile .val small { font: 600 .9rem 'Inter', sans-serif; color: var(--muted); margin-left: 5px; letter-spacing: 0; }
.tile .sub { font-size: .78rem; line-height: 1.35; color: var(--muted); margin-top: 4px; overflow: hidden;
  display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.tile.text .val { font-size: 1.22rem; font-weight: 700; white-space: normal; line-height: 1.22; letter-spacing: -0.01em; }
.tile.gold .ic { background: linear-gradient(135deg, #FFB627, #FFE2A3); box-shadow: 0 0 22px -2px rgba(255,182,39,0.8), inset 0 1px 0 rgba(255,255,255,0.7); }
.tile.pass { background: var(--frost) !important; }
.tile.pass::before { background: linear-gradient(135deg, #fff, rgba(46,240,168,0.9)); opacity: 1; }
.tile.pass .lbl, .tile.pass .sub, .tile.pass .val small { color: #2C5C47; }
.tile.pass .val { color: #04170F; text-shadow: none; }
.tile.pass .ic { background: linear-gradient(135deg, #0FB981, #2EF0A8); color: #fff; }
.tile.pass { box-shadow: 0 0 0 1px rgba(255,255,255,0.6), 0 20px 60px -20px rgba(46,240,168,0.75); }
.tile.fail .ic { background: linear-gradient(135deg, #FF6B8B, #FFB3C2); color: #2A0710;
  box-shadow: 0 0 22px -2px rgba(255,107,139,0.8); }
.tile.fail::before { background: linear-gradient(135deg, rgba(255,107,139,0.9), rgba(255,255,255,0.05) 50%, rgba(255,107,139,0.5)); opacity: .8; }

.pill { display: inline-flex; align-items: center; gap: 6px; padding: 5px 13px 5px 9px; border-radius: 999px;
  font: 700 .8rem 'Inter', sans-serif; letter-spacing: .04em; }
.pill.ok { background: linear-gradient(135deg, #2EF0A8, #B5FFE2); color: #04170F; box-shadow: 0 0 20px -4px rgba(46,240,168,0.8); }
.pill.bad { background: linear-gradient(135deg, #FF6B8B, #FFB3C2); color: #2A0710; box-shadow: 0 0 20px -4px rgba(255,107,139,0.8); }

.sec { display: flex; align-items: center; gap: 12px; margin: 0 0 2px; }
.sec .no { font: 600 .74rem 'JetBrains Mono', monospace; color: #04170F; padding: 4px 10px; border-radius: 999px;
  background: linear-gradient(135deg, #FFD27A, #FFB627); box-shadow: 0 0 16px -4px rgba(255,182,39,0.8); }
.sec h3 { margin: 0 !important; padding: 0 !important; font-size: 1.45rem !important; font-weight: 700 !important; }
.sec-sub { color: var(--muted); font-size: .92rem; margin: 6px 0 14px; max-width: 980px; }

.brand { display: flex; align-items: center; gap: 12px; font: 800 1.2rem 'Outfit', sans-serif; color: #fff; margin: 6px 0 2px; letter-spacing: -0.01em; }
.brand .mark { width: 38px; height: 38px; border-radius: 13px; display: grid; place-items: center; color: #04170F;
  background: linear-gradient(135deg, #2EF0A8, #FFD27A); box-shadow: 0 0 26px -4px rgba(46,240,168,0.85), inset 0 1px 0 rgba(255,255,255,0.7); }
.brand-sub { color: var(--muted); font-size: .8rem; margin: 2px 0 10px 50px; }

/* clickable result tiles -> jump to source section */
a.tile { display: block; color: inherit !important; text-decoration: none !important; cursor: pointer; }
a.tile .go { position: absolute; top: 16px; right: 16px; width: 30px; height: 30px; border-radius: 50%;
  display: grid; place-items: center; color: var(--mint); background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.14); opacity: 0; transform: translate(-6px, 6px) scale(.85);
  transition: opacity .3s var(--ease), transform .45s var(--spring); }
a.tile:hover .go, a.tile:focus-visible .go { opacity: 1; transform: none; }
a.tile.pass .go { color: #0B7A55; background: rgba(4,23,15,0.06); border-color: rgba(4,23,15,0.12); }
a.tile:active { transform: translateY(-2px) scale(.985); }
a.tile:focus-visible { outline: 2px solid var(--gold) !important; outline-offset: 4px; }
@media (hover: none) { a.tile .go { opacity: .85; transform: none; } }
.fs-anchor { scroll-margin-top: 110px; }
[class*="st-key-glass"].fs-flash { animation: flash 2.2s var(--ease); }
[class*="st-key-glass"].fs-flash::before { opacity: 1; }
@keyframes flash {
  0%   { box-shadow: var(--rim), var(--lift), 0 0 0 0 rgba(46,240,168,0); }
  18%  { box-shadow: var(--rim), var(--lift), 0 0 0 3px rgba(46,240,168,0.95), 0 0 70px -6px rgba(46,240,168,0.7); }
  100% { box-shadow: var(--rim), var(--lift), 0 0 0 0 rgba(46,240,168,0); }
}

/* ---- tiles: intro animation only on first render; change glow ---- */
.tile { animation: none; }
.tiles.intro .tile { animation: rise .8s var(--ease) both; }
.tile.changed { animation: changed 1.8s var(--ease) both; }
.tile .delta { margin-left: 8px; padding: 1px 8px; border-radius: 999px; font: 700 .7rem 'JetBrains Mono', monospace;
  color: #3A2600; background: linear-gradient(135deg, #FFD27A, #FFB627); box-shadow: 0 0 14px -2px rgba(255,182,39,0.8);
  vertical-align: 1px; }
@keyframes changed {
  0%   { box-shadow: var(--rim), var(--lift), 0 0 0 0 rgba(255,182,39,0); }
  20%  { box-shadow: var(--rim), var(--lift), 0 0 0 2px rgba(255,210,122,0.95), 0 0 50px -4px rgba(255,182,39,0.75); }
  100% { box-shadow: var(--rim), var(--lift), 0 0 0 0 rgba(255,182,39,0); }
}
.tiles.fs-flash-soft .tile { animation: changed 1.6s var(--ease); }

/* ---- section badge = copy link ---- */
.sec a.no { text-decoration: none !important; cursor: copy; transition: transform .3s var(--spring), box-shadow .25s var(--ease); }
.sec a.no:hover { transform: translateY(-1px) scale(1.06); box-shadow: 0 0 22px -2px rgba(255,182,39,0.95); }
.sec a.no:focus-visible { outline: 2px solid var(--mint) !important; outline-offset: 3px; }

/* ---- metrics that open a formula dialog ---- */
.stElementContainer:has(.fs-why), .element-container:has(.fs-why) { display: none !important; }
[data-testid="stMetric"].fs-why-able { cursor: pointer; }
[data-testid="stMetric"].fs-why-able::after { content: "ƒx"; position: absolute; top: 10px; right: 12px;
  font: 600 .7rem 'JetBrains Mono', monospace; color: var(--gold-soft); padding: 2px 7px; border-radius: 999px;
  background: rgba(255,182,39,0.10); border: 1px solid rgba(255,210,122,0.28); opacity: .55;
  transition: opacity .25s var(--ease); }
[data-testid="stMetric"].fs-why-able:hover::after, [data-testid="stMetric"].fs-why-able:focus-visible::after { opacity: 1; }
[data-testid="stMetric"].fs-why-able:focus-visible { outline: 2px solid var(--gold) !important; outline-offset: 3px; }

.fs-modal { position: fixed; inset: 0; z-index: 10000; display: grid; place-items: center; padding: 16px; }
.fs-modal[hidden] { display: none; }
.fs-scrim { position: absolute; inset: 0; background: rgba(2,6,4,0.55); backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px); opacity: 0; transition: opacity .22s var(--ease); }
.fs-dialog { position: relative; width: min(620px, 100%); max-height: min(80vh, 760px); overflow: auto; overscroll-behavior: contain;
  padding: 26px 26px 22px; border-radius: 30px; color: var(--text);
  background: linear-gradient(160deg, rgba(30,62,47,0.86), rgba(8,18,13,0.92));
  border: 1px solid rgba(255,255,255,0.12); box-shadow: var(--rim), 0 40px 120px -30px rgba(0,0,0,0.95),
  0 0 0 1px rgba(46,240,168,0.15), 0 0 80px -20px rgba(46,240,168,0.35);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
  opacity: 0; transform: translateY(14px) scale(.97); transition: opacity .25s var(--ease), transform .35s var(--spring); }
.fs-modal.open .fs-scrim { opacity: 1; }
.fs-modal.open .fs-dialog { opacity: 1; transform: none; }
.fs-x { position: absolute; top: 14px; right: 14px; width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center;
  color: var(--text); background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14); cursor: pointer;
  transition: background-color .2s var(--ease), transform .3s var(--spring); }
.fs-x:hover { background: rgba(255,255,255,0.16); transform: rotate(90deg); }
.fs-x:focus-visible { outline: 2px solid var(--gold); outline-offset: 2px; }
.fs-why-h { font: 600 .85rem 'Inter', sans-serif; color: var(--muted); padding-right: 44px; }
.fs-why-v { font: 800 2.3rem/1.1 'Outfit', sans-serif; color: #fff; margin: 4px 0 14px; font-variant-numeric: tabular-nums;
  text-shadow: 0 0 30px rgba(46,240,168,0.3); }
.fs-dialog dl { margin: 0; display: grid; gap: 4px; }
.fs-dialog dt { font: 700 .72rem 'Inter', sans-serif; letter-spacing: .08em; text-transform: uppercase; color: var(--gold-soft); margin-top: 12px; }
.fs-dialog dd { margin: 0; line-height: 1.65; }
.fs-dialog dd.f { font: 500 1.02rem 'JetBrains Mono', monospace; color: #fff; padding: 10px 14px; border-radius: 14px;
  background: rgba(46,240,168,0.08); border: 1px solid rgba(46,240,168,0.22); overflow-x: auto; }
.fs-dialog dd.n { font: 400 .95rem 'JetBrains Mono', monospace; color: #DDEFE5; font-variant-numeric: tabular-nums; }
.fs-dialog dd.r { color: var(--muted); font-size: .92rem; }
.fs-dialog dd.x { color: #FFE2A3; font-size: .9rem; }
.fs-dialog sub, .fs-dialog sup { font-size: .72em; }

/* ---- toast ---- */
.fs-toast { position: fixed; left: 50%; bottom: 28px; z-index: 10001; transform: translate(-50%, 20px); opacity: 0; pointer-events: none;
  padding: 11px 18px; border-radius: 999px; font: 600 .9rem 'Inter', sans-serif; color: #04170F;
  background: linear-gradient(110deg, #2EF0A8, #B5FFE2 55%, #FFD27A); box-shadow: 0 14px 40px -12px rgba(46,240,168,0.9);
  transition: opacity .25s var(--ease), transform .4s var(--spring); max-width: calc(100vw - 32px); }
.fs-toast.show { opacity: 1; transform: translate(-50%, 0); }

/* ---- back to results ---- */
.fs-back { position: fixed; right: 26px; bottom: 26px; z-index: 9000; display: inline-flex; align-items: center; gap: 8px;
  padding: 11px 18px 11px 14px; border-radius: 999px; cursor: pointer; font: 600 .9rem 'Inter', sans-serif; color: #fff;
  background: linear-gradient(160deg, rgba(40,80,60,0.75), rgba(8,18,13,0.85)); border: 1px solid rgba(140,255,213,0.35);
  box-shadow: var(--rim), 0 16px 40px -14px rgba(0,0,0,0.9), 0 0 30px -10px rgba(46,240,168,0.6);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
  opacity: 0; transform: translateY(16px) scale(.95); pointer-events: none;
  transition: opacity .3s var(--ease), transform .45s var(--spring), border-color .2s var(--ease); touch-action: manipulation; }
.fs-back.show { opacity: 1; transform: none; pointer-events: auto; }
.fs-back:hover { border-color: var(--mint); }
.fs-back:focus-visible { outline: 2px solid var(--gold); outline-offset: 3px; }

/* ---- sidebar contents list ---- */
.fs-toc:empty { display: none; }
.fs-toc { margin: 8px 0 4px; padding: 10px; border-radius: 20px; background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08); }
.fs-toc-h { font: 700 .72rem 'Inter', sans-serif; letter-spacing: .08em; text-transform: uppercase; color: var(--gold-soft);
  padding: 2px 6px 6px; }
.fs-toc a { display: flex; align-items: center; gap: 9px; padding: 7px 8px; border-radius: 12px; text-decoration: none !important;
  color: var(--muted) !important; font-size: .86rem; transition: background-color .2s var(--ease), color .2s var(--ease); }
.fs-toc a:hover { background: rgba(255,255,255,0.07); color: #fff !important; }
.fs-toc a.on { background: rgba(46,240,168,0.12); color: #fff !important; box-shadow: inset 2px 0 0 var(--emerald); }
.fs-toc a .b { flex: none; font: 600 .66rem 'JetBrains Mono', monospace; color: #04170F; padding: 2px 7px; border-radius: 999px;
  background: linear-gradient(135deg, #FFD27A, #FFB627); }
.fs-toc a .t { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fs-keys { margin: 14px 2px 4px; color: var(--muted); font-size: .76rem; line-height: 1.9; }
.fs-keys kbd { font: 600 .7rem 'JetBrains Mono', monospace; color: #fff; padding: 1px 6px; border-radius: 6px;
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.18); }

/* ---- highlighted sidebar inputs (footing tile, "/" shortcut) ---- */
section[data-testid="stSidebar"] .fs-hl { border-radius: 16px; animation: inputhl 2.4s var(--ease); }
@keyframes inputhl {
  0%   { box-shadow: 0 0 0 0 rgba(46,240,168,0); background: transparent; }
  15%  { box-shadow: 0 0 0 2px rgba(46,240,168,0.95), 0 0 30px -4px rgba(46,240,168,0.7); background: rgba(46,240,168,0.08); }
  100% { box-shadow: 0 0 0 0 rgba(46,240,168,0); background: transparent; }
}

/* compact "Export CSV" button under each table */
[class*="st-key-csv_"] { margin-top: -6px; }
[class*="st-key-csv_"] button { min-height: 0 !important; padding: 5px 14px 5px 11px !important; font-size: .8rem !important;
  color: var(--mint) !important; background: rgba(46,240,168,0.07) !important; border-color: rgba(46,240,168,0.28) !important; }
[class*="st-key-csv_"] button p { font-size: .8rem !important; }

.stElementContainer:has(.fs-js), .element-container:has(.fs-js),
.stElementContainer:has(> [data-testid="stMarkdown"] style:only-child) { display: none !important; }

@keyframes rise { from { opacity: 0; transform: translateY(18px) scale(.98); } to { opacity: 1; transform: none; } }
@keyframes panel { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes sweep { from { transform: translateX(-120%); } to { transform: translateX(420%); } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
@media (max-width: 640px) {
  section[data-testid="stSidebar"] > div:first-child { margin: 0; height: 100vh; border-radius: 0 26px 26px 0; }
  .tile .val { font-size: 1.7rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
"""

_card = {"n": 0}
_mx = {"n": 0}

# Inertial smooth scrolling (no external library).  The wheel scrolls whichever pane is under
# the pointer - main page or sidebar - eased with requestAnimationFrame.  The listener runs in the
# capture phase so a focused number box can never swallow the wheel or silently change its value.
# Native behaviour is kept for pinch-zoom (ctrl+wheel), horizontal scrolling and regions with their
# own scrolling (tables, data editors, charts, open dropdown lists).  Reduced-motion users get
# instant (un-eased) scrolling.  Installed once per page load; survives Streamlit reruns.
SMOOTH_SCROLL_JS = r"""
<div class="fs-js"></div>
<script>
(function () {
  var VER = 2;
  if (window.__fsSmoothVer === VER) return;
  if (window.__fsWheel) window.removeEventListener('wheel', window.__fsWheel, true);
  window.__fsSmoothVer = VER;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var EASE = 0.12;
  var NATIVE = '[data-testid="stDataFrame"], [data-testid="stDataEditor"], [data-testid="stPlotlyChart"], ' +
               '[role="listbox"], [data-baseweb="popover"], [data-baseweb="menu"], textarea, pre';
  function scrollable(el) {
    var s = getComputedStyle(el);
    return /(auto|scroll)/.test(s.overflowY) && el.scrollHeight > el.clientHeight + 1;
  }
  function paneFor(t) {
    for (var n = t; n && n !== document.documentElement; n = n.parentElement) {
      if (n.nodeType === 1 && scrollable(n)) return n;
    }
    return document.scrollingElement;
  }
  function delta(e, el) {
    return e.deltaMode === 1 ? e.deltaY * 40 : (e.deltaMode === 2 ? e.deltaY * el.clientHeight : e.deltaY);
  }
  var state = new WeakMap();
  function step(el) {
    var s = state.get(el);
    s.cur += (s.target - s.cur) * EASE;
    if (Math.abs(s.target - s.cur) < 0.5) { s.cur = s.target; el.scrollTop = s.cur; s.raf = null; return; }
    el.scrollTop = s.cur;
    s.raf = requestAnimationFrame(function () { step(el); });
  }
  function onWheel(e) {
    if (e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
    var t = e.target;
    if (!(t instanceof Element) || t.tagName === 'CANVAS' || t.closest(NATIVE)) return;
    var el = paneFor(t);
    if (!el) return;
    e.preventDefault();                       // also stops wheel-stepping of number inputs
    if (reduce) { el.scrollTop += delta(e, el); return; }
    var s = state.get(el);
    if (!s || s.raf === null) { s = { cur: el.scrollTop, target: el.scrollTop, raf: null }; state.set(el, s); }
    s.target = Math.max(0, Math.min(el.scrollHeight - el.clientHeight, s.target + delta(e, el)));
    if (s.raf === null) s.raf = requestAnimationFrame(function () { step(el); });
  }
  window.__fsWheel = onWheel;
  window.addEventListener('wheel', onWheel, { capture: true, passive: false });
  // keyboard, scrollbar drags, anchor jumps: resync so the next wheel starts from there
  document.addEventListener('scroll', function (ev) {
    var s = state.get(ev.target);
    if (s && s.raf === null) { s.cur = s.target = ev.target.scrollTop; }
  }, true);
})();
</script>
"""


# Page interactions (tile/contents navigation, copy-link badges, formula dialogs, footing-input
# highlight, back-to-results, contents list, keyboard shortcuts) live in ui/interactions.js.
# st.html runs DOMPurify even with JavaScript allowed, and DOMPurify drops a <script> whose text
# contains "<" followed by a letter or "/" (mXSS guard).  The markup strings inside the script are
# therefore written with the JS escape \x3c, which is "<" again at runtime.
INTERACTIONS_JS = re.sub(r"<(?=[/A-Za-z!?])", r"\\x3c",
                         (Path(__file__).with_name("interactions.js")).read_text(encoding="utf-8"))


def inject():
    _card["n"] = 0
    _mx["n"] = 0
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
    st.html(SMOOTH_SCROLL_JS, unsafe_allow_javascript=True)
    st.html(f'<div class="fs-js"></div><script>{INTERACTIONS_JS}</script>', unsafe_allow_javascript=True)
    _plotly_template()


def _plotly_template():
    axis = dict(gridcolor="rgba(255,255,255,0.07)", zerolinecolor="rgba(255,255,255,0.14)",
                linecolor="rgba(255,255,255,0.18)", tickfont=dict(family="JetBrains Mono, monospace", size=11),
                title=dict(font=dict(family="Inter, sans-serif", size=12, color=MUTED)))
    pio.templates["geoglass"] = go.layout.Template(layout=dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.025)",
        font=dict(family="Inter, sans-serif", color="#D5E9DE", size=12),
        colorway=[EMERALD, GOLD, TEAL, AMBER, MINT, GOLD_SOFT, "#A3E635"],
        xaxis=axis, yaxis=axis,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        hoverlabel=dict(bgcolor="#0B1A13", bordercolor=EMERALD, font=dict(family="JetBrains Mono, monospace", color=TEXT)),
        title=dict(font=dict(family="Outfit, sans-serif", size=15, color=TEXT)),
    ))
    pio.templates.default = "plotly_dark+geoglass"


# ------------------------------------------------------------------ components
def card():
    """Bordered container with a stable key -> class st-key-glass_N, styled as a glass card."""
    _card["n"] += 1
    return st.container(border=True, key=f"glass_{_card['n']}")


def hero(title_a: str, title_b: str, sub: str, chips: list[str], kicker: str):
    chips_html = "".join(f'<span class="chip" translate="no">{html.escape(c)}</span>' for c in chips)
    st.markdown(
        f'<div class="hero"><div class="hero-kicker"><span class="dot"></span>{html.escape(kicker)}</div>'
        f'<h1 class="hero-title">{html.escape(title_a)} <span class="grad">{html.escape(title_b)}</span></h1>'
        f'<p class="hero-sub">{sub}</p><div class="chips">{chips_html}</div></div><div class="horizon"></div>',
        unsafe_allow_html=True)


def tile(label: str, value: str, unit: str = "", sub: str = "", ic: str = "gauge", state: str = "",
         text: bool = False, go_to: tuple[int, str, str] | None = None, inputs: list[str] | None = None,
         delta: str = "") -> str:
    """Result tile.  go_to = (tab index, section anchor, where) makes it a link to the section the value
    comes from; inputs = widget keys makes it open and highlight those sidebar inputs.  delta, when set,
    marks the tile as changed since the last run (glow + chip)."""
    cls = " ".join(c for c in ["tile", state, "text" if text else "", "changed" if delta else ""] if c)
    u = f"<small>{html.escape(unit)}</small>" if unit else ""
    s = f'<div class="sub">{html.escape(sub)}</div>' if sub else ""
    d = f'<span class="delta">{html.escape(delta)}</span>' if delta else ""
    body = (f'<div class="ic">{icon(ic, 20)}</div><div class="lbl">{html.escape(label)}{d}</div>'
            f'<div class="val">{html.escape(value)}{u}</div>{s}')
    if go_to is None and not inputs:
        return f'<div class="{cls}">{body}</div>'
    if inputs:
        where = "the footing and load inputs"
        attrs = f'href="#footing" data-fs-inputs="{",".join(inputs)}"'
    else:
        tab, anchor, where = go_to
        attrs = f'href="#sec-{anchor}" data-fs-tab="{tab}" data-fs-anchor="{anchor}"'
    aria = html.escape(f"{label}: {' '.join(x for x in (value, unit) if x)}. Open {where}", quote=True)
    return (f'<a class="{cls}" {attrs} aria-label="{aria}" title="Open {html.escape(where, quote=True)}">'
            f'<span class="go">{icon("arrow-up-right", 16)}</span>{body}</a>')


def tiles(items: list[str], intro: bool = False):
    st.markdown(f'<div class="tiles{" intro" if intro else ""}">{"".join(items)}</div>', unsafe_allow_html=True)


def pill(ok: bool, yes: str = "PASS", no: str = "FAIL") -> str:
    return (f'<span class="pill {"ok" if ok else "bad"}">{icon("check" if ok else "x", 14)}'
            f'{yes if ok else no}</span>')


def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40]


def section(no: str, title: str, sub: str = "", anchor: str | None = None):
    """Section heading inside a glass card.  Every section is a jump target (#sec-<anchor>); the
    badge copies a deep link to it."""
    anchor = anchor or _slug(f"{no}-{title}")
    s = f'<p class="sec-sub">{sub}</p>' if sub else ""
    t = html.escape(f"{no} {title}", quote=True)
    st.markdown(
        f'<div class="sec fs-anchor" id="sec-{anchor}" data-fs-section="{anchor}">'
        f'<a class="no" href="#sec-{anchor}" data-fs-copy="{anchor}" data-fs-title="{t}" translate="no" '
        f'title="Copy a link to this section" aria-label="Copy link to section {t}">{html.escape(no)}</a>'
        f'<h3>{html.escape(title)}</h3></div>{s}', unsafe_allow_html=True)


def metric(where, label: str, value: str, formula: str = "", numbers: str = "", ref: str = "", note: str = ""):
    """st.metric that opens a dialog with its formula, the numbers substituted and the source.
    formula / numbers / ref are HTML written in code (escape any user text before passing it)."""
    _mx["n"] += 1
    with where.container(key=f"mx_{_mx['n']}"):
        st.metric(label, value)
        if formula or numbers or ref:
            rows = "".join(f"<dt>{k}</dt><dd class='{c}'>{v}</dd>" for k, c, v in
                           (("Formula", "f", formula), ("With your numbers", "n", numbers),
                            ("Source", "r", ref), ("Note", "x", note)) if v)
            st.markdown(f'<div class="fs-why" hidden><div class="fs-why-h">{html.escape(label)}</div>'
                        f'<div class="fs-why-v">{html.escape(value)}</div><dl>{rows}</dl></div>',
                        unsafe_allow_html=True)


def toc():
    """Placeholder filled by interactions.js with the sections of the current tab."""
    st.markdown('<nav class="fs-toc" aria-label="Sections on this tab"></nav>', unsafe_allow_html=True)


def shortcuts_hint():
    st.markdown('<div class="fs-keys"><kbd>1</kbd>–<kbd>7</kbd> tabs · <kbd>/</kbd> inputs · '
                '<kbd>?</kbd> help · click a metric for its formula</div>', unsafe_allow_html=True)


def brand():
    st.markdown(f'<div class="brand"><span class="mark">{icon("layers", 20)}</span>Foundation Studio</div>'
                f'<div class="brand-sub">CE 402 · IIT Mandi · Group 1</div>', unsafe_allow_html=True)
