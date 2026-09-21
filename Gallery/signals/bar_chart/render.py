"""Reusable performance chart icon for SVGDrawer."""
SPEC = {
    'schema_version': 1, 'id': 'bar_chart', 'version': 1,
    'name': 'Performance bar chart', 'category': 'signals', 'renderer': 'bar_chart',
    'description': 'An ascending engineering performance chart.', 'tags': ['performance', 'optimization'],
    'defaults': {'fill': '#FFFFFF'}, 'controls': [],
}


def render(drawing, params):
    d, p = drawing, params
    d.rect('frame', 18, 64, 220, 134, p['fill'], p['stroke'], rx=2)
    for index, height in enumerate((22, 43, 67, 91)):
        d.rect(f'bar-{index}', 42 + index * 44, 178 - height, 29, height, p['accent'], 'none', 0, 0)
    d.line('axis', 35, 180, 219, 180, p['stroke'], 3)
