#!/usr/bin/env python3
"""Local-only SVGDrawer gallery. Python 3.10+. No required dependencies.

    python server.py
    python server.py --port 8766 --no-browser

Builds from source on every start. The optional CairoSVG package enables
Python-side PNG conversion; the browser can rasterize the same SVG without it.
"""
from __future__ import annotations
import argparse
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlparse
import webbrowser
from build import build
from engine import handle_request

ROOT = Path(__file__).resolve().parent
try:
    import cairosvg
except (ImportError, OSError):
    cairosvg = None


class Handler(BaseHTTPRequestHandler):
    server_version = 'SVGDrawer/3.0'

    def log_message(self, fmt, *args):
        if len(args) > 1 and str(args[1]) not in ('200', '204', '304'):
            super().log_message(fmt, *args)

    def respond(self, status, content, content_type='application/json; charset=utf-8'):
        data = content if isinstance(content, bytes) else json.dumps(content, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass  # The user may close the preview while a render finishes.

    def local_request(self):
        hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        return self.headers.get('Host') in hosts and self.headers.get('Origin') in {None, *('http://' + h for h in hosts)}

    def do_GET(self):
        if not self.local_request():
            self.respond(403, {'error': 'Local requests only.'}); return
        route = urlparse(self.path).path
        if route == '/api/health':
            self.respond(200, {'app': 'svgdrawer', 'version': '3.0.0', 'png': cairosvg is not None})
        elif route in ('/', '/index.html'):
            self.respond(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif route == '/favicon.ico':
            self.respond(204, b'', 'image/x-icon')
        else:
            self.respond(404, {'error': 'Not found.'})

    def do_POST(self):
        if not self.local_request():
            self.respond(403, {'error': 'Local requests only.'}); return
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            self.respond(415, {'error': 'Expected application/json.'}); return
        route = urlparse(self.path).path
        if route not in ('/api/render', '/api/png'):
            self.respond(404, {'error': 'Not found.'}); return
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 12_000_000:
                raise ValueError('Request must be between 1 byte and 12 MB.')
            payload = json.loads(self.rfile.read(size).decode('utf-8'))
            if route == '/api/render':
                self.respond(200, handle_request(payload)); return
            if cairosvg is None:
                raise ValueError('CairoSVG is not installed. Use the browser PNG renderer or install CairoSVG and restart.')
            if not isinstance(payload, dict):
                raise ValueError('Request must be an object.')
            result = handle_request(dict(payload, action='export'))
            scale = float(payload.get('scale', 2))
            if not math.isfinite(scale) or not 1 <= scale <= 4:
                raise ValueError('PNG scale must be between 1 and 4.')
            width, height = round(result['width']*scale), round(result['height']*scale)
            if max(width, height) > 8192 or width*height > 50_000_000:
                raise ValueError('PNG limit: 8192 pixels per side and 50 megapixels.')
            png = cairosvg.svg2png(bytestring=result['svg'].encode('utf-8'), output_width=width, output_height=height)
            self.respond(200, png, 'image/png')
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, RecursionError) as exc:
            self.respond(400, {'error': str(exc)[:600]})
        except Exception as exc:
            self.respond(500, {'error': 'Rendering failed: ' + str(exc)[:350]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        raise SystemExit('Port must be between 0 and 65535.')
    try:
        path, symbols, categories = build()
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except (ValueError, OSError) as exc:
        raise SystemExit(f'Could not start: {exc}') from exc
    server.daemon_threads = True
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'\n  SVGDrawer · Gallery edition\n  {url}\n  {symbols} symbols / {categories} categories\n  SVG: Python\n  PNG: {"Python / CairoSVG or browser" if cairosvg else "Browser (CairoSVG optional)"}\n  Press Ctrl+C to stop.\n', flush=True)
    if not args.no_browser:
        timer = threading.Timer(.6, lambda: webbrowser.open(url)); timer.daemon = True; timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
