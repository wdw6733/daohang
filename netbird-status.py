#!/usr/bin/env python3
"""Collect real NetBird peer traffic counters into netbird-status.json.

Preferred source: `netbird status --json`.
Fallback source: `netbird status --table` (RX/TX column).

The script computes Mbps from cumulative byte counters. It never invents
traffic: if NetBird status cannot be read, it writes an empty peer list.
"""
import argparse
import json
import re
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

PEER_META = {}

SIZE_UNITS = {
    "B": 1,
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
    "TIB": 1024**4,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
}


def run(cmd):
    return subprocess.run(shlex.split(cmd), text=True, capture_output=True, timeout=20)


def first_value(obj, names):
    if not isinstance(obj, dict):
        return None
    lower = {str(k).lower(): v for k, v in obj.items()}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def as_int(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    return parse_size(text)


def parse_size(text):
    m = re.match(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*([A-Za-z]+)?\s*$", str(text))
    if not m:
        return None
    unit = (m.group(2) or "B").upper()
    return int(float(m.group(1)) * SIZE_UNITS.get(unit, 1))


def find_peer_list(data):
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("peers", "Peers", "peerList"):
        if isinstance(data.get(key), list):
            return data[key]
    for value in data.values():
        found = find_peer_list(value)
        if found:
            return found
    return []


def normalize_peer(raw):
    name = first_value(raw, ["name", "hostname", "fqdn", "peerName", "remote", "remoteName"]) or "Peer"
    ip = first_value(raw, ["ip", "netbirdIp", "netbirdIP", "remoteIp", "remoteIP", "address"]) or ""
    ip = str(ip).split("/")[0]
    rx = as_int(first_value(raw, ["rxBytes", "bytesReceived", "receivedBytes", "rx_bytes", "transferRx", "rx", "received"]))
    tx = as_int(first_value(raw, ["txBytes", "bytesSent", "sentBytes", "tx_bytes", "transferTx", "tx", "sent"]))
    latency_raw = first_value(raw, ["latency", "latencyMs", "latency_ms", "ping"])
    latency = 0
    if latency_raw is not None:
        m = re.search(r"[0-9]+(?:\.[0-9]+)?", str(latency_raw))
        latency = int(float(m.group(0))) if m else 0
    connected_raw = first_value(raw, ["connected", "status", "connectionStatus"])
    connected = True
    if isinstance(connected_raw, bool):
        connected = connected_raw
    elif connected_raw is not None:
        text = str(connected_raw).lower()
        connected = not ("disconnect" in text or "connecting" in text or text in {"false", "0"})
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-") or "peer"
    pid, display_name, role = PEER_META.get(ip, (slug, str(name), ""))
    return {
        "id": pid,
        "name": display_name,
        "ip": ip,
        "role": role,
        "rxBytes": rx,
        "txBytes": tx,
        "latency": latency,
        "connected": connected,
    }


def peers_from_json(command):
    result = run(command)
    if result.returncode != 0:
        return []
    data = json.loads(result.stdout)
    peers = [normalize_peer(p) for p in find_peer_list(data) if isinstance(p, dict)]
    return [p for p in peers if p["rxBytes"] is not None and p["txBytes"] is not None]


def peers_from_table(command):
    result = run(command)
    if result.returncode != 0:
        return []
    peers = []
    for line in result.stdout.splitlines():
        if "/" not in line or "NAME" in line:
            continue
        ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line)
        size_match = re.search(r"([0-9]+(?:\.[0-9]+)?\s*[A-Za-z]+)\s*/\s*([0-9]+(?:\.[0-9]+)?\s*[A-Za-z]+)", line)
        if not ip_match or not size_match:
            continue
        ip = ip_match.group(0)
        name = line[: ip_match.start()].strip() or ip
        latency_match = re.search(r"(\d+(?:\.\d+)?)\s*ms", line)
        peers.append(normalize_peer({
            "name": name,
            "ip": ip,
            "rxBytes": parse_size(size_match.group(1)),
            "txBytes": parse_size(size_match.group(2)),
            "latency": latency_match.group(1) if latency_match else 0,
            "connected": "Connected" in line or "P2P" in line or "Relayed" in line,
        }))
    return peers


def collect(args, previous, previous_time):
    peers = []
    try:
        peers = peers_from_json(args.command)
    except Exception:
        peers = []
    if not peers:
        try:
            peers = peers_from_table(args.table_command)
        except Exception:
            peers = []
    now = time.time()
    out = []
    for peer in peers:
        rx = peer["rxBytes"] or 0
        tx = peer["txBytes"] or 0
        prev = previous.get(peer["id"])
        down = up = 0.0
        if prev and previous_time:
            dt = now - previous_time
            if dt > 0:
                down = max(0.0, (rx - prev[0]) * 8 / dt / 1e6)
                up = max(0.0, (tx - prev[1]) * 8 / dt / 1e6)
        previous[peer["id"]] = (rx, tx)
        out.append({**peer, "downMbps": round(down, 3), "upMbps": round(up, 3)})
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "netbird status counters",
        "peers": out,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_suffix(output.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(output)
    return now


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", default="netbird status --json")
    parser.add_argument("--table-command", default="netbird status --table")
    parser.add_argument("--output", default="site/netbird-status.json")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    previous = {}
    previous_time = 0.0
    while True:
        previous_time = collect(args, previous, previous_time)
        if not args.loop:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
