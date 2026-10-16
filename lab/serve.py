"""Serve the explorer; optionally enable trusted local C/Python comparisons."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from lab.compare import compare, CompareError

ROOT = Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def valid_host(self):
        return self.headers.get('Host') == '127.0.0.1:%s' % self.server.server_port

    def send_json(self, status, body):
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if not self.valid_host():
            return self.send_error(403, 'Use the printed 127.0.0.1 address.')
        if self.path == '/api/status':
            return self.send_json(200, {'enabled': self.server.execution_enabled,
                                      'token': self.server.execution_token if self.server.execution_enabled else None})
        return super().do_GET()

    def do_POST(self):
        origin = 'http://127.0.0.1:%s' % self.server.server_port
        if (not self.valid_host() or self.headers.get('Origin') != origin or
                not self.server.execution_enabled or
                not secrets.compare_digest(self.headers.get('X-ReverseLab-Token', ''), self.server.execution_token)):
            return self.send_json(403, {'error': 'Execution is disabled or this request is not from the local workbench.'})
        if self.path != '/api/compare':
            return self.send_error(404)
        if self.headers.get('Content-Type') != 'application/json' or self.headers.get('Transfer-Encoding'):
            return self.send_json(400, {'error': 'Send a JSON request with a Content-Length.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 1 <= length <= 1024 * 1024:
                return self.send_json(413, {'error': 'Request must be between 1 byte and 1 MiB.'})
        except ValueError:
            return self.send_json(400, {'error': 'Invalid Content-Length.'})
        if not self.server.execution_lock.acquire(blocking=False):
            return self.send_json(409, {'error': 'A comparison is already running. Wait for it to finish.'})
        try:
            self.connection.settimeout(10)
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict) or payload.get('trusted') is not True:
                raise CompareError('Confirm that you trust these programs before running them.')
            result = compare(payload.get('reference'), payload.get('candidate'), payload.get('inputs'),
                             payload.get('function', 'evaluate'), payload.get('count', 0), payload.get('seed', 42),
                             str(payload.get('referenceName', 'reference.c')),
                             str(payload.get('candidateName', 'candidate.py')))
            self.send_json(200, result)
        except (ValueError, OSError) as error:
            self.send_json(400, {'error': str(error), 'stage': getattr(error, 'stage', 'input')})
        finally:
            self.server.execution_lock.release()

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4173)
    parser.add_argument('--production', action='store_true', help='Serve the validated dist export')
    parser.add_argument('--execute', action='store_true', help='Enable trusted local programs; this is not a security sandbox')
    args = parser.parse_args()
    directory = ROOT / ('dist' if args.production else 'web')
    if not (directory / 'index.html').exists():
        parser.error('Explorer missing; run python3 -m lab.webbuild for a production export')
    with ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(directory))) as server:
        server.execution_enabled = args.execute
        server.execution_token = secrets.token_urlsafe(32)
        server.execution_lock = threading.Lock()
        print(f'ReverseLab: http://127.0.0.1:{args.port}' + ('/compare.html (trusted local execution)' if args.execute else ' (recorded examples)'), flush=True)
        if args.execute:
            print('Run only code you trust. Programs have your account permissions; time/output limits are not a security sandbox.', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nStopped.')

if __name__ == '__main__':
    main()
