#!/usr/bin/env python3
import importlib.util
import json
import mimetypes
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
PORT = int(os.environ.get("PORT", "8080"))
INTERVAL = float(os.environ.get("NETBIRD_INTERVAL", "2"))
JSON_COMMAND = os.environ.get("NETBIRD_JSON_COMMAND", "docker exec netbird netbird status --json")
TABLE_COMMAND = os.environ.get("NETBIRD_TABLE_COMMAND", "docker exec netbird netbird status --table")

spec = importlib.util.spec_from_file_location("netbird_status", ROOT / "netbird_status.py")
netbird_status = importlib.util.module_from_spec(spec)
spec.loader.exec_module(netbird_status)

payload = {"generatedAt": None, "source": "not collected yet", "peers": []}
lock = threading.Lock()
previous = {}
previous_time = 0.0


def collect_once():
    global payload, previous_time
    peers = netbird_status.collect_peers(JSON_COMMAND, TABLE_COMMAND)
    now = time.time()
    out = []
    for peer in peers:
        rx = peer.get("rxBytes") or 0
        tx = peer.get("txBytes") or 0
        prev = previous.get(peer["id"])
        down = up = 0.0
        if prev and previous_time:
            dt = now - previous_time
            if dt > 0:
                down = max(0.0, (rx - prev[0]) * 8 / dt / 1e6)
                up = max(0.0, (tx - prev[1]) * 8 / dt / 1e6)
        previous[peer["id"]] = (rx, tx)
        out.append({**peer, "downMbps": round(down, 3), "upMbps": round(up, 3)})
    previous_time = now
    with lock:
        payload = {
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": "netbird status counters",
            "peers": out,
            "interface": netbird_status.interface_rates(netbird_status.interface_counters(), previous, previous_time, now),
        }


def collector_loop():
    while True:
        collect_once()
        time.sleep(INTERVAL)


CONFIG_PATH = SITE / "local" / "config.json"


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        parsed = urlparse(self.path)
        if urlparse(self.path).path != "/api/config":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("config must be an object")
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = CONFIG_PATH.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(CONFIG_PATH)
            body = b'{"ok": true}'
            self.send_response(200)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}).encode("utf-8")
            self.send_response(400)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/config":
            try:
                body = CONFIG_PATH.read_bytes()
            except OSError:
                body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/netbird-status.json", "/api/netbird-status"):
            with lock:
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/":
            path = "/index.html"
        target = (SITE / path.lstrip("/")).resolve()
        if SITE.resolve() not in target.parents and target != SITE.resolve():
            self.send_error(403)
            return
        if not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store" if target.name == "index.html" else "public, max-age=300")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    threading.Thread(target=collector_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
