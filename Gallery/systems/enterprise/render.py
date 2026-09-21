"""Reusable enterprise building icon for SVGDrawer."""
SPEC = {
    'schema_version': 1, 'id': 'enterprise', 'version': 1,
    'name': 'Enterprise building', 'category': 'systems', 'renderer': 'enterprise',
    'description': 'Office towers with window details.', 'tags': ['enterprise', 'building'],
    'defaults': {}, 'controls': [],
}


def render(drawing, params):
    d, p = drawing, params
    d.path('tower', 'M 82 223 V 48 L 150 22 L 178 42 V 223 Z', p['accent'], p['stroke'])
    d.path('wing', 'M 31 223 V 106 L 74 87 V 223 Z', p['fill'], p['stroke'])
    d.rect('annex', 181, 132, 40, 91, p['fill'], p['stroke'], rx=0)
    for col in range(3):
        for row in range(7):
            d.rect(f'window-{col}-{row}', 97 + col * 19, 63 + row * 20, 7, 11, p['highlight'], 'none', 0, 0)
    d.line('ground', 19, 227, 236, 227, p['stroke'], 6)
