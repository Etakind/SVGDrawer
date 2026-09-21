"""Reusable verification checklist icon for SVGDrawer."""
SPEC = {
    'schema_version': 1, 'id': 'checklist', 'version': 1,
    'name': 'Verification checklist', 'category': 'documents', 'renderer': 'checklist',
    'description': 'A verification document with check marks.', 'tags': ['verification', 'testbench'],
    'defaults': {'fill': '#FFFFFF'}, 'controls': [],
}


def render(drawing, params):
    d, p = drawing, params
    d.rect('page', 36, 20, 184, 216, p['fill'], p['stroke'], rx=3)
    for row in range(3):
        y = 63 + row * 60
        d.line(f'line-{row}', 60, y, 119, y, p['accent'], 8)
        d.line(f'detail-{row}', 60, y + 16, 98, y + 16, p['accent'], 4)
        d.path(f'check-{row}', f'M 149 {y+7} L 164 {y+22} L 197 {y-10}', 'none', p['accent'], 9)
