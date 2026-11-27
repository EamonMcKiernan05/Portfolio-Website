"""Turn a new build + its session into gallery records, data files and pages."""
from __future__ import annotations

import ast
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess

ROOT = pathlib.Path.home() / "portfolio-website"
DOCS = ROOT / "docs"
GEN = ROOT / "tools" / "build_model_gallery.py"
MIRROR = pathlib.Path.home() / "Local-LLM-Testing" / "Model Testing Gallery"
DEMOS = ROOT / "demos" / "model-testing"
THUMBS = ROOT / "demos" / "thumbs" / "model-testing"

PROVIDER_LABEL = {
    "nous-portal": "Nous portal",
    "deepseek-account": "DeepSeek API",
    "qwen-token-plan-custom": "Qwen token plan",
    "qwen-token-plan": "Qwen token plan",
    "maya": "Maya",
    "llama.cpp (maya)": "Maya",
    "openrouter": "OpenRouter",
    "opencode-go": "OpenCode Go",
    "hungerg-free": "OpenCode Go",
}
MODEL_NOTE = ("Session captured from the harness. Model id as configured there; "
              "not checked against the vendor's own model list.")

# Every build on this gallery is driven by the DeepSeek harness (owner, 24 Nov 2026).
# The session header is NOT the source of truth for provider/model: one GLM-5.4 session
# recorded a stale `maya` + Qwen gguf path, which published GLM as a Qwen build.
# Maya and Strata are the engines; the model is the model (owner, 24 Nov 2026).
SERVING_BY_WORKSPACE = {
    "GLM-5.4": ("GLM Coding Plan", "GLM-5.4"),
    "Qwen3.8-27B": ("Maya", "qwen3.8-27b-ud-q8_k_xl"),
    "Hy4 Flash Maya M": ("Maya", "hy4-flash-maya-m"),
    "Inkling-2-Mini": ("Maya", "inkling-2-mini"),
    "Qwen3.8-Flash-Next": ("Strata", "qwen3.8-flash-next"),
    "Qwen3.8 Flash-Next": ("Strata", "qwen3.8-flash-next"),
    "HungerG": ("OpenCode Go", "HungerG"),
}


def serving_for(workspace: str, provider: str | None,
                model: str | None) -> tuple[str, str, str]:
    """(provider label, model id, kind) for a build's serving panel."""
    alias = SERVING_BY_WORKSPACE.get(workspace)
    if alias:
        prov, mid = alias
        return prov, mid, "local" if prov.startswith("Maya") else "cloud"
    label = PROVIDER_LABEL.get(provider or "", provider or "Not recorded")
    mid = model or "not recorded"
    if mid.startswith("/") or mid.lower().endswith(".gguf"):
        # a filesystem path is a serving detail, never a model id
        name = pathlib.Path(mid).name
        mid = (name[:-5] if name.lower().endswith(".gguf") else name).lower()
        label = "Maya M (llama.cpp engine)"
    kind = "local" if label.startswith("Maya") or label == "Strata" else "cloud"
    return label, mid, kind


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------- generator io

def read_text() -> str:
    return GEN.read_text()


def existing_slugs(text: str) -> dict[str, str]:
    """rel -> slug for every record, parsed by record boundary (multi-line safe)."""
    out = {}
    for block in re.split(r"\n(?=\s{4}dict\(rel=)", text):
        m_rel = re.search(r"rel=(['\"])(.+?)\1", block)
        m_slug = re.search(r"slug=(['\"])(.+?)\1", block)
        if m_rel and m_slug:
            out[m_rel.group(2)] = m_slug.group(2)
    return out


def record_block(rec: dict) -> str:
    q = lambda v: "'" + str(v).replace("'", "’") + "'"
    return (f"    dict(rel={q(rec['rel'])}, slug={q(rec['slug'])}, model={q(rec['model'])}, "
            f"group={q(rec['group'])}, harness={q(rec['harness'])},\n"
            f"         variant={q(rec['variant'])}, title={q(rec['title'])}, prompt={q(rec['prompt'])}, "
            f"session={q(rec['session'])},\n"
            f"         followups={rec['followups']}, date={q(rec['date'])}, "
            f"build_min={rec['build_min']}, kb={rec['kb']},\n"
            f"         blurb={q(rec['blurb'])}),\n")


def replace_records(text: str, rec: dict) -> str:
    """Rewrite the record whose rel matches rec, keeping every other record as-is."""
    parts = re.split(r"(?m)^(?=\s{4}dict\(rel=)", text)
    hit = False
    for i, part in enumerate(parts):
        m_rel = re.search(r"rel=(['\"])(.+?)\1", part)
        if not m_rel or m_rel.group(2) != rec["rel"]:
            continue
        start = part.index("dict(rel=")
        # the record ends at the ")," that is followed by another record or the list close
        for m in re.finditer(r"\),\n", part):
            tail = part[m.end():]
            if not tail.strip() or re.match(r"\s{4}dict\(rel=", tail):
                end = m.end()
                break
        else:
            raise RuntimeError(f"cannot find the end of the record for {rec['rel']}")
        parts[i] = part[:start] + record_block(rec).lstrip() + tail
        hit = True
        break
    if not hit:
        raise RuntimeError(f"no existing record for {rec['rel']}")
    return "".join(parts)


def append_records(text: str, recs: list[dict]) -> str:
    """Insert before the closing bracket of BUILDS, found by bracket matching.

    A literal "]\n\nGROUP_ORDER" marker breaks the moment anything is written between the list and
    GROUP_ORDER (a comment block did exactly that and aborted a whole nightly run)."""
    start = text.find("BUILDS = [")
    if start < 0:
        raise RuntimeError("no BUILDS list in the generator")
    i, depth, quote = text.index("[", start), 0, None
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    else:
        raise RuntimeError("cannot find the BUILDS terminator in the generator")
    body = "".join(record_block(r) for r in recs)
    line_start = text.rfind("\n", 0, i) + 1
    return text[:line_start] + body + text[line_start:]


def ensure_group(text: str, group: str) -> str:
    m = re.search(r"GROUP_ORDER\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        raise RuntimeError("no GROUP_ORDER in the generator")
    groups = re.findall(r"['\"](.+?)['\"]", m.group(1))
    if group in groups:
        return text
    groups.append(group)
    new = "GROUP_ORDER = [" + ", ".join(repr(g) for g in groups) + "]"
    return text[:m.start()] + new + text[m.end():]


# ---------------------------------------------------------------- prompt keys

def title_of(prompt: str, stem: str) -> str:
    first = prompt.strip().splitlines()[0].strip()
    m = re.match(r"^#\s*\d+\s*[—–-]+\s*(.+)$", first)
    if m:
        return m.group(1).strip()
    m = re.search(r"\bfor\s+([A-Z0-9][A-Z0-9 ,'’&.\-]{2,40})", prompt[:400])
    if m:
        return m.group(1).strip().rstrip(",.")
    return stem


def prompt_key(prompt: str, stem: str, model_slug: str) -> tuple[str, bool]:
    """(key, is_new). Same text reuses its key, and so does the same *title*: the body of a brief
    drifts a line or two between sessions, and minting "<key>-<model>" put a second copy of
    The Floating Classroom on the site under a private name."""
    prompts = json.load(open(DOCS / "model-testing-prompts.json"))["spec_prompts"]
    for key, text in prompts.items():
        if norm(text) == norm(prompt):
            return key, False
    want = norm(title_of(prompt, stem)).strip().lower()
    if want:
        for key, text in prompts.items():
            if norm(title_of(text, "")).strip().lower() == want:
                return key, False          # same brief, slightly different body: keep the text
    key = slugify(title_of(prompt, stem)) or slugify(stem)
    if key in prompts:
        key = f"{key}-{model_slug}"
    return key, True


# ---------------------------------------------------------------- naming rules

# Models that ran both through the cloud API and on the local maya engine are listed
# as two separate models, so the two serving paths never share a group (owner, 23 Nov).
MODEL_SPLIT = {"Hy4 Flash": {"api": "Hy4 Flash - API", "maya": "Hy4 Flash - Maya"}}


# a workspace folder is not a model title: the engine/build suffix belongs in `variant`, not in
# the name that groups the cards (the 24 Nov run put DeepSeek's four new builds in a second group)
MODEL_ALIASES = {"DeepSeek-V4.1-Flash-1017": "DeepSeek V4.1 Flash"}


def name_parts(workspace: str, provider: str | None) -> tuple[str, str, str]:
    """(group, variant, harness) from a workspace folder name and provider."""
    group = workspace.strip()
    variant = ""
    # Every build here was driven by the DeepSeek harness. "maya" is the llama.cpp
    # engine serving the model, never a harness — it belongs in the provider line.
    harness = "DeepSeek Harness"
    m = re.match(r"^(.*?)\s+Maya\s+(.+)$", group)
    if m:
        group, variant = m.group(1).strip(), "Maya " + m.group(2).strip()
    group = MODEL_ALIASES.get(group, group)
    split = MODEL_SPLIT.get(group)
    if split:
        group = split["maya" if (provider or "").lower() == "maya" else "api"]
        variant = ""
    return group, variant, harness


def _floor(x):
    return int(x) if x is not None else None


def human_minutes(mins: int | None) -> str:
    """17 minutes / 1 h 54 m — never a bare 700."""
    if mins is None:
        return "unrecorded"
    if mins < 60:
        return f"{mins} minutes"
    h, m = divmod(int(mins), 60)
    return f"{h} h {m} m" if m else f"{h} h"


def blurb_for(stats: dict) -> str:
    """Build time is the time the agent was actually working: idle gaps between a
    finished turn and the next prompt are excluded (owner rule, 2026-11-23)."""
    fp, mins, fu = stats.get("first_pass"), stats.get("minutes"), stats.get("followups") or 0
    if not fu:
        return f"One pass, {human_minutes(fp)}."
    return (f"{human_minutes(fp)} first pass, then {fu} follow-up{'s' if fu > 1 else ''} — "
            f"{human_minutes(mins)} of working time.")


# ---------------------------------------------------------------- ingestion

def ingest_unattributed(build: dict, key: str, prompt_text: str, *,
                        copy_demo: bool = True) -> dict:
    """Publish a finished build whose session log is not in the store.

    Nothing is guessed: the prompt comes from the named spec key, the model from the
    workspace folder it sits in, and every timing or count stays honestly unrecorded.
    """
    rel = build["rel"].replace("\\", "/")
    workspace, file_name = rel.split("/", 1)
    stem = pathlib.Path(file_name).stem
    group, variant, harness = name_parts(workspace, None)
    slug = "-".join(filter(None, [slugify(group), slugify(variant), slugify(stem)]))
    kb = max(1, round(build["bytes"] / 1024))
    date = dt.datetime.fromisoformat(build["mtime"]).strftime("%d %b %Y")
    stats = dict(start=None, finish=None, minutes=None, first_pass=None, followups=None,
                 steps=None, tools=None, turns=None)
    rec = dict(rel=rel, slug=slug, model=group, group=group, harness=harness, variant=variant,
               title=title_of(prompt_text, stem), prompt=key, session="",
               followups=None, date=date, build_min=None, kb=kb,
               blurb=("Session log for this build is not in the harness store, so its timings, "
                      "step counts and follow-ups are not recorded."),
               bytes=build["bytes"], workspace=workspace, file_name=file_name)
    if copy_demo:
        dst = DEMOS / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(build["local"], dst)

    text = ensure_group(append_records(read_text(), [rec]), group)
    GEN.write_text(text)
    ast.parse(text)

    sj = DOCS / "model-testing-build-stats.json"
    st = json.load(open(sj)); st[slug] = stats
    sj.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")

    vp = DOCS / "model-testing-serving.json"
    sv = json.load(open(vp))
    sv[slug] = dict(provider="Not recorded", kind="cloud", model="not recorded",
                    harness=harness, note="No session log for this build in the harness store.")
    vp.write_text(json.dumps(sv, indent=1, sort_keys=True) + "\n")

    cp = DOCS / "model-testing-cards.json"
    cards = json.load(open(cp))
    cards.append(dict(model=workspace, file=file_name, rel=rel, kb=kb, title=stem,
                      date=date, date_iso=build["mtime"][:10]))
    cp.write_text(json.dumps(cards, indent=1) + "\n")
    return rec


def ingest(build: dict, session: dict, *, copy_demo: bool = True,
           title: str | None = None, slug: str | None = None,
           replace: bool = False) -> dict:
    """Add one build: demo file, records, data files. Returns the record."""
    rel = build["rel"].replace("\\", "/")
    workspace, file_name = rel.split("/", 1)
    stem = pathlib.Path(file_name).stem

    group, variant, harness = name_parts(workspace, session.get("provider"))
    model_slug = slugify(group)
    slug = slug or "-".join(filter(None, [model_slug, slugify(variant), slugify(stem)]))

    if replace:
        existing = existing_slugs(read_text())
        if rel in existing:
            slug = existing[rel]
    key, key_is_new = prompt_key(session["goal"], stem, model_slug)
    kb = max(1, round(build["bytes"] / 1024))
    built = dt.datetime.fromisoformat(build["mtime"])
    date = built.strftime("%d %b %Y")
    # finish = last turn/end; a session still open has none, so the build's own mtime stands in
    fmt = lambda ms: dt.datetime.fromtimestamp(ms / 1000).strftime("%d %b %Y %H:%M")
    t_goal = session.get("t_goal") or int(built.timestamp() * 1000)
    finish_ms = session.get("t_end") or int(built.timestamp() * 1000)
    first_ms = session.get("t_first_end") or finish_ms
    stats = {
        "start": session.get("start") or fmt(t_goal), "finish": fmt(finish_ms),
        # working time = the turns themselves; the gap between an answer and Eamon's next prompt
        # is not the model working, so the wall clock is only a fallback
        "minutes": session.get("minutes") if session.get("minutes") is not None
        else int((finish_ms - t_goal) // 60000),
        "first_pass": int((first_ms - t_goal) // 60000),
        "followups": session.get("followups") or 0, "steps": session.get("steps"),
        "tools": session.get("tools"), "turns": (session.get("followups") or 0) + 1,
    }
    rec = dict(rel=f"{workspace}/{file_name}", slug=slug, model=group, group=group,
               harness=harness, variant=variant, title=title or title_of(session["goal"], stem),
               prompt=key, session=session["session"], followups=stats["followups"],
               date=date, build_min=stats["minutes"], kb=kb, blurb=blurb_for(stats),
               bytes=build["bytes"], workspace=workspace, file_name=file_name)

    # demo file
    if copy_demo:
        src = build.get("local")
        if src is None:
            raise RuntimeError(f"no local copy for {rel}")
        dst = DEMOS / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # generator
    text = read_text()
    text = ensure_group(replace_records(text, rec) if replace else append_records(text, [rec]), group)
    GEN.write_text(text)
    ast.parse(text)

    # prompts
    pj = DOCS / "model-testing-prompts.json"
    pr = json.load(open(pj))
    if key_is_new or norm(pr["spec_prompts"].get(key, "")) != norm(session["goal"]):
        pr["spec_prompts"][key] = session["goal"]
        pj.write_text(json.dumps(pr, indent=1) + "\n")

    # stats
    sj = DOCS / "model-testing-build-stats.json"
    st = json.load(open(sj))
    st[slug] = stats
    sj.write_text(json.dumps(st, indent=1, sort_keys=True) + "\n")

    # serving
    label, mid, kind = serving_for(workspace, session.get("provider"), session.get("model"))
    vp = DOCS / "model-testing-serving.json"
    sv = json.load(open(vp))
    entry = dict(provider=label, kind=kind, model=mid, harness=harness, note=MODEL_NOTE)
    if workspace in SERVING_BY_WORKSPACE:
        entry["note"] = ("Provider and model are the subscription and model Eamon ran the build on; "
                         "the harness session header is not used for them.")
    sv[slug] = entry
    vp.write_text(json.dumps(sv, indent=1, sort_keys=True) + "\n")

    # cards
    cp = DOCS / "model-testing-cards.json"
    cards = json.load(open(cp))
    entry = dict(model=workspace, file=file_name, rel=f"{workspace}/{file_name}", kb=kb,
                 title=stem, date=date, date_iso=build["mtime"][:10])
    cards = [c for c in cards if c.get("rel") != entry["rel"]] if replace else cards
    cards.append(entry)
    cp.write_text(json.dumps(cards, indent=1) + "\n")

    return rec


def mirror(rec: dict, prompt_text: str) -> None:
    src = DEMOS / rec["rel"]
    dst = MIRROR / rec["rel"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    (MIRROR / "prompts").mkdir(exist_ok=True)
    (MIRROR / "prompts" / f"{rec['prompt']}.md").write_text(prompt_text)

    sv = json.load(open(DOCS / "model-testing-serving.json"))
    mp = MIRROR / "serving.json"
    ms = json.load(open(mp)) if mp.exists() else {}
    ms[rec["slug"]] = sv[rec["slug"]]
    mp.write_text(json.dumps(ms, indent=1, sort_keys=True) + "\n")

    readme = MIRROR / "README.md"
    t = readme.read_text()
    n = len(list(MIRROR.rglob("*.html")))
    t = re.sub(r"\b\d+ self-contained browser demos", f"{n} self-contained browser demos", t)
    readme.write_text(t)


def rebuild() -> str:
    p = subprocess.run(["python3", "tools/build_model_gallery.py"], cwd=ROOT,
                       capture_output=True, text=True, timeout=900)
    if p.returncode != 0:
        raise RuntimeError(f"generator failed: {p.stderr[-800:]}")
    return p.stdout.strip().splitlines()[-1]
