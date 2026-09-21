"""Reusable academic cap icon for SVGDrawer."""
SPEC = {
    'schema_version': 1, 'id': 'graduate_cap', 'version': 1,
    'name': 'Graduation cap', 'category': 'systems', 'renderer': 'graduate_cap',
    'description': 'Academic mortarboard and tassel.', 'tags': ['academic', 'university'],
    'defaults': {'accent': '#304D70'}, 'controls': [],
}


def render(drawing, params):
    d, p = drawing, params
    d.path('base', 'M 59 128 V 174 Q 128 216 197 174 V 128 Z', p['accent'], p['stroke'])
    d.path('cap', 'M 18 100 L 128 48 L 238 100 L 128 155 Z', p['accent'], p['highlight'], 4)
    d.path('tassel', 'M 128 98 L 225 115 V 191', 'none', p['stroke'], 5)
    d.path('tassel-tip', 'M 220 180 L 216 202 H 233 L 229 180 Z', p['accent'], p['stroke'], 3)
