"""Styles: loaded from brand-config.json, so the three looks come from one system with different settings."""
import json

from .core import hex_rgb
from .logo import Logo
from .paths import KIT
from .type import Face

_CFG = None


def config(reload=False):
    global _CFG
    if _CFG is None or reload:
        _CFG = json.loads((KIT / "brand-config.json").read_text())
    return _CFG


def films():
    """Film titles from films.txt (or brand-config.json if films.txt is missing) -> [(title, small note)]."""
    f = KIT / "films.txt"
    lines = [l.strip() for l in f.read_text().splitlines()] if f.exists() else config()["films"]
    out = []
    for l in lines:
        if not l or l.startswith("#"):
            continue
        note = ""
        if "(" in l and l.endswith(")"):
            l, note = l[: l.index("(")].strip(), l[l.index("(") + 1:-1].strip()
        out.append((l, note))
    return out


def slug(text):
    keep = "".join(c.lower() if c.isalnum() else "-" for c in text)
    while "--" in keep:
        keep = keep.replace("--", "-")
    return keep.strip("-")


class Style:
    _cache = {}

    def __new__(cls, key):
        if key not in cls._cache:
            self = super().__new__(cls)
            cfg = config()
            sc = cfg["styles"][key]
            self.key, self.cfg, self.name, self.number = key, sc, sc["name"], sc["number"]
            self.hex = {k: v["hex"] for k, v in sc["colours"].items()}
            self.colour_names = {k: v["name"] for k, v in sc["colours"].items()}
            self.rgb = {k: hex_rgb(v) for k, v in self.hex.items()}
            self.display = Face(sc["fonts"]["display"])
            self.text_family = sc["fonts"]["text"]
            self.tagline = sc["tagline"]
            self.grain_amount, self.grain_sigma, self.grain_lift = sc["grain"]["amount"], sc["grain"]["sigma"], sc["grain"]["lift"]
            self.bleed, self.rough, self.wear = sc["ink"]["bleed"], sc["ink"]["rough"], sc["ink"]["wear"]
            self.logo = Logo(cfg.get("logo_version", "geometric"))
            self.is_riso = sc["schemes"]["main"].get("mode") == "riso"
            cls._cache[key] = self
        return cls._cache[key]

    def text_face(self, weight=500):
        return Face(f"{self.text_family}-{weight}")

    def scheme(self, name="main"):
        sc = self.cfg["schemes"][name]
        out = {"mode": sc.get("mode", "flat"), "name": name}
        for role in ("field", "ink", "second"):
            out[role] = self.rgb[sc[role]]
            out[role + "_hex"] = self.hex[sc[role]]
            out[role + "_key"] = sc[role]
        for k in ("flood", "shadow", "misregister", "grain_gain"):
            if k in sc:
                out[k] = sc[k]
        return out


STYLES = ["red", "yellow", "wildcard"]
