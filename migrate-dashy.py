#!/usr/bin/env python3
"""Convert a Dashy conf.yml into local-config/config.json.

Run on the NAS only. The output may contain personal links; do not commit it.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

src = Path(sys.argv[1] if len(sys.argv) > 1 else "user-data/conf.yml")
out = Path(sys.argv[2] if len(sys.argv) > 2 else "local-config/config.json")
text = src.read_text(encoding="utf-8")
sections = []
current = None
item = None
for line in text.splitlines():
    m = re.match(r"\s*-\s+name:\s*(.+?)\s*$", line)
    if m:
        current = {"name": m.group(1).strip().strip('\"').strip("'"), "items": []}
        sections.append(current)
        item = None
        continue
    m = re.match(r"\s*-\s+title:\s*(.+?)\s*$", line)
    if m and current is not None:
        item = {"title": m.group(1).strip().strip('\"').strip("'")}
        current["items"].append(item)
        continue
    m = re.match(r"\s+(url|description):\s*(.+?)\s*$", line)
    if m and item is not None:
        item[m.group(1)] = m.group(2).strip().strip('\"').strip("'")

def host(url):
    p = urlparse(url if "://" in url else "https://" + url)
    return p.netloc

community, pt_sites, docker_apps = [], [], []
for sec in sections:
    name = sec["name"]
    for it in sec["items"]:
        title = it.get("title", "")
        url = it.get("url", "")
        if not title or not url:
            continue
        if "PT" in name:
            pt_sites.append({"id": re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "pt", "name": title, "host": host(url), "url": url})
        elif "社区" in name or "community" in name.lower():
            community.append({"name": title, "host": host(url), "url": url, "desc": it.get("description", "")})
        else:
            docker_apps.append({"name": title, "lan": url, "wan": "", "mode": "auto"})

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"community": community, "ptSites": pt_sites, "dockerApps": docker_apps}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"wrote {out}: community={len(community)} pt={len(pt_sites)} docker={len(docker_apps)}")
