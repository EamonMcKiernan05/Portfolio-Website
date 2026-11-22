"""Parse dsh session logs: goal, model, timings, step/tool counts, files written."""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess

BUILD_ROOT_MARK = "Model Testing"
HTML_RE = re.compile(r"([A-Za-z0-9 _\-.()+&']+\.html)", re.I)


def load_zstd(path: pathlib.Path) -> list[dict]:
    raw = subprocess.run(["zstd", "-d", "-c", "--", str(path)], capture_output=True)
    if raw.returncode != 0:
        raise RuntimeError(f"zstd failed on {path.name}: {raw.stderr[-300:]!r}")
    out = []
    for line in raw.stdout.decode("utf-8", "replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def parse(path: pathlib.Path) -> dict | None:
    """Return the session summary, or None when it carries no goal."""
    events = load_zstd(path)
    goal = None
    t_goal = t_first_end = t_end = None
    turns = steps = tools = 0
    sel = None
    files: dict[str, int] = {}
    cwd = None

    for ev in events:
        ty = ev.get("type")
        data = ev.get("data") or {}
        t = ev.get("time")
        if ty == "model/selection" and sel is None:
            sel = (data.get("provider"), data.get("model"))
        if cwd is None and isinstance(data.get("cwd"), str):
            cwd = data["cwd"]
        if ty == "goal/change" and data.get("operation") == "create" and goal is None:
            goal = (data.get("goal") or {}).get("objective")
            t_goal = t
        elif ty == "turn/start":
            turns += 1
        elif ty == "turn/end":
            if turns == 1:
                t_first_end = t
            t_end = t
        elif ty == "assistant/message":
            steps += 1
        elif ty == "tool/call":
            tools += 1
            blob = json.dumps(data.get("arguments") or {})
            for m in HTML_RE.finditer(blob):
                name = m.group(1).split("\\")[-1].split("/")[-1]
                if BUILD_ROOT_MARK in blob or name.lower().endswith(".html"):
                    files[name] = files.get(name, 0) + 1

    if not goal or not t_goal:
        return None
    fmt = lambda ms: dt.datetime.fromtimestamp(ms / 1000).strftime("%d %b %Y %H:%M") if ms else None
    minutes = lambda a, b: int((b - a) // 60000) if a and b else None
    return {
        "session": path.stem.replace("session-", "") if path.stem.startswith("session-") else path.stem,
        "goal": goal,
        "provider": sel[0] if sel else None,
        "model": sel[1] if sel else None,
        "cwd": cwd,
        "start": fmt(t_goal),
        "finish": fmt(t_end),
        "minutes": minutes(t_goal, t_end),
        "first_pass": minutes(t_goal, t_first_end),
        "followups": max(0, turns - 1),
        "steps": steps,
        "tools": tools,
        "files": files,
        "t_goal": t_goal, "t_first_end": t_first_end, "t_end": t_end,
        "mtime": path.stat().st_mtime,
        "file": str(path),
    }
