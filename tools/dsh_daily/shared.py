"""Keep Desktop\\Model Testing - Shared Builds current.

The folder holds one subfolder per build that at least MIN_MODELS different models made,
one `<Model>.html` per version plus that version's clip when one was recorded. It is rebuilt
from the published gallery records (the source of truth), never edited by hand.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import shutil
import zipfile

from . import ingest, win

MIN_MODELS = 3
FOLD_INTO = {                                     # one brief stored under two prompt keys
    "hungerg-sky-temple": "the-pagoda",           # Eamon: "sky temple and pagoda are the same thing"
}
STAGE = pathlib.Path.home() / ".hermes/profiles/dev/cache/scratch/dsh_daily/shared"
REMOTE_DIR = "C:/Users/Eamon/dsh"
DEST = "C:\\Users\\eamon\\Desktop\\Model Testing - Shared Builds"

# folder names the folder has always used; anything unseen falls back to the title-cased spec
TITLES = {
    "the-pagoda": "The Pagoda",
    "pagoda": "The Pagoda (early brief)",
    "breadfruit-cay": "Breadfruit Cay",
    "linen-on-the-bleaching-green": "Linen on the Bleaching Green",
    "the-basalt-organ": "The Basalt Organ",
    "mangrove-after-dark": "Mangrove After Dark",
    "the-rain-cathedral": "The Rain Cathedral",
    "salt-mirror": "Salt Mirror",
    "croft-at-the-wrack-line": "The Croft at the Wrack Line",
    "the-two-shores-of-kettle-lake": "The Two Shores of Kettle Lake",
    "the-castle": "The Castle",
    "castle": "The Castle",
    "medieval-village": "Medieval Village",
    "the-last-light": "The Last Light",
}

# clips whose file name does not follow `<slug>.mp4`; spec -> {model: file name}
CLIP_ALIASES = {("the-pagoda", "Qwen3.8 Flash-Next"): "qwen3-8-flash-next-sky-temple.mp4"}


def _span(part: str) -> tuple[int, int]:
    start = part.index("dict(rel=")
    depth, i, quote = 0, start, None
    while i < len(part):
        ch = part[i]
        if quote:
            if ch == "\\":
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise RuntimeError("unbalanced record in the generator")


def records(text: str | None = None) -> list[dict]:
    """Every published build record from tools/build_model_gallery.py."""
    text = ingest.read_text() if text is None else text
    out = []
    for part in re.split(r"(?m)^(?=\s{4}dict\(rel=)", text):
        if "dict(rel=" not in part:
            continue
        a, b = _span(part)
        body = part[a:b].rstrip().rstrip(",")
        node = ast.parse("x = " + body).body[0]
        assert isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
        out.append({kw.arg: ast.literal_eval(kw.value) for kw in node.value.keywords})
    return out


def _spec_of(rec: dict, known: set[str]) -> str | None:
    key = rec.get("prompt") or ""
    for cand in (key, key[4:] if key.startswith("the-") else "the-" + key):
        if cand in known:
            return cand
    return None


def _title(spec: str) -> str:
    if spec in TITLES:
        return TITLES[spec]
    return spec.replace("the-", "", 1).replace("-", " ").title()


def _short(spec: str) -> str:
    tail = spec[4:] if spec.startswith("the-") else spec
    return "-".join(tail.split("-")[-2:])


def _prefixes(rows: list[dict]) -> list[tuple[str, str]]:
    """(file-name prefix, model) pairs, longest first: hy4-flash-maya-m- before hy4-flash-."""
    seen: dict[str, str] = {}
    for r in rows:
        tail = r["spec"][4:] if r["spec"].startswith("the-") else r["spec"]
        pre = r["slug"].split(tail)[0] if tail in r["slug"] else r["slug"].rsplit("-", 1)[0] + "-"
        seen.setdefault(pre, r["model"])
    return sorted(seen.items(), key=lambda kv: -len(kv[0]))


def _clips_for(spec: str, recs: list[dict], clips: list[dict], prefixes: list[tuple[str, str]],
               others: set[str]) -> list[dict]:
    """Every clip that belongs to this build, labelled by the model that recorded it.

    A clip counts even when that model has no published page for the build — the recording is
    still evidence the model built it — so the folder shows clips the gallery itself cannot.
    """
    short = _short(spec)
    names = {c["name"] for c in clips}
    out: list[dict] = []
    taken: set[str] = set()

    def add(model: str, clip: dict) -> None:
        if model in taken:
            return
        taken.add(model)
        out.append({"rel": clip["rel"], "as": f"{model}.mp4"})

    # a record's own slug first: exact `<slug>.mp4`, then the pre-slug naming
    for r in recs:
        exact = next((c for c in clips if c["name"] == f"{r['slug']}.mp4"), None)
        if exact:
            add(r["model"], exact)
            continue
        alias = CLIP_ALIASES.get((spec, r["model"]))
        if alias and alias in names:
            add(r["model"], next(c for c in clips if c["name"] == alias))
            continue
        pre = next((p for p, m in prefixes if m == r["model"]), "")
        hit = next((c for c in sorted(clips, key=lambda c: c["name"])
                    if c["name"].startswith(pre) and short in c["name"]), None)
        if hit:
            add(r["model"], hit)

    # then any clip for this build that no published record claimed. A clip named after another
    # build's record (the-pagoda vs the early-brief pagoda) belongs there, not here.
    for c in sorted(clips, key=lambda c: c["name"]):
        if short not in c["name"]:
            continue
        stem = c["name"][:-4]
        if any(stem == o or stem.startswith(o + "-") or o.startswith(stem + "-") for o in others):
            continue
        for pre, model in prefixes:
            if c["name"].startswith(pre):
                add(model, c)
                break
    return out


def build(*, deploy: bool = True) -> dict:
    text = ingest.read_text()
    specs = json.loads((ingest.DOCS / "model-testing-prompts.json").read_text())["spec_prompts"]
    rows = [r for r in records(text) if _spec_of(r, set(specs))]
    for r in rows:
        # a handful of briefs are one build under two names — Eamon: "sky temple and pagoda
        # are the same thing" — so file those under the prompt the group already uses
        r["spec"] = FOLD_INTO.get(r["slug"], _spec_of(r, set(specs)))

    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r["spec"], []).append(r)
    kept = {k: v for k, v in groups.items() if len({r["model"] for r in v}) >= MIN_MODELS}

    shutil.rmtree(STAGE, ignore_errors=True)
    tree = STAGE / "tree"
    tree.mkdir(parents=True)
    written, absent = 0, []
    htmls: dict[str, list[str]] = {}
    for spec, recs in kept.items():
        title = _title(spec)
        folder = tree / title
        folder.mkdir(parents=True, exist_ok=True)
        htmls[title] = []
        for r in recs:
            src = ingest.DEMOS / r["rel"]
            if not src.exists():
                absent.append(r["rel"])
                continue
            name = r["model"]
            if (folder / f"{name}.html").exists():          # two builds of one spec by one model
                name = f"{name} ({r['slug']})"
            shutil.copy2(src, folder / f"{name}.html")
            htmls[title].append(f"{name}.html")
            written += 1

    raw_clips = win.ps("shared_builds.ps1", "list", timeout=600) or "[]"
    clips = json.loads(raw_clips[raw_clips.find("["):raw_clips.rfind("]") + 1] or "[]")
    prefixes = _prefixes(rows)
    slug_spec = {r["slug"]: r["spec"] for r in rows}
    manifest = {"builds": []}
    for spec, recs in sorted(kept.items()):
        others = {s for s, sp in slug_spec.items() if sp != spec}
        title = _title(spec)
        manifest["builds"].append({"name": title, "html": htmls.get(title, []),
                                   "clips": _clips_for(spec, recs, clips, prefixes, others)})

    stage = STAGE
    zpath = stage / "shared-builds.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(tree.rglob("*")):
            if f.is_file():
                zf.write(f, f.relative_to(tree))
    man_path = stage / "shared-manifest.json"
    man_path.write_text(json.dumps(manifest, indent=1))

    result = {"builds_kept": len(kept), "html": written, "html_absent": absent,
              "clips_listed": len(clips), "clips_planned": sum(len(b["clips"]) for b in manifest["builds"]),
              "bytes": zpath.stat().st_size}
    if not deploy:
        result["staged"] = str(zpath)
        return result

    win.push(zpath, "dsh/shared-builds.zip")
    win.push(man_path, "dsh/shared-manifest.json")
    raw = win.ps("shared_builds.ps1", "apply",
                 REMOTE_DIR + "/shared-builds.zip", REMOTE_DIR + "/shared-manifest.json", timeout=1800)
    start = raw.find("{")
    if start < 0:
        raise RuntimeError(f"shared folder script gave no JSON: {raw[:400]}")
    summary = json.loads(raw[start:])
    result.update(summary)
    if summary.get("html") != written:
        raise RuntimeError(f"folder holds {summary.get('html')} html, staged {written}")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
