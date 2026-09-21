"""Reusable red Vitis-style tool symbol for the supplied reference diagram."""

SPEC = {
    "schema_version": 1,
    "id": "vitis_symbol",
    "version": 1,
    "name": "Vitis HLS tool symbol",
    "category": "systems",
    "renderer": "vitis_symbol",
    "description": "A red tile and white angular tool mark, without a wordmark.",
    "tags": ["eda", "hls"],
    "defaults": {"fill": "#E91822", "highlight": "#FFFFFF", "stroke": "none"},
    "controls": [],
}


def render(drawing, params):
    drawing.rect("tile", 27, 17, 202, 222, params["fill"], "none", 0, 12)
    drawing.path("upper-mark", "M 169 30 L 87 37 L 74 113 L 126 81 L 150 88 L 180 63 Z", params["highlight"], "none", 0)
    drawing.path("lower-mark", "M 124 98 L 181 138 L 140 194 L 161 227 L 72 214 L 47 162 L 86 128 L 75 162 L 114 185 L 139 151 L 99 127 Z", params["highlight"], "none", 0)
