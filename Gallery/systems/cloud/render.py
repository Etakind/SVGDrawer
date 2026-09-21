"""Reusable cloud deployment icon for SVGDrawer."""
SPEC = {
    'schema_version': 1, 'id': 'cloud', 'version': 1,
    'name': 'Deployment cloud', 'category': 'systems', 'renderer': 'cloud',
    'description': 'A compact cloud silhouette.', 'tags': ['cloud', 'deployment'],
    'defaults': {}, 'controls': [],
}


def render(drawing, params):
    drawing.path('cloud', 'M 55 183 C 10 180 13 115 58 111 C 58 57 130 46 150 91 C 180 69 217 95 211 123 C 256 132 242 183 207 183 Z', params['accent'], params['stroke'], params['stroke_width'])
