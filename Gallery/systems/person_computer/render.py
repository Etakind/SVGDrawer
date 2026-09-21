"""A colored person using a fixed-color laptop, with independently styled parts."""

SPEC = {
    "schema_version": 1,
    "id": "person_computer",
    "version": 1,
    "name": "Person with computer",
    "category": "systems",
    "renderer": "person_computer",
    "description": "A person behind a laptop; fill changes only the person color.",
    "tags": ["person", "user", "computer", "terminal"],
    "defaults": {
        "fill": "#2878B5",
        "accent": "#A8DDF6",
        "stroke": "#213644",
        "highlight": "#DEE9ED",
        "stroke_width": 4,
    },
    "controls": [],
}


def render(drawing, params):
    """Keep the laptop geometry and palette independent of the person fill."""
    drawing.ellipse("person-head", 128, 53, 25, 25, params["fill"], "none", 0)
    drawing.path(
        "person-body",
        "M 65 162 V 128 C 65 76 191 76 191 128 V 162 Z",
        params["fill"], "none", 0, center=(128, 121),
    )
    drawing.rect("computer-bezel", 49, 130, 158, 91,
                 params["stroke"], params["stroke"], params["stroke_width"], 4)
    drawing.rect("computer-screen", 56, 137, 144, 77,
                 params["accent"], "none", 0, 1)
    drawing.path("computer-reflection", "M 56 137 H 200 V 150 Z",
                 params["highlight"], "none", 0)
    drawing.path("computer-base", "M 49 222 H 207 L 223 237 H 33 Z",
                 params["highlight"], params["stroke"], params["stroke_width"])
    drawing.line("computer-keyboard", 65, 227, 191, 227, params["stroke"], 2)
    drawing.line("computer-trackpad", 114, 233, 142, 233, params["stroke"], 2)
