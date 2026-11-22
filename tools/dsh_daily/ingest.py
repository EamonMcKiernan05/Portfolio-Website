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
    "maya": "Maya M",
    "llama.cpp (maya)": "Maya M",
    "openrouter": "OpenRouter",
}
MODEL_NOTE = ("Session captured from the harness. Model id as configured there; "
              "not checked against the vendor's own model list.")


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


def append_records(text: str, recs: list[dict]) -> str:
    marker = "]\n\nGROUP_ORDER"
    if text.count(marker) != 1:
        raise RuntimeError("cannot find the BUILDS terminator in the generator")
    body = "".join(record_block(r) for r in recs)
    return text.replace(marker, body + marker)


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
    """(key, is_new). Reuse an identical text's key; suffix when the text differs."""
    prompts = json.load(open(DOCS / "model-testing-prompts.json"))["spec_prompts"]
    for key, text in prompts.items():
        if norm(text) == norm(prompt):
            return key, False
    key = slugify(title_of(prompt, stem)) or slugify(stem)
    if key in prompts and norm(prompts[key]) != norm(prompt):
        key = f"{key}-{model_slug}"
    return key, True


# ---------------------------------------------------------------- naming rules

def name_parts(workspace: str, provider: str | None) -> tuple[str, str, str]:
    """(group, variant, harness) from a workspace folder name and provider."""
    group = workspace.strip()
    variant = ""
    harness = "DeepSeek Harness"
    if provider == "maya":
        harness = "Maya M"
        m = re.match(r"^(.*?)\s+Maya\s+(.+)$", group)
        if m:
            group, variant = m.group(1).strip(), "Maya " + m.group(2).strip()
    return group, variant, harness


def _floor(x):
    return int(x) if x is not None else None


def blurb_for(stats: dict) -> str:
    fp, mins, fu = stats.get("first_pass"), stats.get("minutes"), stats.get("followups") or 0
    if not fu:
        return f"One pass, {fp} minutes."
    return (f"{fp} minute first pass, then {fu} follow-up{'s' if fu > 1 else ''} — "
            f"{mins} minutes from goal to finish.")


# ---------------------------------------------------------------- ingestion

def ingest(build: dict, session: dict, *, copy_demo: bool = True) -> dict:
    """Add one build: demo file, records, data files. Returns the record."""
    rel = build["rel"].replace("\\", "/")
    workspace, file_name = rel.split("/", 1)
    stem = pathlib.Path(file_name).stem

    group, variant, harness = name_parts(workspace, session.get("provider"))
    model_slug = slugify(group)
    slug = "-".join(filter(None, [model_slug, slugify(variant), slugify(stem)]))

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
        "minutes": int((finish_ms - t_goal) // 60000),
        "first_pass": int((first_ms - t_goal) // 60000),
        "followups": session.get("followups") or 0, "steps": session.get("steps"),
        "tools": session.get("tools"), "turns": (session.get("followups") or 0) + 1,
    }
    rec = dict(rel=f"{workspace}/{file_name}", slug=slug, model=group, group=group,
               harness=harness, variant=variant, title=title_of(session["goal"], stem),
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
    text = ensure_group(append_records(text, [rec]), group)
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
    provider = session.get("provider") or "Not recorded"
    label = PROVIDER_LABEL.get(provider, provider)
    vp = DOCS / "model-testing-serving.json"
    sv = json.load(open(vp))
    sv[slug] = dict(provider=label, kind="cloud", model=session.get("model") or "not recorded",
                    harness=harness, note=MODEL_NOTE)
    vp.write_text(json.dumps(sv, indent=1, sort_keys=True) + "\n")

    # cards
    cp = DOCS / "model-testing-cards.json"
    cards = json.load(open(cp))
    cards.append(dict(model=workspace, file=file_name, rel=f"{workspace}/{file_name}", kb=kb,
                      title=stem, date=date, date_iso=build["mtime"][:10]))
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
