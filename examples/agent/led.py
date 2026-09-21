"""A single-file Gallery extension: literal metadata plus pure Python SVG geometry.

Register: python svgdrawer.py --add-symbol led --script examples/agent/led.py
The specification is read with ast.literal_eval; rendering executes trusted Python.
"""
SPEC = {
    'schema_version': 1,
    'id': 'led',
    'version': 1,
    'name': 'LED indicator',
    'category': 'hardware',
    'renderer': 'led',
    'description': 'An indicator with an adjustable diameter, label and color roles.',
    'tags': ['light', 'indicator', 'status', 'led'],
    'defaults': {},
    'controls': [
        {'key': 'diameter', 'label': 'Diameter', 'type': 'number',
         'default': 168, 'min': 80, 'max': 220, 'step': 1, 'unit': 'u'},
        {'key': 'label', 'label': 'Label', 'type': 'text',
         'default': 'ON', 'max_length': 6},
        {'key': 'show_label', 'label': 'Show label', 'type': 'boolean', 'default': True},
    ],
}


def render(drawing, params):
    d, p = drawing, params
    radius = p['diameter'] / 2
    d.ellipse('bezel', 128, 128, radius, radius, p['fill'], p['stroke'])
    d.ellipse('indicator', 128, 128, radius * 0.78, radius * 0.78, p['accent'], 'none', 0)
    if p['show_label']:
        d.label('label', 128, 137, p['label'], min(26, radius * 0.36), p['highlight'])
