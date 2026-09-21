"""Git branch symbol drawn with SVGDrawer primitives, without a wordmark."""

SPEC = {
    "schema_version": 1,
    "id": "git_symbol",
    "version": 1,
    "name": "Git tool symbol",
    "category": "systems",
    "renderer": "git_symbol",
    "description": "An orange diamond with a white branching version-control graph.",
    "tags": ["eda", "git", "version-control"],
    "defaults": {"fill": "#F34F29", "highlight": "#FFFFFF", "stroke": "none"},
    "controls": [],
}


def render(drawing, params):
    drawing.path("diamond", "M 113 21 Q 128 6 143 21 L 235 113 Q 250 128 235 143 L 143 235 Q 128 250 113 235 L 21 143 Q 6 128 21 113 Z", params["fill"], "none", 0)
    drawing.path("branch", "M 89 49 L 113 73 L 113 190 M 113 87 L 173 147", "none", params["highlight"], 13)
    for name, x, y in [("root", 113, 84), ("tip", 113, 189), ("fork", 174, 148)]:
        drawing.ellipse(name, x, y, 18, 18, params["highlight"], "none", 0)
