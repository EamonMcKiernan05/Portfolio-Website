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


def user_text(data: dict) -> str | None:
    """Plain text of a user/message event (its content is a list of parts)."""
    content = data.get("content")
    if isinstance(content, str):
        return content.strip() or None
    parts = []
    for part in content or []:
        if isinstance(part, dict) and part.get("type") == "text":
            parts.append(part.get("text") or "")
    text = "\n".join(p for p in parts if p).strip()
    return text or None


def parse(path: pathlib.Path) -> dict | None:
    """Return the session summary, or None when it carries no goal."""
    events = load_zstd(path)
    goal = None
    t_goal = t_first_end = t_end = None
    turns = steps = tools = 0
    sel = None
    files: dict[str, int] = {}
    mentions: dict[str, int] = {}   # any .html named anywhere, incl. build-script output
    cwd = None
    session_created = None
    first_user = None
    goal_source = None
    turn_open = None
    spans: list[int] = []

    for ev in events:
        ty = ev.get("type")
        data = ev.get("data") or {}
        t = ev.get("time")
        if ty == "model/selection" and sel is None:
            sel = (data.get("provider"), data.get("model"))
        if sel is None and ty == "request/header":
            cfg = ((data.get("header") or {}).get("config") or {})
            if cfg.get("model"):
                sel = (cfg.get("provider"), cfg.get("model"))
        if sel is None and isinstance(data.get("model"), str) and data.get("provider"):
            sel = (data["provider"], data["model"])
        if cwd is None and isinstance(ev.get("cwd") or data.get("cwd"), str):
            cwd = ev.get("cwd") or data.get("cwd")
        if session_created is None and ty == "session":
            # the session event carries createdAt/cwd at the top level, not in data
            session_created = ev.get("createdAt") or data.get("createdAt") or t
        if first_user is None and ty == "user/message":
            text = user_text(data)
            if text and not text.lstrip().startswith("<"):
                first_user = text
        if ty == "goal/change" and data.get("operation") == "create" and goal is None:
            goal = (data.get("goal") or {}).get("objective")
            t_goal = t
            goal_source = "goal/change"
        elif ty == "turn/start":
            turns += 1
            turn_open = t
        elif ty == "turn/end":
            if turn_open is not None:
                spans.append(max(0, t - turn_open))
                turn_open = None
            if turns == 1:
                t_first_end = t
            t_end = t
        elif ty == "assistant/message":
            steps += 1
        elif ty and ty.startswith("tool/"):
            if ty == "tool/call":
                tools += 1
            # a build script writes the html, so the file name often appears only in the
            # tool's output ("n-a--- 825006 floating-classroom.html"), never in a path arg
            blob = json.dumps(data)
            for m in HTML_RE.finditer(blob):
                name = m.group(1).split("\\")[-1].split("/")[-1].strip()
                mentions[name] = mentions.get(name, 0) + 1
                if ty == "tool/call" and (BUILD_ROOT_MARK in blob or name.lower().endswith(".html")):
                    files[name] = files.get(name, 0) + 1

    if goal is None and first_user:
        # Not every harness session logs a goal/change event (done this way since
        # 20 Nov builds have none); the first user message IS the spec, and the
        # session's own creation time is when it was sent.
        goal = first_user
        t_goal = session_created
        goal_source = "first-user-message"

    if not goal or not t_goal:
        return None
    fmt = lambda ms: dt.datetime.fromtimestamp(ms / 1000).strftime("%d %b %Y %H:%M") if ms else None
    minutes = lambda a, b: int((b - a) // 60000) if a and b else None
    # Time the agent was actually working: the sum of each turn's own span. The gap
    # between a turn ending and the next prompt arriving is the owner being away, not
    # build time, so it is excluded (owner rule, 2026-11-23).
    active_ms = sum(spans)
    first_span_ms = spans[0] if spans else None
    return {
        "session": path.stem.replace("session-", "") if path.stem.startswith("session-") else path.stem,
        "goal": goal,
        "provider": sel[0] if sel else None,
        "model": sel[1] if sel else None,
        "cwd": cwd,
        "start": fmt(t_goal),
        "finish": fmt(t_end),
        "minutes": int(active_ms // 60000) if spans else minutes(t_goal, t_end),
        "wall_minutes": minutes(t_goal, t_end),
        "first_pass": int(first_span_ms // 60000) if first_span_ms is not None
                      else minutes(t_goal, t_first_end),
        "turn_minutes": [int(s // 60000) for s in spans],
        "followups": max(0, turns - 1),
        "steps": steps,
        "tools": tools,
        "files": files,
        "mentions": mentions,
        "goal_source": goal_source,
        "t_goal": t_goal, "t_first_end": t_first_end, "t_end": t_end,
        "mtime": path.stat().st_mtime,
        "file": str(path),
    }
