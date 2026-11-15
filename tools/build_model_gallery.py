#!/usr/bin/env python3
"""Generate the Model testing gallery index and per-build pages.

Reads docs/model-testing-cards.json (what is on disk) plus the prompt sources, and writes
gallery.html and gallery/model-testing/<slug>.html.
"""
import html
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DEMOS = ROOT / "demos" / "model-testing"
OUT = ROOT / "gallery" / "model-testing"

SITE = "https://eamonmckiernan05.github.io/Portfolio-Website"
REPO = "https://github.com/EamonMcKiernan05/Local-LLM-Testing/tree/main/Model%20Testing%20Gallery"

# ---------------------------------------------------------------- build metadata
# rel (under demos/model-testing) -> display data
BUILDS = [
    # Qwen3.8-27B
    dict(rel="Qwen3.8-27B/DFlash2/pagoda.html", slug="qwen38-27b-dflash2-pagoda",
         model="Qwen3.8-27B", group="Qwen3.8-27B", variant="DFlash2 config",
         title="The Pagoda — DFlash2", prompt="pagoda", session="65225474", followups=0,
         blurb="The full pagoda brief in one shot on the DFlash2 serving config."),
    dict(rel="Qwen3.8-27B/DSpine/THE-PAGODA.html", slug="qwen38-27b-dspine-pagoda",
         model="Qwen3.8-27B", group="Qwen3.8-27B", variant="DSpine config",
         title="The Pagoda — DSpine", prompt="pagoda", session="25c560ee", followups=4,
         blurb="Same brief, four follow-ups — the run that kept iterating on roof and path fixes."),
    dict(rel="Qwen3.8-27B/MTP/sky-temple.html", slug="qwen38-27b-mtp-pagoda",
         model="Qwen3.8-27B", group="Qwen3.8-27B", variant="MTP config",
         title="The Pagoda — MTP", prompt="pagoda", session="6133e5ab", followups=1,
         blurb="MTP serving config, one follow-up, the pagoda landing as a sky temple."),
    dict(rel="Qwen3.8-27B/Plain/pagoda.html", slug="qwen38-27b-plain-pagoda",
         model="Qwen3.8-27B", group="Qwen3.8-27B", variant="Plain config",
         title="The Pagoda — Plain", prompt="pagoda", session="004a6560", followups=0,
         blurb="Stock config, single shot — the control run for the three above."),
    # Qwen 4 Preview
    dict(rel="Qwen 4 Preview/liberty-1886.html", slug="qwen4-preview-liberty",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="",
         title="Liberty Island, 1886", prompt="liberty", session="17131dd2", followups=3,
         blurb="A voxel diorama of Liberty Island and the New York waterfront in autumn 1886."),
    dict(rel="Qwen 4 Preview/medieval-village.html", slug="qwen4-preview-village",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="",
         title="Alderbrook — medieval village", prompt="village", session="33c57346", followups=0,
         blurb="A medieval village at golden hour, one shot, no fixes."),
    dict(rel="Qwen 4 Preview/the-pagoda.html", slug="qwen4-preview-pagoda",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="",
         title="The Pagoda", prompt="pagoda", session="c23fdca6", followups=1,
         blurb="The pagoda brief again, one follow-up — its largest file of the set."),
    dict(rel="Qwen 4 Preview/torchlight-depths.html", slug="qwen4-preview-torchlight",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="",
         title="Torchlight Depths", prompt="torchlight", session="c00f5356", followups=0,
         blurb="A self-playing isometric dungeon crawler — the model animates the torchbearer itself."),
    # Qwen Code
    dict(rel="QwenCode/sky-temple.html", slug="qwen-code-sky-temple",
         model="Qwen Code", group="Qwen Code", variant="CLI, Qwen 4 Max Preview",
         title="Sky Temple", prompt="pagoda", session="6bb0ae54", followups=2,
         blurb="The pagoda brief run through Qwen Code with two follow-ups."),
    dict(rel="QwenCode/medieval-village.html", slug="qwen-code-village",
         model="Qwen Code", group="Qwen Code", variant="CLI, Qwen 4 Max Preview",
         title="Alderglen — medieval village", prompt="village", session="0886538b", followups=0,
         blurb="The village brief, one shot, from the CLI agent rather than the harness."),
    dict(rel="QwenCode/liberty-1886.html", slug="qwen-code-liberty",
         model="Qwen Code", group="Qwen Code", variant="CLI, Qwen 4 Max Preview",
         title="Liberty Island, 1886", prompt="liberty", session="787d2fe5", followups=4,
         blurb="Liberty Island after four follow-ups — the most iterated build in the set."),
    dict(rel="QwenCode/lbuild/baseline-gap.html", slug="qwen-code-liberty-baseline",
         model="Qwen Code", group="Qwen Code", variant="CLI, Qwen 4 Max Preview",
         title="Liberty Island — baseline gap", prompt="liberty", session="787d2fe5", followups=4,
         blurb="A second build from the same session, kept as the comparison baseline."),
    # DeepSeek V4.1 Flash
    dict(rel="DeepSeek-V4.1-Flash-1017/THE-CASTLE.html", slug="deepseek-v41-castle",
         model="DeepSeek V4.1 Flash", group="DeepSeek V4.1 Flash", variant="",
         title="The Castle", prompt="castle", session="23f01a1f", followups=0,
         blurb="The castle brief, one shot, the largest single render in the gallery."),
    dict(rel="DeepSeek-V4.1-Flash-1017/sky-temple-DeepSeek-V4.1-Flash-1017.html", slug="deepseek-v41-sky-temple",
         model="DeepSeek V4.1 Flash", group="DeepSeek V4.1 Flash", variant="",
         title="Sky Temple", prompt="pack:sky-temple", session="", followups=None,
         blurb="The bench pack's raw-WebGL Sky Temple brief, before the session logs start."),
    dict(rel="DeepSeek-V4.1-Flash-1017/test1-deepseek-v4.1-flash-1017.html", slug="deepseek-v41-nightfall",
         model="DeepSeek V4.1 Flash", group="DeepSeek V4.1 Flash", variant="",
         title="Nightfall — procedural city", prompt="pack:dusk-cityline", session="", followups=None,
         note="Built on the retired v2-era city brief, not today's Dusk Cityline text.",
         blurb="A procedural city at night — kept because it was the first convincing city render."),
    # MiniMax M3.1 Flash
    dict(rel="MiniMax M3.1-Flash Tests/sky-temple-minimax-m3-1-flash.html", slug="minimax-m31-sky-temple",
         model="MiniMax M3.1 Flash", group="MiniMax M3.1 Flash", variant="",
         title="Sky Temple", prompt="pack:sky-temple", session="", followups=None,
         blurb="Sky Temple from the v3 pack — the rebuild that replaced the flat v2 attempt."),
    dict(rel="MiniMax M3.1-Flash Tests/dusk-cityline-minimax-m3.1-flash.html", slug="minimax-m31-dusk-cityline",
         model="MiniMax M3.1 Flash", group="MiniMax M3.1 Flash", variant="",
         title="Dusk Cityline", prompt="pack:dusk-cityline", session="", followups=None,
         blurb="CSS 3D only — no WebGL allowed — and it still reads as a city at dusk."),
    # HY4
    dict(rel="HY4/THE-CASTLE.html", slug="hy4-castle",
         model="HY4", group="HY4", variant="",
         title="The Castle", prompt="castle", session="61dd0d47", followups=0,
         blurb="The castle brief on HY4, one shot."),
    # LongCat 2.5
    dict(rel="LongCat-2.5/sky-temple.html", slug="longcat-25-sky-temple",
         model="LongCat 2.5", group="LongCat 2.5", variant="",
         title="Sky Temple", prompt="pagoda", session="763e2897", followups=5,
         blurb="The pagoda brief on LongCat, five follow-ups before it settled."),
]

GROUP_ORDER = ["Qwen3.8-27B", "Qwen 4 Preview", "Qwen Code", "DeepSeek V4.1 Flash",
               "MiniMax M3.1 Flash", "HY4", "LongCat 2.5"]
GROUP_BLURB = {
    "Qwen3.8-27B": "27B dense model, Q8_K_XL, four serving configurations — the same brief four times to isolate the engine's effect on craft.",
    "Qwen 4 Preview": "The preview build of Qwen 4, run through the DeepSeek Harness with one prompt per build.",
    "Qwen Code": "The same model driven through the Qwen Code CLI instead of the harness — agent scaffolding changes the output.",
    "DeepSeek V4.1 Flash": "DeepSeek's Flash tier on the same castle, sky-temple and city briefs.",
    "MiniMax M3.1 Flash": "Two surviving v3-pack runs. The earlier v2-era attempts are retired with the prompts that made them.",
    "HY4": "A single castle build from HY4.",
    "LongCat 2.5": "LongCat 2.5 on the pagoda brief, five follow-ups in.",
}

sess = json.load(open(DOCS / "model-testing-prompts.json"))
pack = json.load(open(DOCS / "pack-prompts.json"))


def pack_prompt(name):
    for k, v in pack.items():
        if k.lower().startswith(name.lower()):
            return re.sub(r"^```text\n", "", re.sub(r"\n```$", "", v)).strip()
    raise KeyError(name)


def prompt_for(key):
    if key.startswith("pack:"):
        n = key.split(":", 1)[1]
        return pack_prompt("Sky Temple" if n == "sky-temple" else "Dusk Cityline")
    return sess["spec_prompts"][key]


CARDS = {(c["rel"].replace("\\", "/")): c for c in json.load(open(DOCS / "model-testing-cards.json"))}


def meta(rel):
    """Size and the ORIGINAL build date — the files were copied into the repo, so mtime lies."""
    p = DEMOS / rel
    kb = max(1, round(p.stat().st_size / 1024))
    c = CARDS.get(rel.replace("\\", "/"), {})
    return kb, c.get("date", "")


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="Eamon McKiernan">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Eamon McKiernan">
<meta property="og:locale" content="en_GB">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="{css}">
<link rel="icon" href="{icon}favicon.svg" type="image/svg+xml">
<link rel="icon" href="{icon}favicon-32.png" sizes="32x32" type="image/png">
<link rel="apple-touch-icon" href="{icon}apple-touch-icon.png">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<main id="main">
<div class="wrap gal-wrap">
"""

RUN_JS = """<script>
document.querySelectorAll('[data-run]').forEach(function(btn){
  btn.addEventListener('click', function(){
    var art = btn.closest('.gal-res');
    var box = art.querySelector('.gal-run');
    var fr = box.querySelector('iframe');
    if (box.hidden) {
      fr.src = fr.getAttribute('data-src');
      box.hidden = false;
      btn.textContent = 'stop';
      btn.classList.add('on');
    } else {
      fr.src = 'about:blank';
      box.hidden = true;
      btn.textContent = 'run in this page';
      btn.classList.remove('on');
    }
  });
});
</script>
"""


def build_page(b):
    kb, mt = meta(b["rel"])
    prompt = prompt_for(b["prompt"])
    demo = "../../demos/model-testing/" + b["rel"]
    src = REPO + "/" + b["rel"].replace(" ", "%20")
    if b["session"]:
        prompt_meta = (f"Prompt captured from DeepSeek Harness session "
                       f"<code>{b['session']}</code>"
                       + (f", {b['followups']} follow-up{'s' if b['followups'] != 1 else ''}"
                          if b["followups"] else ", one shot, no follow-ups"))
    else:
        prompt_meta = "Prompt from the one-shot demo bench pack (v3.4)"
    note = f'<p class="gal-meta">{html.escape(b["note"])}</p>' if b.get("note") else ""
    return HEAD.format(
        title=f"{html.escape(b['title'])} &middot; {html.escape(b['model'])} &middot; Model testing gallery — Eamon McKiernan",
        desc=html.escape(f"{b['title']} — {b['model']}. The one-shot prompt, verbatim, and the build it produced."),
        ogtitle=html.escape(f"{b['title']} — {b['model']}"),
        css="../../assets/site.css", icon="../../assets/") + f"""
  <div class="gal-top">
    <a class="gal-back" href="../../gallery.html">&#8592;&nbsp;model testing gallery</a>
  </div>

  <h1 class="gal-h1">{html.escape(b['title'])}</h1>
  <p class="gal-lede">{html.escape(b['blurb'])}</p>
  <p class="gal-meta">{html.escape(b['model'])}{(' &middot; ' + html.escape(b['variant'])) if b['variant'] else ''} &middot; {kb} KB &middot; {mt}</p>
  {note}

  <section class="gal-sec">
    <div class="gal-sec-h"><span class="gal-sec-n">01</span><div class="gal-sec-t">The build</div><span class="gal-sec-rule"></span></div>
    <div class="gal-sec-s">One-shot output, unedited. Run it here or open it full size.</div>
    <article class="gal-res">
      <div class="gal-rt">
        <div class="gal-rb">
          <div class="gal-rt-t">{html.escape(b['title'])}</div>
          <div class="gal-rm">{html.escape(b['model'])} &middot; {kb} KB &middot; {mt}</div>
          <div class="gal-rd">{html.escape(b['blurb'])}</div>
          <div class="gal-ra">
            <button class="gal-btn" type="button" data-run>run in this page</button>
            <a class="gal-btn go" href="{demo}" target="_blank" rel="noopener">open in new tab &#8599;</a>
            <a class="gal-btn" href="{src}" target="_blank" rel="noopener">source &#8599;</a>
          </div>
        </div>
      </div>
      <div class="gal-run" hidden>
        <iframe src="about:blank" data-src="{demo}" title="{html.escape(b['title'])} — live demo" sandbox="allow-scripts allow-same-origin allow-pointer-lock" allowfullscreen></iframe>
        <div class="gal-runhint">Runs sandboxed in this page — click inside to interact.</div>
      </div>
    </article>
  </section>

  <section class="gal-sec">
    <div class="gal-sec-h"><span class="gal-sec-n">02</span><div class="gal-sec-t">The prompt</div><span class="gal-sec-rule"></span></div>
    <div class="gal-sec-s">{prompt_meta}.</div>
    <pre class="gal-prompt">{html.escape(prompt)}</pre>
  </section>

  <footer>
    <div class="gal-f1">&copy; 2026 Eamon McKiernan &mdash; <a href="../../gallery.html">model testing gallery</a></div>
    <div class="gal-f2">Sources and prompts: <a href="https://github.com/EamonMcKiernan05/Local-LLM-Testing" target="_blank" rel="noopener">github.com/EamonMcKiernan05/Local-LLM-Testing</a>. No tracking.</div>
  </footer>

</div>
{RUN_JS}</main>
</body>
</html>
"""


def index_page():
    by_group = {}
    for b in BUILDS:
        by_group.setdefault(b["group"], []).append(b)
    sections = []
    n = 0
    for g in GROUP_ORDER:
        items = by_group.get(g, [])
        if not items:
            continue
        n += 1
        cards = []
        for b in items:
            kb, mt = meta(b["rel"])
            fol = ("no session log" if b["followups"] is None
                   else ("one shot" if b["followups"] == 0
                         else f"{b['followups']} follow-up{'s' if b['followups'] != 1 else ''}"))
            cards.append(f"""      <a class="gal-card" href="gallery/model-testing/{b['slug']}.html">
        <div class="gal-body">
          <div class="gal-t">{html.escape(b['title'])}</div>
          <div class="gal-m">{html.escape(b['model'])}{(' &middot; ' + html.escape(b['variant'])) if b['variant'] else ''}</div>
          <div class="gal-d">{html.escape(b['blurb'])}</div>
          <div class="gal-m">{mt} &middot; {kb} KB &middot; {fol}</div>
          <div class="gal-go">prompt + build &#8594;</div>
        </div>
      </a>""")
        sections.append(f"""  <section class="gal-sec">
    <div class="gal-sec-h"><span class="gal-sec-n">{n:02d}</span><div class="gal-sec-t">{html.escape(g)}</div><span class="gal-sec-rule"></span></div>
    <div class="gal-sec-s">{html.escape(GROUP_BLURB[g])} &middot; {len(items)} build{'s' if len(items) != 1 else ''}.</div>
    <div class="gal-grid">
{chr(10).join(cards)}
    </div>
  </section>""")
    total = len(BUILDS)
    return HEAD.format(
        title="Model testing gallery — Eamon McKiernan",
        desc="One-shot browser demos written by AI models running on my own hardware, organised by model. Every build published unedited, with the prompt that made it.",
        ogtitle="Model testing gallery — one-shot demos, grouped by model",
        css="assets/site.css", icon="assets/") + f"""
  <div class="gal-top">
    <a class="gal-back" href="index.html">&#8592;&nbsp;Eamon McKiernan</a>
  </div>

  <h1 class="gal-h1">Model testing gallery</h1>
  <p class="gal-lede">{total} one-shot browser demos written by AI models running on my own hardware, grouped by the model that wrote them. One prompt, one self-contained HTML file, no fixes — published as they came out, defects and all.</p>
  <p class="gal-meta">{len(GROUP_ORDER)} models &middot; {total} builds &middot; prompts quoted verbatim</p>

{chr(10).join(sections)}

  <footer>
    <div class="gal-f1">&copy; 2026 Eamon McKiernan &mdash; <a href="index.html">back to the portfolio</a></div>
    <div class="gal-f2">Prompts and sources: <a href="https://github.com/EamonMcKiernan05/Local-LLM-Testing" target="_blank" rel="noopener">github.com/EamonMcKiernan05/Local-LLM-Testing</a>. No tracking.</div>
  </footer>

</div>
</main>
</body>
</html>
"""


def main():
    missing = [b["rel"] for b in BUILDS if not (DEMOS / b["rel"]).exists()]
    if missing:
        raise SystemExit("missing demo files: " + ", ".join(missing))
    OUT.mkdir(parents=True, exist_ok=True)
    for b in BUILDS:
        (OUT / f"{b['slug']}.html").write_text(build_page(b))
    (ROOT / "gallery.html").write_text(index_page())
    print(f"wrote gallery.html + {len(BUILDS)} build pages into {OUT}")


if __name__ == "__main__":
    main()
