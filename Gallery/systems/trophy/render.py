"""Reusable competition trophy icon for SVGDrawer."""
SPEC = {
    'schema_version': 1, 'id': 'trophy', 'version': 1,
    'name': 'Competition trophy', 'category': 'systems', 'renderer': 'trophy',
    'description': 'A gold cup award.', 'tags': ['competition', 'award'],
    'defaults': {'accent': '#C26B08', 'stroke': '#9C4D00'}, 'controls': [],
}


def render(drawing, params):
    d, p = drawing, params
    d.path('handles', 'M 79 61 H 35 V 104 Q 38 144 88 143 M 177 61 H 221 V 104 Q 218 144 168 143', 'none', p['accent'], 12)
    d.path('cup', 'M 76 40 H 180 L 175 113 Q 174 162 139 169 V 200 H 167 V 223 H 89 V 200 H 117 V 169 Q 82 162 81 113 Z', p['accent'], p['stroke'], 4)
