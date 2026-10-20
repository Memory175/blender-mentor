# -*- coding: utf-8 -*-
"""source_refresh.py — 来源过期后的“候选查询”，只提议，不自动改写。

安全边界：
- 只访问 source_registry.policy.allowed_domains 中的官方域名 / api.crossref.org；
- 不绕过登录、反爬、付费墙；
- 不自动替换 registry 或模块数据；
- 查询失败标 unreachable，不猜测“最新版”。

用法：
    python scripts/source_refresh.py --offline
    python scripts/source_refresh.py --source-id NEUFERT-5E
    python scripts/source_refresh.py --json .source_refresh.json
"""
import argparse
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _load(root, path=None):
    p = path or os.path.join(root, "assets", "source_registry.json")
    with open(p, encoding="utf-8") as fh:
        return json.load(fh), p


def _allowed(url, domains):
    host = urllib.parse.urlparse(url).hostname or ""
    return any(host == d or host.endswith("." + d) for d in domains)


def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": "blender-mentor-source-refresh/1 (+manual review only)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read(200000).decode("utf-8", "replace")
        return {"http_status": getattr(resp, "status", None), "final_url": resp.geturl(),
                "bytes": len(body), "last_modified": resp.headers.get("Last-Modified")}


def _proposal(src, domains, timeout, offline):
    sid = src.get("id")
    url = src.get("check_url")
    if offline:
        return {"source_id": sid, "action": "offline", "proposed": None,
                "reason": "offline mode; no network request"}
    if not url:
        return {"source_id": sid, "action": "manual_check", "proposed": None,
                "reason": "no check_url; provide official URL / DOI"}
    if not _allowed(url, domains):
        return {"source_id": sid, "action": "blocked", "proposed": None,
                "reason": "domain not in policy.allowed_domains: %s" % url}
    try:
        if src.get("doi"):
            meta = _fetch("https://api.crossref.org/works/" + urllib.parse.quote(src["doi"]), timeout)
            return {"source_id": sid, "action": "crossref_checked", "proposed": None,
                    "http": meta, "reason": "DOI metadata fetched; compare title/year manually"}
        meta = _fetch(url, timeout)
        return {"source_id": sid, "action": "manual_review", "proposed": None,
                "http": meta, "reason": "official page fetched; edition/status must be read and confirmed manually"}
    except Exception as exc:  # noqa: BLE001
        return {"source_id": sid, "action": "unreachable", "proposed": None,
                "reason": type(exc).__name__ + ": " + str(exc)}


def main():
    ap = argparse.ArgumentParser(description="Propose source refresh candidates (never auto-applies)")
    ap.add_argument("--root", default=os.path.dirname(HERE))
    ap.add_argument("--source-registry", default=None)
    ap.add_argument("--source-id", default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--timeout", type=int, default=15)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    try:
        reg, _ = _load(os.path.abspath(args.root), args.source_registry)
    except Exception as exc:  # noqa: BLE001
        print("SOURCE_REFRESH " + json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False))
        return 1
    domains = reg.get("policy", {}).get("allowed_domains", [])
    proposals = []
    for src in reg.get("sources", []):
        if args.source_id and src.get("id") != args.source_id:
            continue
        proposals.append(_proposal(src, domains, args.timeout, args.offline))
    result = {"status": "proposals", "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
              "applied": False, "proposals": proposals}
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    print("SOURCE_REFRESH " + json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
