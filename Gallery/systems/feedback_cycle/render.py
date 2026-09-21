"""Five separate feedback-cycle arrows with clear gaps for native PPT labels."""

SPEC = {
    "schema_version": 1,
    "id": "feedback_cycle",
    "version": 1,
    "name": "Five-stage feedback cycle",
    "category": "systems",
    "renderer": "feedback_cycle",
    "description": "Five curved blue arrows surrounding a clear center and five label gaps.",
    "tags": ["cycle", "feedback", "iteration"],
    "defaults": {"accent": "#327FB5", "stroke_width": 9},
    "controls": [],
}


def render(drawing, params):
    # Each open arc ends before the next label gap; no text is baked into the icon.
    arrows = [
        ("upper-right", "M 165 38 C 181 42 191 51 199 61", "M 190 64 L 211 72 L 204 49 Z"),
        ("lower-right", "M 214 115 Q 216 132 207 145", "M 199 137 L 199 161 L 219 148 Z"),
        ("bottom", "M 144 185 Q 128 194 111 190", "M 114 180 L 93 187 L 110 201 Z"),
        ("lower-left", "M 44 161 Q 32 147 32 132", "M 22 136 L 32 114 L 42 135 Z"),
        ("upper-left", "M 50 73 Q 62 49 82 42", "M 77 32 L 100 36 L 83 53 Z"),
    ]
    for name, arc, head in arrows:
        drawing.path(f"{name}-arc", arc, "none", params["accent"], params["stroke_width"])
        drawing.path(f"{name}-head", head, params["accent"], "none", 0)
