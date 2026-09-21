"""Compact three-lobed Vivado-style symbol traced from the supplied figure."""

SPEC = {
    "schema_version": 1,
    "id": "vivado_symbol",
    "version": 1,
    "name": "Vivado tool symbol",
    "category": "systems",
    "renderer": "vivado_symbol",
    "description": "Three geometric lobes used beside a native Vivado text label.",
    "tags": ["eda", "vivado"],
    "defaults": {"fill": "#C8CB24", "accent": "#C8CB24", "stroke": "none"},
    "controls": [],
}


def render(drawing, params):
    drawing.path("upper", "M 105 30 L 151 30 L 168 107 L 133 126 L 99 104 Z", params["fill"], "none", 0)
    drawing.path("right", "M 151 134 L 181 107 L 235 143 L 216 183 L 148 178 Z", params["fill"], "none", 0)
    drawing.path("left", "M 111 127 L 116 172 L 58 205 L 22 171 L 78 122 Z", params["fill"], "none", 0)
