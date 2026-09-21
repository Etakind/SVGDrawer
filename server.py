#!/usr/bin/env python3
"""Local Python SVGDrawer application. Run python start.py in the activated Conda environment."""
from __future__ import annotations
import argparse
import json
import math
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlparse
import webbrowser
from engine import gallery
from engine.png import converter, svg_to_png
from cli.api import manage
from cli.trash import list_trash
from cli.archives import backup_bytes
from cli.common import UserError
from engine.gallery import GalleryBusy
from engine import handle_request

ROOT = Path(__file__).resolve().parent
ACCESS = threading.RLock()
try:
    cairosvg = converter()
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
        if route in ('/api/gallery', '/api/trash', '/api/backup'):
            try:
                with ACCESS:
                    if route == '/api/gallery':
                        self.respond(200, {**gallery().metadata(), 'revision': (ROOT / 'Gallery/catalog.json').stat().st_mtime_ns})
                    elif route == '/api/trash':
                        self.respond(200, list_trash())
                    else:
                        self.respond(200, backup_bytes(), 'application/zip')
            except (ValueError, OSError, UserError, GalleryBusy) as exc:
                self.respond(409, {'error': str(exc)})
        elif route == '/api/health':
            self.respond(200, {'app': 'svgdrawer', 'version': '3.0.0', 'png': cairosvg is not None})
        elif route in ('/', '/index.html'):
            self.respond(200, (ROOT / 'app' / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif route.startswith('/app/') and route[5:] in {'styles.css', 'app.js', 'browser.js', 'detail.js', 'library.js', 'init.js', 'runtime.js'}:
            kind = 'text/css' if route.endswith('.css') else 'text/javascript'
            self.respond(200, (ROOT / route[1:]).read_bytes(), kind + '; charset=utf-8')
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
        if route not in ('/api/render', '/api/png', '/api/manage'):
            self.respond(404, {'error': 'Not found.'}); return
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 180_000_000:
                raise ValueError('Request must be between 1 byte and 180 MB.')
            payload = json.loads(self.rfile.read(size).decode('utf-8'))
            if route == '/api/manage':
                with ACCESS:
                    result = manage(payload)
                self.respond(200, result); return
            if route == '/api/render':
                with ACCESS:
                    result = handle_request(payload)
                self.respond(200, result); return
            if cairosvg is None:
                raise ValueError('Python PNG is unavailable. Run the application with its activated Conda environment.')
            if not isinstance(payload, dict):
                raise ValueError('Request must be an object.')
            with ACCESS:
                result = handle_request(dict(payload, action='export'))
            scale = float(payload.get('scale', 2))
            if not math.isfinite(scale) or not 1 <= scale <= 4:
                raise ValueError('PNG scale must be between 1 and 4.')
            width, height = round(result['width']*scale), round(result['height']*scale)
            if max(width, height) > 8192 or width*height > 50_000_000:
                raise ValueError('PNG limit: 8192 pixels per side and 50 megapixels.')
            png = svg_to_png(result['svg'].encode('utf-8'), width, height)
            self.respond(200, png, 'image/png')
        except (UserError, GalleryBusy, ValueError, TypeError, KeyError, UnicodeDecodeError, RecursionError) as exc:
            self.respond(400, {'schema_version': 2, 'ok': False, 'error': {'code': getattr(exc, 'code', 'invalid_input'), 'message': str(exc)[:600]}} if route == '/api/manage' else {'error': str(exc)[:600]})
        except Exception as exc:
            self.respond(500, {'error': 'Rendering failed: ' + str(exc)[:350]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=9178)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        raise SystemExit('Port must be between 0 and 65535.')
    try:
        gal = gallery()
        symbols, categories = len(gal.symbols), len(gal.categories)
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except (ValueError, OSError) as exc:
        raise SystemExit(f'Could not start: {exc}') from exc
    server.daemon_threads = True
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'\n  SVGDrawer · Gallery edition\n  {url}\n  {symbols} symbols / {categories} categories\n  SVG: Python\n  PNG: {"Python / CairoSVG" if cairosvg else "Unavailable (use .venv Python)"}\n  Press Ctrl+C to stop.\n', flush=True)
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
