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
         model="Qwen3.8-27B", group="Qwen3.8-27B", harness="DeepSeek Harness", variant="DFlash2 config",
         title="The Pagoda — DFlash2", prompt="pagoda", session="65225474", followups=0,
         blurb="The full pagoda brief in one shot on the DFlash2 serving config."),
    dict(rel="Qwen3.8-27B/DSpine/THE-PAGODA.html", slug="qwen38-27b-dspine-pagoda",
         model="Qwen3.8-27B", group="Qwen3.8-27B", harness="DeepSeek Harness", variant="DSpine config",
         title="The Pagoda — DSpine", prompt="pagoda", session="25c560ee", followups=4,
         blurb="Same brief, four follow-ups — the run that kept iterating on roof and path fixes."),
    dict(rel="Qwen3.8-27B/MTP/sky-temple.html", slug="qwen38-27b-mtp-pagoda",
         model="Qwen3.8-27B", group="Qwen3.8-27B", harness="DeepSeek Harness", variant="MTP config",
         title="The Pagoda — MTP", prompt="pagoda", session="6133e5ab", followups=1,
         blurb="MTP serving config, one follow-up, the pagoda landing as a sky temple."),
    dict(rel="Qwen3.8-27B/Plain/pagoda.html", slug="qwen38-27b-plain-pagoda",
         model="Qwen3.8-27B", group="Qwen3.8-27B", harness="DeepSeek Harness", variant="Plain config",
         title="The Pagoda — Plain", prompt="pagoda", session="004a6560", followups=0,
         blurb="Stock config, single shot — the control run for the three above."),
    # Qwen 4 Preview
    dict(rel="Qwen 4 Preview/liberty-1886.html", slug="qwen4-preview-liberty",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="DeepSeek Harness",
         title="Liberty Island, 1886", prompt="liberty", session="17131dd2", followups=3,
         blurb="A voxel diorama of Liberty Island and the New York waterfront in autumn 1886."),
    dict(rel="Qwen 4 Preview/medieval-village.html", slug="qwen4-preview-village",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="DeepSeek Harness",
         title="Alderbrook — medieval village", prompt="village", session="33c57346", followups=0,
         blurb="A medieval village at golden hour, one shot, no fixes."),
    dict(rel="Qwen 4 Preview/the-pagoda.html", slug="qwen4-preview-pagoda",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="DeepSeek Harness",
         title="The Pagoda", prompt="pagoda", session="c23fdca6", followups=1,
         blurb="The pagoda brief again, one follow-up — its largest file of the set."),
    dict(rel="Qwen 4 Preview/torchlight-depths.html", slug="qwen4-preview-torchlight",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="DeepSeek Harness",
         title="Torchlight Depths", prompt="torchlight", session="c00f5356", followups=0,
         blurb="A self-playing isometric dungeon crawler — the model animates the torchbearer itself."),
    # Qwen Code
    dict(rel="QwenCode/sky-temple.html", slug="qwen-code-sky-temple",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="Qwen Code",
         title="Sky Temple", prompt="pagoda", session="6bb0ae54", followups=2,
         blurb="The pagoda brief run through Qwen Code with two follow-ups."),
    dict(rel="QwenCode/medieval-village.html", slug="qwen-code-village",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="Qwen Code",
         title="Alderglen — medieval village", prompt="village", session="0886538b", followups=0,
         blurb="The village brief, one shot, from the CLI agent rather than the harness."),
    dict(rel="QwenCode/liberty-1886.html", slug="qwen-code-liberty",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="Qwen Code",
         title="Liberty Island, 1886", prompt="liberty", session="787d2fe5", followups=4,
         blurb="Liberty Island after four follow-ups — the most iterated build in the set."),
    dict(rel="QwenCode/lbuild/baseline-gap.html", slug="qwen-code-liberty-baseline",
         model="Qwen 4 Preview", group="Qwen 4 Preview", variant="", harness="Qwen Code",
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
    # Qwen3.8 Flash-Next — the builds that were already on the site
    dict(rel="Qwen3.8 Flash-Next/sky-temple.html", slug="qwen38-flash-next-sky-temple",
         model="Qwen3.8 Flash-Next", group="Qwen3.8 Flash-Next", variant="", harness="DeepSeek Harness",
         title="Sky Temple", prompt="legacy-sky-temple", session="", followups=0,
         date="4 Oct 2026", kb=66,
         blurb="The original bench run — one message, the file it produced. Still the best of the set."),
    dict(rel="Qwen3.8 Flash-Next/sky-temple-agent.html", slug="qwen38-flash-next-sky-temple-agent",
         model="Qwen3.8 Flash-Next", group="Qwen3.8 Flash-Next", variant="", harness="DeepSeek Harness",
         title="Sky Temple — agent rebuild", prompt="legacy-sky-temple", session="", followups=None,
         date="6 Oct 2026", kb=38,
         blurb="The same prompt driven by an agent loop instead of one shot — smaller, tidier, less alive."),
    dict(rel="Qwen3.8 Flash-Next/living-city.html", slug="qwen38-flash-next-living-city",
         model="Qwen3.8 Flash-Next", group="Qwen3.8 Flash-Next", variant="", harness="DeepSeek Harness",
         title="Living City", prompt="legacy-living-city", session="", followups=0,
         date="4 Oct 2026", kb=79,
         blurb="A procedural city with traffic and pedestrians, generated and animated in one file."),
    dict(rel="Qwen3.8 Flash-Next/neon-drift.html", slug="qwen38-flash-next-neon-drift",
         model="Qwen3.8 Flash-Next", group="Qwen3.8 Flash-Next", variant="", harness="DeepSeek Harness",
         title="Neon Drift", prompt="legacy-neon-drift", session="", followups=0,
         date="5 Oct 2026", kb=34,
         blurb="A playable synthwave racer — the smallest file that still plays."),
    dict(rel="Qwen3.8 Flash-Next/pulse-engine.html", slug="qwen38-flash-next-pulse-engine",
         model="Qwen3.8 Flash-Next", group="Qwen3.8 Flash-Next", variant="", harness="DeepSeek Harness",
         title="Pulse Engine", prompt="legacy-pulse-engine", session="", followups=0,
         date="5 Oct 2026", kb=59,
         blurb="A generative audio-visual engine that reacts to its own soundtrack."),
    dict(rel="Qwen3.8 Flash-Next/cloth-lab.html", slug="qwen38-flash-next-cloth-lab",
         model="Qwen3.8 Flash-Next", group="Qwen3.8 Flash-Next", variant="", harness="DeepSeek Harness",
         title="Cloth Lab", prompt="legacy-cloth-lab", session="", followups=0,
         date="5 Oct 2026", kb=40,
         blurb="Cloth physics written from scratch — no library, no solver borrowed."),
    # the October Qwen3.8-27B build that was on the site
    dict(rel="Qwen3.8-27B/Plain/sky-temple-oct.html", slug="qwen38-27b-sky-temple-oct",
         model="Qwen3.8-27B", group="Qwen3.8-27B", variant="", harness="DeepSeek Harness",
         title="Sky Temple — October run", prompt="legacy-sky-temple", session="", followups=0,
         date="6 Oct 2026", kb=41,
         blurb="The 27B model on the Sky Temple brief a month before the pagoda runs."),
]

GROUP_ORDER = ["Qwen3.8 Flash-Next", "Qwen3.8-27B", "Qwen 4 Preview", "DeepSeek V4.1 Flash",
               "MiniMax M3.1 Flash", "HY4", "LongCat 2.5"]
GROUP_BLURB = {
    "Qwen3.8 Flash-Next": "The model the gallery started with — Qwen3.8 Flash-Next on Strata, one prompt per build, back in early October.",
    "Qwen3.8-27B": "27B dense model, Q8_K_XL, four serving configurations — the same brief four times to isolate the engine's effect on craft.",
    "Qwen 4 Preview": "The preview build of Qwen 4, run two ways — the DeepSeek Harness and the Qwen Code CLI. Same model, different scaffolding, so the builds are split by harness.",
    "DeepSeek V4.1 Flash": "DeepSeek's Flash tier on the same castle, sky-temple and city briefs.",
    "MiniMax M3.1 Flash": "Two surviving v3-pack runs. The earlier v2-era attempts are retired with the prompts that made them.",
    "HY4": "A single castle build from HY4.",
    "LongCat 2.5": "LongCat 2.5 on the pagoda brief, five follow-ups in.",
}

sess = json.load(open(DOCS / "model-testing-prompts.json"))
pack = json.load(open(DOCS / "pack-prompts.json"))
SERVING = json.load(open(DOCS / "model-testing-serving.json"))


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


def meta(b):
    """Size and the ORIGINAL build date — the files were copied into the repo, so mtime lies."""
    p = DEMOS / b["rel"]
    kb = b.get("kb") or max(1, round(p.stat().st_size / 1024))
    c = CARDS.get(b["rel"].replace("\\", "/"), {})
    return kb, b.get("date") or c.get("date", "")


STYLE = """<style>
:root{
  --bg:#15130F; --ink:#EDE5D8; --dim:#9A9184; --quiet:#585147; --line:#332E27; --line-strong:#4a4132; --accent:#D8A73C;
  --display:'Franklin Gothic Demi Cond','Franklin Gothic Medium Cond','Franklin Gothic Medium','Franklin Gothic','Arial Narrow',Arial,sans-serif;
  --sans:ui-sans-serif,system-ui,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
  --mono:'DejaVu Sans Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace;
  --ease:cubic-bezier(.22,.61,.36,1);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.65;font-size:16px;-webkit-font-smoothing:antialiased}
::selection{background:rgba(216,167,60,.25)}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(216,167,60,.32);transition:border-color .2s,color .2s}
a:hover{border-color:var(--accent)}
a:focus-visible,button:focus-visible{outline:1px solid var(--accent);outline-offset:3px}
code{font-family:var(--mono);font-size:.9em;background:#1d1a14;padding:1px 5px;color:var(--ink)}
.skip{position:absolute;left:-9999px}
.skip:focus{left:16px;top:16px;z-index:9;background:var(--bg);border:1px solid var(--accent);padding:8px 14px;font-family:var(--mono);font-size:12px}
.wrap{max-width:1180px;margin:0 auto;padding:0 32px}

/* top + headings */
.gal-top{padding:34px 0 0}
.gal-back{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim);border:0}
.gal-back:hover{color:var(--accent)}
.gal-h1{font-family:var(--display);font-weight:600;font-size:clamp(40px,7.4vw,88px);line-height:.94;letter-spacing:-.01em;margin:26px 0 0;max-width:18ch}
.gal-lede{font-size:clamp(16px,1.9vw,19px);color:var(--dim);max-width:62ch;margin-top:22px}
.gal-meta{font-family:var(--mono);font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--quiet);margin-top:18px;line-height:1.8}

/* sections + subsections (collapsible) */
.gal-sec{margin-top:76px}
.gal-sec-m{margin-top:76px}
.gal-sec-m>summary{display:flex;align-items:baseline;gap:16px;cursor:pointer;list-style:none;padding:2px 0}
.gal-sec-m>summary::-webkit-details-marker{display:none}
.gal-sec-m>summary:hover .gal-sec-t{color:#fff}
.gal-sec-n{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;color:var(--accent);flex-shrink:0}
.gal-sec-t{font-family:var(--display);font-size:clamp(22px,2.8vw,30px);font-weight:600;letter-spacing:-.005em;transition:color .2s}
.gal-sec-rule{flex:1;height:1px;background:var(--line);align-self:center;min-width:24px}
.gal-sec-c{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--quiet);flex-shrink:0}
.gal-sec-m>summary::after{content:"+";font-family:var(--sans);font-size:19px;font-weight:400;line-height:1;color:var(--accent);flex-shrink:0;width:16px;text-align:center}
.gal-sec-m[open]>summary::after{content:"–"}
.gal-sec-s{font-size:14.5px;color:var(--quiet);margin:12px 0 26px;max-width:74ch}

/* harness subsection */
.gal-h{margin:30px 0 0}
.gal-h>summary{display:flex;align-items:baseline;gap:12px;cursor:pointer;list-style:none;padding:0 0 11px;border-bottom:1px solid var(--line)}
.gal-h>summary::-webkit-details-marker{display:none}
.gal-h-t{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--dim);transition:color .2s}
.gal-h[open]>summary .gal-h-t,.gal-h>summary:hover .gal-h-t{color:var(--ink)}
.gal-h-c{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--quiet);margin-left:auto}
.gal-h>summary::after{content:"+";font-family:var(--sans);font-size:15px;line-height:1;color:var(--dim);width:13px;text-align:center}
.gal-h[open]>summary::after{content:"–";color:var(--accent)}
.gal-h .gal-grid{margin-top:22px}

/* cards (index) */
.gal-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));border-top:1px solid var(--line);border-left:1px solid var(--line)}
.gal-card{display:block;background:var(--bg);padding:24px 24px 20px;border:0;border-right:1px solid var(--line);border-bottom:1px solid var(--line);color:inherit;transition:background .22s var(--ease)}
.gal-card:hover{background:#1b1812}
.gal-t{font-family:var(--display);font-size:19px;font-weight:600;letter-spacing:.005em;color:var(--ink);line-height:1.2}
.gal-m{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--quiet);margin-top:9px}
.gal-d{font-size:14px;color:var(--dim);margin-top:12px;line-height:1.6;min-height:3.2em}
.gal-go{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-top:16px;opacity:.75;transition:opacity .2s,transform .2s var(--ease)}
.gal-card:hover .gal-go{opacity:1;transform:translateX(3px)}

/* build page */
.gal-res{border:1px solid var(--line)}
.gal-rt{padding:26px}
.gal-rt-t{font-family:var(--display);font-size:22px;font-weight:600}
.gal-rm{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--quiet);margin-top:8px}
.gal-rd{font-size:14.5px;color:var(--dim);margin-top:14px;max-width:70ch}
.gal-ra{display:flex;flex-wrap:wrap;gap:10px;margin-top:22px}
.gal-btn{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim);background:transparent;border:1px solid var(--line-strong);padding:10px 16px;cursor:pointer;transition:color .2s,border-color .2s,background .2s}
.gal-btn:hover{color:var(--ink);border-color:var(--accent)}
.gal-btn.on{color:var(--bg);background:var(--accent);border-color:var(--accent)}
.gal-btn.go{color:var(--ink);border-color:var(--line-strong)}
a.gal-btn{border-bottom:1px solid var(--line-strong)}
a.gal-btn:hover{border-bottom-color:var(--accent)}
.gal-run{border-top:1px solid var(--line);background:#0f0d0a}
.gal-run iframe{display:block;width:100%;height:min(78vh,720px);border:0;background:#000}
.gal-runhint{font-family:var(--mono);font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--quiet);padding:10px 16px;border-top:1px solid var(--line)}

/* prompt */
.gal-prompt{font-family:var(--mono);font-size:12.5px;line-height:1.75;color:#d6cdbd;background:#1b1812;border:1px solid var(--line);padding:22px;white-space:pre-wrap;word-break:break-word;max-height:640px;overflow:auto}
.gal-prompt::selection{background:rgba(216,167,60,.3)}

/* serving chips + description list */
.gal-chip{display:inline-block;font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;padding:3px 8px;border:1px solid var(--line-strong);color:var(--dim);margin-top:12px}
.gal-chip.local{color:var(--accent);border-color:rgba(216,167,60,.45)}
.gal-chip.cloud{color:var(--quiet)}
.gal-chip.unknown{color:var(--quiet);border-style:dashed}
.gal-dl{display:grid;grid-template-columns:170px 1fr;column-gap:0;margin-top:24px;border-top:1px solid var(--line)}
.gal-dl dt{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--quiet);padding:15px 18px 15px 0;border-bottom:1px solid var(--line)}
.gal-dl dd{font-size:14px;color:var(--dim);padding:15px 0;border-bottom:1px solid var(--line);line-height:1.62}

/* footer */
footer{border-top:1px solid var(--line);margin:84px 0 0;padding:26px 0 60px;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}
.gal-f1,.gal-f2{font-family:var(--mono);font-size:11px;letter-spacing:.06em;color:var(--quiet)}
.gal-f2 a{color:var(--quiet);border-bottom-color:var(--line-strong)}
.gal-f2 a:hover{color:var(--accent)}

@media(max-width:760px){
  .wrap{padding:0 20px}
  .gal-sec{margin-top:54px}
  .gal-grid{grid-template-columns:1fr}
  .gal-d{min-height:0}
  .gal-run iframe{height:60vh}
  .gal-rt{padding:20px}
  .gal-prompt{font-size:11.5px;padding:16px;max-height:none}
  .gal-dl{grid-template-columns:1fr}
  .gal-dl dt{padding:12px 0 0;border-bottom:0}
  .gal-dl dd{padding:6px 0 14px}
  footer{flex-direction:column;gap:10px}
}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>"""


HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="Eamon McKiernan">
<meta name="theme-color" content="#15130F">
<meta property="og:title" content="{ogtitle}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Eamon McKiernan">
<meta property="og:locale" content="en_GB">
<meta name="twitter:card" content="summary_large_image">
{style}
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


def serving_rows(b):
    sv = SERVING.get(b["slug"], {})
    kind = sv.get("kind", "")
    rows = []
    if sv.get("provider"):
        rows.append(("Provider", sv["provider"]))
    if sv.get("harness"):
        rows.append(("Harness", sv["harness"]))
    if sv.get("model"):
        rows.append(("Model", sv["model"]))
    if sv.get("endpoint") and kind == "local":
        rows.append(("Endpoint", sv["endpoint"]))
    if sv.get("config"):
        rows.append(("Serving config", sv["config"]))
    if sv.get("measured"):
        rows.append(("Measured", sv["measured"]))
    body = "".join(
        f'      <dt>{html.escape(k)}</dt><dd>{html.escape(v).replace(chr(10), "<br>")}</dd>\n'
        for k, v in rows)
    note = ""
    if sv.get("note"):
        note += f'<p class="gal-sec-s">{html.escape(sv["note"])}</p>'
    return note + '<dl class="gal-dl">\n' + body + '    </dl>'


def build_page(b):
    kb, mt = meta(b)
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
        style=STYLE) + f"""
  <div class="gal-top">
    <a class="gal-back" href="../../gallery.html">&#8592;&nbsp;model testing gallery</a>
  </div>

  <h1 class="gal-h1">{html.escape(b['title'])}</h1>
  <p class="gal-lede">{html.escape(b['blurb'])}</p>
  <p class="gal-meta">{html.escape(b['model'])}{(' &middot; ' + html.escape(b['harness'])) if b.get('harness') else ''}{(' &middot; ' + html.escape(b['variant'])) if b['variant'] else ''} &middot; {kb} KB &middot; {mt}</p>
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
    <div class="gal-sec-h"><span class="gal-sec-n">02</span><div class="gal-sec-t">How it was served</div><span class="gal-sec-rule"></span></div>
    {serving_rows(b)}
  </section>

  <section class="gal-sec">
    <div class="gal-sec-h"><span class="gal-sec-n">03</span><div class="gal-sec-t">The prompt</div><span class="gal-sec-rule"></span></div>
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


def card_html(b):
    kb, mt = meta(b)
    fol = ("no session log" if b["followups"] is None
           else ("one shot" if b["followups"] == 0
                 else f"{b['followups']} follow-up{'s' if b['followups'] != 1 else ''}"))
    bits = [b["model"]] + ([b["variant"]] if b.get("variant") else [])
    sv = SERVING.get(b["slug"], {})
    kind = sv.get("kind", "")
    tag = {"local": f"{html.escape(sv.get('provider',''))} · .5",
           "cloud": html.escape(sv.get('provider',''))}.get(kind, "provider unrecorded")
    return f"""      <a class="gal-card" href="gallery/model-testing/{b['slug']}.html">
        <div class="gal-body">
          <div class="gal-t">{html.escape(b['title'])}</div>
          <div class="gal-m">{html.escape(' · '.join(bits))}</div>
          <div class="gal-chip {kind or 'unknown'}">{tag}</div>
          <div class="gal-d">{html.escape(b['blurb'])}</div>
          <div class="gal-m">{mt} &middot; {kb} KB &middot; {fol}</div>
          <div class="gal-go">prompt + build &#8594;</div>
        </div>
      </a>"""


def grid(items):
    return '<div class="gal-grid">\n' + "\n".join(card_html(b) for b in items) + '\n    </div>'


def harness_block(name, items):
    return f"""    <details class="gal-h" open>
      <summary><span class="gal-h-t">{html.escape(name)}</span><span class="gal-h-c">{len(items)} build{'s' if len(items) != 1 else ''}</span></summary>
      {grid(items)}
    </details>"""


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
        labels = {b.get("harness", "") for b in items}
        split = len([x for x in labels if x]) >= 2
        if split:
            order = []
            for b in items:
                if b["harness"] not in order:
                    order.append(b["harness"])
            body = "\n".join(harness_block(h, [b for b in items if b["harness"] == h]) for h in order)
        else:
            body = "    " + grid(items)
        sections.append(f"""  <details class="gal-sec-m" open>
    <summary><span class="gal-sec-n">{n:02d}</span><span class="gal-sec-t">{html.escape(g)}</span><span class="gal-sec-rule"></span><span class="gal-sec-c">{len(items)} build{'s' if len(items) != 1 else ''}</span></summary>
    <p class="gal-sec-s">{html.escape(GROUP_BLURB[g])}</p>
{body}
  </details>""")
    total = len(BUILDS)
    return HEAD.format(
        title="Model testing gallery — Eamon McKiernan",
        desc="One-shot browser demos written by AI models — local and cloud — organised by model, with the harness and serving config behind each build.",
        ogtitle="Model testing gallery — one-shot demos, grouped by model",
        style=STYLE) + f"""
  <div class="gal-top">
    <a class="gal-back" href="index.html">&#8592;&nbsp;Eamon McKiernan</a>
  </div>

  <h1 class="gal-h1">Model testing gallery</h1>
  <p class="gal-lede">{total} one-shot browser demos written by AI models, grouped by the model that wrote them. One prompt, one self-contained HTML file, no fixes — published as they came out, defects and all. Each build records the harness it ran under and where it was served: my own V100s for the local runs, a cloud plan for the rest.</p>
  <p class="gal-meta">{len([g for g in GROUP_ORDER if g in by_group])} models &middot; {total} builds &middot; prompts quoted verbatim</p>

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
