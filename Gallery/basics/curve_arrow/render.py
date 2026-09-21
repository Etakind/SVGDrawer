"""A single parameterized curved arrow for editable diagram connections."""

import math


SPEC = {
    "schema_version": 1,
    "id": "curve_arrow",
    "version": 1,
    "name": "Customizable curved arrow",
    "category": "basics",
    "renderer": "curve_arrow",
    "description": "Single curved arrow with adjustable length, bend, width, head and angle.",
    "tags": ["arrow", "curve", "connector", "cycle"],
    "defaults": {"accent": "#2676B9", "stroke_width": 8},
    "controls": [
        {"key": "length", "label": "Arrow length", "type": "number",
         "default": 160, "min": 60, "max": 180, "step": 1},
        {"key": "bend", "label": "Curve bend", "type": "number",
         "default": 45, "min": -65, "max": 65, "step": 1},
        {"key": "head_length", "label": "Head length", "type": "number",
         "default": 23, "min": 10, "max": 32, "step": 1},
        {"key": "head_width", "label": "Head width", "type": "number",
         "default": 25, "min": 10, "max": 34, "step": 1},
        {"key": "angle", "label": "Rotation angle", "type": "number",
         "default": 0, "min": -180, "max": 180, "step": 1},
    ],
}


def render(drawing, params):
    """Rotate both the curve and its tangent-aligned head about the canvas center."""
    length = params["length"]
    bend = params["bend"]
    angle = math.radians(params["angle"])

    def point(x, y):
        return (128 + x * math.cos(angle) - y * math.sin(angle),
                128 + x * math.sin(angle) + y * math.cos(angle))

    def pair(position):
        return f"{position[0]:.5f} {position[1]:.5f}"

    tangent_length = math.hypot(length / 3, bend)
    tangent_x = length / 3 / tangent_length
    tangent_y = bend / tangent_length
    base_x = length / 2 - params["head_length"] * tangent_x
    base_y = -params["head_length"] * tangent_y
    half_width = params["head_width"] / 2
    start = point(-length / 2, 0)
    control_one = point(-length / 6, -bend)
    control_two = point(length / 6, -bend)
    shaft_end = point(base_x + tangent_x * 3, base_y + tangent_y * 3)
    tip = point(length / 2, 0)
    side_one = point(base_x - half_width * tangent_y, base_y + half_width * tangent_x)
    side_two = point(base_x + half_width * tangent_y, base_y - half_width * tangent_x)
    drawing.path("shaft", f"M {pair(start)} C {pair(control_one)} {pair(control_two)} {pair(shaft_end)}",
                 "none", params["accent"], params["stroke_width"])
    drawing.path("head", f"M {pair(tip)} L {pair(side_one)} L {pair(side_two)} Z",
                 params["accent"], "none", 0)
