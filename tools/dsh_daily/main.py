#!/usr/bin/env python3
"""Daily: find new dsh builds, publish them to the gallery, record a clip each.

    python3 tools/dsh_daily/main.py                 # the real run (used by cron)
    python3 tools/dsh_daily/main.py --dry-run       # discover + parse, touch nothing
    python3 tools/dsh_daily/main.py --no-video --no-publish --only "Hy4 Flash/TWO_SHORES.html"

State (last watermark, published rels, cached session files) lives under the profile
cache so it never enters either repo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import threading
import functools
import http.server

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dsh_daily import ingest, publish, record, sessions, shared, win  # noqa: E402

STATE_DIR = pathlib.Path.home() / ".hermes/profiles/dev/cache/dsh_daily"
STATE_FILE = STATE_DIR / "state.json"
SESS_CACHE = STATE_DIR / "sessions"
MIN_BYTES = 40_000
SCAFFOLD = re.compile(r"(^|/)(template|shell|.*_head|.*_tail|_.*|build/.*|.*_shell|.*template.*|.*\.min)\.html$", re.I)
LOOKBACK = dt.timedelta(days=3)


def log(msg: str) -> None:
    print(msg, flush=True)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"watermark": None, "published": {}, "runs": []}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=1))


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    """The capture browser hangs up mid-request; that is not an error worth printing."""

    def handle_one_request(self):
        try:
            super().handle_one_request()
        except (ConnectionResetError, BrokenPipeError):
            self.close_connection = True

    def log_message(self, *args):
        pass


RECORD_PORT = 8098


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def serve_repo(port: int = 8099):
    """Serve the site repo on all interfaces so the Windows browser can load it."""
    handler = functools.partial(_QuietHandler,
                                directory=str(pathlib.Path.home() / "portfolio-website"))
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def candidate_builds(inv: dict, published: dict[str, str]) -> list[dict]:
    out = []
    for b in inv["builds"]:
        rel = b["rel"].replace("\\", "/")
        if rel in published:
            continue
        if not b.get("doctype") or b["bytes"] < MIN_BYTES:
            continue
        if SCAFFOLD.match(rel):
            continue
        out.append(b)
    return out


def fetch_sessions(inv: dict) -> dict[str, str]:
    """Pull changed sessions; return uuid -> workspace folder name."""
    SESS_CACHE.mkdir(parents=True, exist_ok=True)
    index_path = SESS_CACHE / "index.json"
    index = json.loads(index_path.read_text()) if index_path.exists() else {}
    paths = {}
    for s in inv["sessions"]:
        index[s["uuid"]] = win.decode_workspace(s["ws"])
        dest = SESS_CACHE / f"{s['uuid']}.zstd"
        if not dest.exists():
            try:
                win.pull(".dsh/sessions/" + s["rel"].replace("\\", "/"), dest)
            except Exception as exc:
                log(f"  ! could not pull session {s['uuid']}: {exc}")
                continue
        paths[s["uuid"]] = index.get(s["uuid"], "")
    index_path.write_text(json.dumps(index, indent=1))
    return paths


def parsed_pool(new_paths: dict[str, str]) -> list[dict]:
    """Sessions fetched today plus any cached in the last few days."""
    seen = {}
    cutoff = (dt.datetime.now() - dt.timedelta(days=7)).timestamp()
    for p in sorted(SESS_CACHE.glob("*.zstd")):
        if p.stat().st_mtime < cutoff and p not in new_paths:
            continue
        if p.stem in seen:
            continue
        try:
            s = sessions.parse(p)
        except Exception as exc:
            log(f"  ! session {p.stem} unreadable: {exc}")
            continue
        if s:
            s["workspace"] = new_paths.get(p.stem) or WORKSPACE_INDEX.get(p.stem)
            seen[p.stem] = s
    return list(seen.values())


def workspace_folder(rel: str) -> str:
    return rel.replace("\\", "/").split("/")[0]


def spec_key_for_html(path: pathlib.Path) -> str | None:
    """Name the one known prompt whose title equals this build's <title>, else None."""
    head = path.read_text(errors="replace")[:6000]
    m = re.search(r"<title>([^<]*)</title>", head, re.S)
    if not m:
        return None
    def core(text: str) -> str:
        """'THE FLOATING CLASSROOM — a lake village school' -> 'the floating classroom'"""
        head = re.split(r"\s+[\u2014\u2013]\s+", text, maxsplit=1)[0]
        head = re.sub(r"^\s*\d+\s*[\u2014\u2013-]+\s*", "", head)
        return ingest.norm(head).strip().lower()

    want = core(m.group(1))
    prs = json.load(open(ingest.DOCS / "model-testing-prompts.json"))["spec_prompts"]
    hits = [k for k, txt in prs.items() if core(ingest.title_of(txt, "")) == want]
    return hits[0] if len(hits) == 1 else None


def _fname(key: str) -> str:
    """A session's file key can carry build-log noise ("n-a--- 825006 x.html") or a full path,
    so compare on the last path-ish token, never on the raw key."""
    k = key.strip().strip("'\"").replace("\\", "/")
    last = re.split(r"[\s|>]+", k)[-1] if (" " in k or "|" in k) else k
    return pathlib.Path(last).name.lower()


_STOP = {"the", "a", "and", "of", "in", "on", "at", "for", "to", "with", "one", "self",
         "contained", "html", "file", "create", "build", "complete", "new", "make", "its"}


def _words(text: str | None) -> set[str]:
    text = re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower().replace("_", " ").replace("-", " "))
    return {w for w in text.split() if len(w) > 2 and w not in _STOP and not w.isdigit()}


def attribute(build: dict, pool: list[dict]) -> dict | None:
    """The session that produced this build.

    A dsh session stores its own workspace, provider, model, goal text and timings, so the build's
    workspace folder decides the model and the session's own goal decides which run it was. A write
    to the file name is corroboration, never the gate: several models log writes to "sky-temple.html".
    """
    rel = build["rel"].replace("\\", "/")
    name = pathlib.Path(rel).name.lower()
    workspace = rel.split("/")[0]
    want = _words(pathlib.Path(name).stem) | _words(build.get("title") or "")
    build_ms = 0.0
    if build.get("mtime"):
        build_ms = dt.datetime.fromisoformat(build["mtime"]).timestamp() * 1000
    best = None
    for s in pool:
        if s.get("workspace") != workspace:
            continue
        overlap = len(want & _words(s.get("goal")))
        hits = sum(v for k, v in s["files"].items() if _fname(k) == name)
        # a session that logged a write to this file only needs the goal to not contradict it;
        # a goal-only match must share at least two meaningful words, or the whole name when the
        # name is a single word — otherwise "create one complete, self-contained html" wins
        if not hits and overlap < min(2, len(want)):
            continue
        gap = (build_ms - (s.get("t_end") or 0)) if build_ms else 0.0
        gap = gap if gap >= 0 else 4e12 - gap        # a session that ended after the file is suspect
        score = (-overlap, -hits, gap)
        if best is None or score < best[0]:
            best = (score, s)
    return best[1] if best else None


def is_held(rel: str, ignored: set[str]) -> bool:
    """True when a build is on the ignore list. `Workspace/*` holds every build in that workspace,
    including ones that do not exist yet — an early-access model must stay out of the gallery."""
    rel = rel.replace("\\", "/")
    for i in (x.replace("\\", "/") for x in ignored):
        if rel == i:
            return True
        if i.endswith("/*") and rel.startswith(i[:-1]):
            return True
        if i.endswith("/") and rel.startswith(i):
            return True
    return False


def refresh_shared(run: dict) -> None:
    """Keep Desktop\\Model Testing - Shared Builds in step with what the gallery now holds."""
    try:
        sh = shared.build()
        log(f"   shared builds: {sh['builds_kept']} builds, {sh['html']} html, {sh['mp4']} clips "
            f"({sh['copied']} copied, {sh['pruned']} pruned) -> {sh['dest']}")
        run["shared"] = {k: sh.get(k) for k in
                         ("builds_kept", "html", "mp4", "copied", "pruned", "missing")}
    except Exception as exc:
        log(f"   shared builds FAILED: {exc}")
        run["shared"] = {"error": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--since")
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--no-publish", action="store_true")
    args = ap.parse_args()

    state = load_state()
    since = args.since
    if not since:
        base = state.get("watermark")
        since = ((dt.datetime.fromisoformat(base) - LOOKBACK) if base
                 else dt.datetime.now() - LOOKBACK).strftime("%Y-%m-%dT%H:%M:%S")
    log(f"== dsh daily {dt.datetime.now():%Y-%m-%d %H:%M} — scanning since {since}"
        f"{' (dry run)' if args.dry_run else ''}")

    inv = win.inventory(since)
    log(f"   box: {len(inv['builds'])} build files, {len(inv['sessions'])} changed sessions")

    gen_text = ingest.read_text()
    published = ingest.existing_slugs(gen_text)
    cands = candidate_builds(inv, published)
    ignored = {r.replace("\\", "/") for r in (state.get("ignored") or [])}
    if ignored:
        held = [c for c in cands if is_held(c["rel"], ignored)]
        cands = [c for c in cands if not is_held(c["rel"], ignored)]
        for c in held:
            log(f"   - {c['rel']} — held by the ignore list, not published")
    if args.only:
        want = {o.replace("\\", "/") for o in args.only}
        cands = [c for c in cands if c["rel"].replace("\\", "/") in want]
    log(f"   unpublished builds: {len(cands)}")
    for c in cands:
        log(f"     {c['bytes']:>9} B  {c['mtime']}  {c['rel']}")

    new_paths = fetch_sessions(inv)
    globals()["WORKSPACE_INDEX"] = json.loads((SESS_CACHE / "index.json").read_text())
    pool = parsed_pool(new_paths)
    log(f"   sessions parsed: {len(pool)}")

    # sessions that never logged a model/selection inherit their workspace's default
    # only fill a missing model/selection when the whole workspace agrees on one pair
    seen_ws: dict[str, set] = {}
    for s in pool:
        if s.get("provider") and s.get("workspace"):
            seen_ws.setdefault(s["workspace"], set()).add((s["provider"], s.get("model")))
    unanimous = {ws: next(iter(v)) for ws, v in seen_ws.items() if len(v) == 1}
    for s in pool:
        if not s.get("provider") and s.get("workspace") in unanimous:
            s["provider"], s["model"] = unanimous[s["workspace"]]
            s["inferred"] = True

    todo = []
    for c in cands:
        s = attribute(c, pool)
        if not s:
            # no session names this file: publish it only if its own title matches a known spec,
            # so the prompt on the page is the real one and the missing stats stay unrecorded
            rel = c["rel"].replace("\\", "/")
            local = STATE_DIR / "incoming" / rel
            try:
                win.pull("Desktop/Model Testing/" + rel, local)
                key = spec_key_for_html(local)
            except Exception as exc:
                log(f"   ? {c['rel']} — could not read it: {exc}")
                continue
            if not key:
                log(f"   ? {c['rel']} — no session names this file and its title matches no known "
                    f"spec, leaving it alone")
                continue
            c["local"] = local
            todo.append((c, {"unattributed": True, "prompt_key": key}))
            log(f"   + {c['rel']} — no session; prompt '{key}', stats left unrecorded")
            continue
        todo.append((c, s))
        log(f"   + {c['rel']} <- {s['session'][:8]} "
            f"({s.get('model') or 'model?'}, {s.get('first_pass')} min first pass)")

    if args.dry_run or not todo:
        if args.dry_run:
            log("   dry run: stopping before ingest")
        else:
            log("   nothing to ingest")
            state["watermark"] = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            run = {"at": dt.datetime.now().isoformat(timespec="seconds"),
                   "ingested": [], "videos": [], "publish": None,
                   "skipped": [c["rel"] for c in cands]}
            refresh_shared(run)
            state["runs"] = (state.get("runs") or [])[-20:] + [run]
            save_state(state)
        return 0

    # local copies of the html files
    work = STATE_DIR / "incoming"
    recs = []
    for c, s in todo:
        rel = c["rel"].replace("\\", "/")
        local = work / rel
        if not c.get("local"):
            win.pull("Desktop/Model Testing/" + rel, local)
        c["local"] = local
        if s.get("unattributed"):
            prs = json.load(open(ingest.DOCS / "model-testing-prompts.json"))["spec_prompts"]
            rec = ingest.ingest_unattributed(c, s["prompt_key"], prs[s["prompt_key"]])
        else:
            rec = ingest.ingest(c, s)
        recs.append(rec)
        log(f"   ingested {rec['slug']} ({rec['kb']} KB, prompt '{rec['prompt']}')")

    log("   " + ingest.rebuild())
    prs = json.load(open(ingest.DOCS / "model-testing-prompts.json"))["spec_prompts"]
    for rec in recs:
        ingest.mirror(rec, prs[rec["prompt"]])

    videos = []
    if not args.no_video:
        # A fixed port, opened for the LAN in ufw: the box captures over the network and can
        # only reach ports that are allowed through. 8099 is another profile's keyproxy.
        serve_port = RECORD_PORT
        srv = serve_repo(serve_port)
        pairs = [(r["slug"], r["rel"]) for r in recs]
        try:
            videos = record.record_builds(pairs, copy_to_desktop=False, serve_port=serve_port)
        finally:
            srv.shutdown()
        for v in videos:
            v["workspace"] = next((r["workspace"] for r in recs if r["slug"] == v["slug"]), "")
            log(f"   clip {v['slug']}: " + (
                f"{v['seconds']}s {v['bytes']/1e6:.1f} MB, cinematic={v['cinematic']}, "
                f"motion {v['motion']}, -> {v.get('desktop')}"
                if "clip" in v else f"FAILED {v.get('error')}"))
        # copy after the workspace is known
        for v in videos:
            if "clip" in v and v.get("workspace"):
                win.push(pathlib.Path(v["clip"]),
                         f"Desktop/{record.DESKTOP_SUBDIR}/{v['workspace']}/{v['slug']}.mp4")
                v["desktop"] = f"Desktop\\{record.DESKTOP_SUBDIR}\\{v['workspace']}\\{v['slug']}.mp4"
        ingest.rebuild()

    result = {"ingested": [r["slug"] for r in recs], "videos": videos, "publish": None}
    if not args.no_publish:
        msg = ("Gallery: " + ", ".join(r["slug"] for r in recs) if recs
               else "dsh daily pipeline: update") + " (daily dsh run)"
        result["publish"] = publish.ship(msg)
        result["live"] = publish.live_check()
        log(f"   live: {result['live']}")

    refresh_shared(result)

    state["watermark"] = dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for r in recs:
        state["published"][r["rel"]] = r["slug"]
    state["runs"] = (state.get("runs") or [])[-20:] + [{
        "at": dt.datetime.now().isoformat(timespec="seconds"),
        "ingested": result["ingested"],
        "videos": [{k: v.get(k) for k in ("slug", "seconds", "bytes", "cinematic", "motion", "desktop", "error")}
                   for v in videos],
        "publish": result["publish"],
    }]
    save_state(state)

    print("RESULT " + json.dumps(result, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
