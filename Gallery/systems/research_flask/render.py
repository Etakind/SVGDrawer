"""Reusable research flask icon for SVGDrawer."""
SPEC = {
    'schema_version': 1, 'id': 'research_flask', 'version': 1,
    'name': 'Research flask', 'category': 'systems', 'renderer': 'research_flask',
    'description': 'Laboratory flask with blue liquid.', 'tags': ['research', 'science'],
    'defaults': {}, 'controls': [],
}


def render(drawing, params):
    d, p = drawing, params
    d.path('glass', 'M 104 32 H 152 V 48 H 144 V 104 L 208 208 Q 219 229 194 229 H 62 Q 37 229 48 208 L 112 104 V 48 H 104 Z', p['highlight'], p['stroke'], 7)
    d.path('liquid', 'M 89 157 Q 115 146 139 159 Q 160 170 170 161 L 196 209 Q 201 217 190 217 H 66 Q 55 217 60 209 Z', p['accent'], 'none', 0)
    d.ellipse('bubble', 120, 179, 7, 7, p['highlight'], 'none', 0)
