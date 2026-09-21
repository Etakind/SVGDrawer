"""Example for agents: run independent exports using argv arrays, never shell=True.

Run from anywhere: python /path/to/SVGDrawer/examples/agent/batch_export.py
Outputs go under the caller's exports/ directory. Existing files are not replaced.
"""
from pathlib import Path
import json
import subprocess
import sys

CLI = Path(__file__).resolve().parents[2] / 'svgdrawer.py'
JOBS = [
    ('chip', {'pins': 10, 'label': 'DSP'}),
    ('folder', {}),
    ('waveform', {'wave_type': 'sine', 'cycles': 5}),
]


def main():
    for ident, params in JOBS:
        result = subprocess.run(
            [sys.executable, str(CLI), '--create', ident, '--params', json.dumps(params),
             '--color-sets', 'mint', '--output', str(Path('exports') / ('batch-' + ident + '.svg')), '--json'],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            error = json.loads(result.stderr)['error']
            print(f'{ident}: {error["code"]}: {error["message"]}', file=sys.stderr)
            return result.returncode
        data = json.loads(result.stdout)['data']
        print('\n'.join(data['files']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
