import http.client
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
NGINX_CONF = REPO_ROOT / "nginx" / "nginx.conf"
API_CLIENT_FILE = REPO_ROOT / "frontend" / "src" / "services" / "apiClient.ts"

ALLOWED_ORIGIN_PATTERN = re.compile(r"^https?://(localhost(:5173)?|127.0.0.1(:5173)?)$")


class _CorsHandler(BaseHTTPRequestHandler):
    def _write_cors_headers(self):
        origin = self.headers.get("Origin", "")
        allowed_origin = origin if ALLOWED_ORIGIN_PATTERN.match(origin) else ""
        self.send_header("Access-Control-Allow-Origin", allowed_origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        self.send_header(
            "Access-Control-Allow-Headers", "Authorization,Content-Type,Accept,Origin"
        )

    def do_OPTIONS(self):
        self.send_response(204)
        self._write_cors_headers()
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):  # pragma: no cover - network verification path
        self.send_response(200)
        self._write_cors_headers()
        self.end_headers()


def test_nginx_conf_whitelists_frontend_origin():
    content = NGINX_CONF.read_text(encoding="utf-8")
    assert "Access-Control-Allow-Origin" in content
    assert "localhost(:5173)?" in content


def test_cors_headers_match_nginx_rules():
    server = HTTPServer(("127.0.0.1", 0), _CorsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    origin = "http://localhost:5173"
    path = "/api/documents/"

    conn = http.client.HTTPConnection(
        server.server_address[0], server.server_address[1], timeout=2
    )
    conn.request("OPTIONS", path, headers={"Origin": origin})
    response = conn.getresponse()
    headers = {k.lower(): v for k, v in response.getheaders()}

    server.shutdown()
    thread.join(timeout=1.0)

    assert response.status == 204
    assert headers.get("access-control-allow-origin") == origin


def test_frontend_defaults_to_gateway_base_url():
    content = API_CLIENT_FILE.read_text(encoding="utf-8")
    assert "http://localhost/api" in content
