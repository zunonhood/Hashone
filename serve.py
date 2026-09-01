from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
from urllib import request as urlrequest
from urllib import error as urlerror

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = int(os.environ.get("HASHONE_PORT", "4173"))

class LocalFrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        requested = self.path.split("?", 1)[0]
        if requested != "/api/permit":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 16_384:
            self.send_error(400, "Invalid request body")
            return

        body = self.rfile.read(length)
        upstream = urlrequest.Request(
            "https://www.therig.sh/api/permit",
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "https://www.therig.sh",
                "User-Agent": "Hashone-local-frontend/1.0",
            },
        )
        try:
            with urlrequest.urlopen(upstream, timeout=20) as response:
                payload = response.read()
                self.send_response(response.status)
                self.send_header("Content-Type", response.headers.get("Content-Type", "application/json"))
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except urlerror.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", exc.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (urlerror.URLError, TimeoutError):
            payload = b'{"error":"Permit service unavailable"}'
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    def do_GET(self):
        requested = self.path.split("?", 1)[0].split("#", 1)[0]
        local_path = ROOT / requested.lstrip("/")
        if requested != "/" and not local_path.exists():
            self.path = "/index.html"
        super().do_GET()

if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), LocalFrontendHandler)
    print(f"Hashone is running at http://{HOST}:{PORT}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
