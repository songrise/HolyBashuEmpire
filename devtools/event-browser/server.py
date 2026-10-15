"""Serve the read-only event viewer on localhost. Reload indexes current source files."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import threading
from urllib.parse import urlsplit
from catalog import build_catalog
from drafts import add_drafts

HERE = Path(__file__).resolve().parent

def default_mod():
    for p in (HERE.parents[1] / 'mod/holy_bashu_empire',
              HERE.parents[1] / 'work/event-expansion/mod/holy_bashu_empire'):
        if (p / 'in_game/events').is_dir():
            return p
    raise ValueError('Pass --mod-path pointing to the mod folder')

def serve(mod, port):
    lock = threading.Lock()
    root = mod.resolve().parents[1]
    def current_catalog():
        return add_drafts(build_catalog(mod), root)
    state = {'data': current_catalog()}
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path in ('/api/catalog', '/api/refresh', '/api/health'):
                try:
                    with lock:
                        if path == '/api/refresh':
                            state['data'] = current_catalog()
                        result = {'stats': state['data']['stats'], 'modPath': str(mod)} if path == '/api/health' else state['data']
                        payload = json.dumps(result, ensure_ascii=False).encode('utf-8')
                    self.send_response(200)
                except Exception as exc:
                    payload = json.dumps({'error': str(exc)}, ensure_ascii=False).encode('utf-8')
                    self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if path.startswith(('/art/', '/ending-art/')):
                is_ending = path.startswith('/ending-art/')
                name = path.split('/', 2)[2]
                if not name.endswith('.png') or '/' in name or '\\' in name or '..' in name:
                    self.send_error(404); return
                image = root / ('assets/event_endings_v031' if is_ending else 'assets/event_expansion') / name
                if not image.is_file():
                    self.send_error(404); return
                payload = image.read_bytes()
                self.send_response(200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers(); self.wfile.write(payload); return
            if path not in ('/', '/index.html', '/app.js', '/style.css', '/favicon.svg'):
                self.send_error(404)
                return
            super().do_GET()
        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
            super().end_headers()
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, directory=str(HERE)))
    print(f'Local: http://127.0.0.1:{port}', flush=True)
    print(json.dumps(state['data']['stats']), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mod-path', type=Path)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--export', type=Path, help='Write a catalogue snapshot without starting a server')
    args = parser.parse_args()
    mod = args.mod_path or default_mod()
    if args.export:
        args.export.write_text(json.dumps(build_catalog(mod), ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        serve(mod, args.port)
