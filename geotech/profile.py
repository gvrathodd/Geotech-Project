"""P1 - Layered soil profile and in-situ vertical stresses.

Stress definitions: total stress sigma_v = sum(gamma_i * h_i); pore pressure
u = gamma_w * (z - z_w) below the water table (hydrostatic); effective stress
sigma'_v = sigma_v - u  (Terzaghi's effective-stress principle; e.g. Das,
Principles of Geotechnical Engineering, chapter "In situ stresses").
Above the water table the moist unit weight is used, below it the saturated one.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import List, Optional

from . import GAMMA_W

GRANULAR = "Granular"
COHESIVE = "Cohesive"
SOIL_TYPES = (GRANULAR, COHESIVE)
HISTORY_MODES = ("NC", "OCR", "POP", "sigma_p")  # how pre-consolidation stress is given


@dataclass
class Layer:
    top: float  # m below ground level
    bottom: float  # m below ground level
    description: str = ""
    soil_type: str = GRANULAR  # 'Granular' or 'Cohesive'
    gamma_moist: float = 18.0  # kN/m3, above water table
    gamma_sat: float = 20.0  # kN/m3, below water table
    c_eff: float = 0.0  # c', kPa (drained)
    phi_eff: float = 30.0  # phi', degrees (drained)
    cu: float = 0.0  # undrained shear strength, kPa (phi_u = 0 analysis)
    E: float = 20000.0  # Young's modulus for Schmertmann method, kPa
    Cc: float = 0.0  # compression index (-)
    Cs: float = 0.0  # swelling / recompression index (-)
    e0: float = 0.8  # initial void ratio (-)
    history: str = "NC"  # 'NC' | 'OCR' | 'POP' | 'sigma_p'
    history_value: float = 1.0  # OCR (-), POP (kPa) or sigma'_p (kPa) depending on mode
    cv: float = 1.0  # coefficient of consolidation, m2/yr
    drainage: str = "Double"  # 'Double' | 'Top only' | 'Bottom only'
    dilatancy: bool = False  # True for saturated fine sand / silt (IS 2131 dilatancy correction)
    undrained: bool = False  # True -> use cu with phi = 0 in bearing capacity

    @property
    def thickness(self) -> float:
        return self.bottom - self.top

    def sigma_p(self, sigma_eff0: float) -> float:
        """Pre-consolidation stress (kPa) at a point with in-situ sigma'_v0 (kPa)."""
        if self.history == "OCR":  # sigma'_p = OCR * sigma'_v0 (definition of OCR)
            return max(self.history_value, 1.0) * sigma_eff0
        if self.history == "POP":  # sigma'_p = sigma'_v0 + POP (pre-overburden pressure)
            return sigma_eff0 + max(self.history_value, 0.0)
        if self.history == "sigma_p":  # constant measured sigma'_p
            return max(self.history_value, sigma_eff0)
        return sigma_eff0  # NC: sigma'_p = sigma'_v0


@dataclass
class SPTRecord:
    depth: float  # m bgl
    N: float  # observed blows per 300 mm
    refusal: bool = False  # True when 50 blows gave < 300 mm penetration


@dataclass
class SoilProfile:
    layers: List[Layer]
    gwt_measured: float = 100.0  # m bgl, water level at time of SPT/boring
    gwt_design: float = 100.0  # m bgl, design (e.g. highest seasonal) water level
    spt: List[SPTRecord] = field(default_factory=list)
    name: str = ""

    # ---------------------------------------------------------------- checks
    def validate(self) -> List[str]:
        msgs = []
        if not self.layers:
            return ["The profile has no layers."]
        ls = sorted(self.layers, key=lambda l: l.top)
        if abs(ls[0].top) > 1e-6:
            msgs.append(f"First layer starts at {ls[0].top} m, not at ground level (0 m).")
        for a, b in zip(ls, ls[1:]):
            if abs(a.bottom - b.top) > 1e-6:
                msgs.append(f"Gap/overlap between {a.bottom} m and {b.top} m.")
        for l in ls:
            if l.bottom <= l.top:
                msgs.append(f"Layer '{l.description}' has bottom <= top.")
            if l.gamma_sat < l.gamma_moist - 1e-9:
                msgs.append(f"Layer '{l.description}': saturated unit weight is less than moist.")
            if l.soil_type == COHESIVE and l.Cc > 0 and l.Cs > l.Cc:
                msgs.append(f"Layer '{l.description}': Cs > Cc.")
        return msgs

    @property
    def depth(self) -> float:
        return max(l.bottom for l in self.layers)

    def sorted_layers(self) -> List[Layer]:
        return sorted(self.layers, key=lambda l: l.top)

    def layer_at(self, z: float) -> Layer:
        """Layer containing depth z (m bgl); the last layer is extended downward."""
        ls = self.sorted_layers()
        for l in ls:
            if l.top - 1e-9 <= z < l.bottom - 1e-9:
                return l
        return ls[-1] if z >= ls[-1].bottom - 1e-9 else ls[0]

    # --------------------------------------------------------------- stresses
    def stresses(self, z: float, gwt: Optional[float] = None):
        """Return (sigma_v, u, sigma'_v) in kPa at depth z (m) for water table gwt (m bgl).

        sigma_v = sum gamma*h with gamma_moist above / gamma_sat below the water table;
        u = gamma_w (z - z_w) for z > z_w (hydrostatic); sigma' = sigma - u (Terzaghi).
        """
        gwt = self.gwt_design if gwt is None else gwt
        z = max(z, 0.0)
        sig = 0.0
        ls = self.sorted_layers()
        for i, l in enumerate(ls):
            top = l.top
            bot = l.bottom if i < len(ls) - 1 else max(l.bottom, z)  # extend last layer
            a, b = top, min(bot, z)
            if b <= a:
                continue
            # part above the water table
            a1, b1 = a, min(b, gwt)
            if b1 > a1:
                sig += l.gamma_moist * (b1 - a1)
            # part below the water table
            a2, b2 = max(a, gwt), b
            if b2 > a2:
                sig += l.gamma_sat * (b2 - a2)
        u = GAMMA_W * max(z - gwt, 0.0)
        return sig, u, sig - u

    def sigma_eff(self, z: float, gwt: Optional[float] = None) -> float:
        return self.stresses(z, gwt)[2]

    def sigma_tot(self, z: float, gwt: Optional[float] = None) -> float:
        return self.stresses(z, gwt)[0]

    # -------------------------------------------------------------- serialise
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gwt_measured": self.gwt_measured,
            "gwt_design": self.gwt_design,
            "layers": [asdict(l) for l in self.sorted_layers()],
            "spt": [asdict(s) for s in self.spt],
        }

    @staticmethod
    def from_dict(d: dict) -> "SoilProfile":
        layers = [Layer(**l) for l in d.get("layers", [])]
        spt = [SPTRecord(**s) for s in d.get("spt", [])]
        return SoilProfile(
            layers=layers,
            gwt_measured=float(d.get("gwt_measured", 100.0)),
            gwt_design=float(d.get("gwt_design", 100.0)),
            spt=spt,
            name=d.get("name", ""),
        )
