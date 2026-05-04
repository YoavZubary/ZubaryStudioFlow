#!/usr/bin/env python3
import json, os, socket, mimetypes
from http.server import HTTPServer, SimpleHTTPRequestHandler

SYNC_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sync-data.json')
AUDIO_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audio-files')
os.makedirs(AUDIO_DIR, exist_ok=True)

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return 'localhost'

def _find_audio(file_id):
    for fname in os.listdir(AUDIO_DIR):
        base = os.path.splitext(fname)[0]
        if base == file_id:
            return os.path.join(AUDIO_DIR, fname), fname
    return None, None

class StudioHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/sync':
            try:
                with open(SYNC_FILE) as f:
                    stored = json.load(f)
            except:
                stored = {}
            stored['serverIp'] = local_ip()
            self._json(200, stored)

        elif self.path.startswith('/api/audio/'):
            file_id = self.path[len('/api/audio/'):].split('?')[0]
            fpath, fname = _find_audio(file_id)
            if not fpath:
                self._json(404, {'error': 'not found'})
                return
            mime = mimetypes.guess_type(fname)[0] or 'audio/mpeg'
            size = os.path.getsize(fpath)
            # Range support (required for iOS Safari seeking)
            range_header = self.headers.get('Range', '')
            start, end = 0, size - 1
            if range_header.startswith('bytes='):
                parts = range_header[6:].split('-')
                start = int(parts[0]) if parts[0] else 0
                end   = int(parts[1]) if parts[1] else size - 1
            length = end - start + 1
            with open(fpath, 'rb') as f:
                f.seek(start)
                data = f.read(length)
            code = 206 if range_header else 200
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', length)
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            if range_header:
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            self.end_headers()
            self.wfile.write(data)

        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/sync':
            n = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(n).decode()
            with open(SYNC_FILE, 'w') as f:
                f.write(body)
            self._json(200, {'ok': True})

        elif self.path.startswith('/api/audio/'):
            file_id = self.path[len('/api/audio/'):].split('?')[0]
            ct = self.headers.get('Content-Type', 'audio/mpeg').split(';')[0].strip()
            fname = self.headers.get('X-Filename', '')
            if fname:
                ext = os.path.splitext(fname)[1] or '.mp3'
            else:
                ext_map = {
                    'audio/mpeg': '.mp3', 'audio/mp4': '.m4a', 'audio/x-m4a': '.m4a',
                    'audio/wav': '.wav', 'audio/ogg': '.ogg', 'audio/flac': '.flac',
                    'audio/aiff': '.aiff', 'audio/x-aiff': '.aiff',
                }
                ext = ext_map.get(ct, mimetypes.guess_extension(ct) or '.mp3')
            n = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(n)
            fpath = os.path.join(AUDIO_DIR, file_id + ext)
            with open(fpath, 'wb') as f:
                f.write(data)
            self._json(200, {'ok': True})

        else:
            self._json(404, {'error': 'not found'})

    def do_OPTIONS(self):
        self.send_response(200)
        for h, v in [('Access-Control-Allow-Origin', '*'),
                     ('Access-Control-Allow-Methods', 'GET,POST,OPTIONS'),
                     ('Access-Control-Allow-Headers', 'Content-Type,X-Filename,Range')]:
            self.send_header(h, v)
        self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

if __name__ == '__main__':
    port = 3344
    ip = local_ip()
    server = HTTPServer(('0.0.0.0', port), StudioHandler)
    print(f'Studio Flow: http://localhost:{port}')
    print(f'מהטלפון (אותה WiFi): http://{ip}:{port}')
    server.serve_forever()
