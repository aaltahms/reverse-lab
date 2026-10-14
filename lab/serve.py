"""Serve only the read-only explorer on a loopback interface."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4173)
    parser.add_argument('--production', action='store_true', help='Serve the validated dist export')
    args = parser.parse_args()
    directory = ROOT / ('dist' if args.production else 'web')
    if not (directory / 'index.html').exists():
        parser.error('Explorer missing; run python3 -m lab.webbuild for a production export')
    with ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(directory))) as server:
        print(f'ReverseLab: http://127.0.0.1:{args.port} (read-only recording)', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\nStopped.')

if __name__ == '__main__':
    main()
