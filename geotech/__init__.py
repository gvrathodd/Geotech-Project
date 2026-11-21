"""geotech – calculation core for the CE 402 shallow-foundation platform.

Every equation carries a comment naming its source (code clause or textbook).
The full reference list is in SOURCES.md.  All quantities are SI:
lengths m, settlements m (shown as mm in the interface), stresses kPa,
unit weights kN/m3, forces kN, moments kN*m, angles in degrees at the API.
"""

GAMMA_W = 9.81  # unit weight of water, kN/m3
KGCM2_TO_KPA = 98.0665  # 1 kg/cm2 = 98.0665 kPa (exact, 1 kgf = 9.80665 N)
CM2S_TO_M2YR = 1e-4 * 365.25 * 24 * 3600  # 1 cm2/s = 3155.76 m2/yr
