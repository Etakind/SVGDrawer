"""Waveform tile used as the Icarus Verilog symbol in the supplied figure."""

SPEC = {
    "schema_version": 1,
    "id": "icarus_symbol",
    "version": 1,
    "name": "Icarus Verilog tool symbol",
    "category": "signals",
    "renderer": "icarus_symbol",
    "description": "A navy tile containing a light engineering waveform.",
    "tags": ["eda", "verilog", "simulation"],
    "defaults": {"fill": "#183B70", "highlight": "#E6F4FF", "stroke": "none"},
    "controls": [],
}


def render(drawing, params):
    drawing.rect("tile", 16, 24, 224, 208, params["fill"], "none", 0, 20)
    drawing.path("trace", "M 30 132 L 57 132 L 65 93 L 76 168 L 90 164 L 101 67 L 118 185 L 134 182 L 145 97 L 160 153 L 187 153 L 194 110 L 205 147 L 224 147", "none", params["highlight"], 7)
