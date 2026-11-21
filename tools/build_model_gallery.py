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
def thumb_ver(b):
    """mtime+size stamp so a re-captured thumbnail gets a new URL (edge caches the old one for 4h)."""
    f = ROOT / "demos" / "thumbs" / "model-testing" / f"{b['slug']}.jpg"
    st = f.stat()
    return f"?v={int(st.st_mtime)}-{st.st_size}"


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
    dict(rel="DeepSeek-V4.1-Flash-1017/THE-CASTLE.html", slug="deepseek-v41-castle",
         model="DeepSeek V4.1 Flash", group="DeepSeek V4.1 Flash", variant="",
         title="The Castle", prompt="castle", session="23f01a1f", followups=0,
         blurb="The castle brief, one shot, the largest single render in the gallery."),
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
    dict(rel='Qwen 4 Max/basalt-organ.html', slug='qwen-4-max-basalt-organ', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='The Basalt Organ', prompt='the-basalt-organ', session='23275136-cd04-4d51-836e-8a780bceb938', followups=0, date='17 Nov 2026', build_min=65, kb=51, blurb='The Basalt Organ, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/glass-tide.html', slug='qwen-4-max-glass-tide', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='The Glass Tide', prompt='the-glass-tide', session='57e3c117-2a9b-42e7-aed1-a4baf925a3c0', followups=0, date='17 Nov 2026', build_min=30, kb=52, blurb='The Glass Tide, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/mangrove-after-dark.html', slug='qwen-4-max-mangrove-after-dark', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='Mangrove After Dark', prompt='mangrove-after-dark', session='5210f296-4d6f-492f-a23c-88bbc488371d', followups=0, date='17 Nov 2026', build_min=33, kb=51, blurb='Mangrove After Dark, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/medieval-village.html', slug='qwen-4-max-medieval-village', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='Medieval Village', prompt='medieval-village', session='5d32af58-5d64-4397-982e-0882db898256', followups=0, date='16 Nov 2026', build_min=44, kb=62, blurb='Medieval Village, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/rain-cathedral.html', slug='qwen-4-max-rain-cathedral', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='The Rain Cathedral', prompt='the-rain-cathedral', session='8cd32292-2398-4f87-9170-8c785a7404b0', followups=0, date='17 Nov 2026', build_min=28, kb=48, blurb='The Rain Cathedral, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/salt-mirror.html', slug='qwen-4-max-salt-mirror', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='Salt Mirror', prompt='salt-mirror', session='5dbf1619-51eb-4f67-8500-088e62b6bd87', followups=0, date='17 Nov 2026', build_min=32, kb=54, blurb='Salt Mirror, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/the-last-light.html', slug='qwen-4-max-the-last-light', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='The Last Light', prompt='the-last-light', session='89f4c3c2-ef41-402e-bbc3-cdca692ce125', followups=0, date='16 Nov 2026', build_min=170, kb=688, blurb='The Last Light, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/the-pagoda.html', slug='qwen-4-max-the-pagoda', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='The Pagoda', prompt='the-pagoda', session='ce6993ad-b524-4c01-b99f-197fdbab638b', followups=0, date='16 Nov 2026', build_min=57, kb=671, blurb='The Pagoda, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/torchlight-depths.html', slug='qwen-4-max-torchlight-depths', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness', variant='', title='Torchlight Depths', prompt='torchlight-depths', session='2cf3f37e-0669-4d8a-ab51-feadffeecf22', followups=0, date='16 Nov 2026', build_min=60, kb=720, blurb='Torchlight Depths, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Hy4 Flash/MANGROVE_AFTER_DARK.html', slug='hy4-flash-mangrove-after-dark', model='Hy4 Flash', group='Hy4 Flash', harness='DeepSeek Harness', variant='', title='Mangrove After Dark', prompt='mangrove-after-dark', session='8b5a27e6-7344-4775-a41d-e85b5d1d61f2', followups=0, date='17 Nov 2026', build_min=14, kb=54, blurb='Mangrove After Dark, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Hy4 Flash/SALT_MIRROR.html', slug='hy4-flash-salt-mirror', model='Hy4 Flash', group='Hy4 Flash', harness='DeepSeek Harness', variant='', title='Salt Mirror', prompt='salt-mirror', session='8f2f7717-d4a8-4db9-a10a-0f2bd2aa2bf1', followups=0, date='17 Nov 2026', build_min=22, kb=40, blurb='Salt Mirror, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Hy4 Flash/THE_LAST_LIGHT.html', slug='hy4-flash-the-last-light', model='Hy4 Flash', group='Hy4 Flash', harness='DeepSeek Harness', variant='', title='The Last Light', prompt='the-last-light', session='38f1045f-fb02-4321-985c-25a6592bec53', followups=0, date='16 Nov 2026', build_min=30, kb=656, blurb='The Last Light, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Hy4 Flash/medieval-village.html', slug='hy4-flash-medieval-village', model='Hy4 Flash', group='Hy4 Flash', harness='DeepSeek Harness', variant='', title='Medieval Village', prompt='medieval-village', session='200a3603-c2ec-47de-a731-09849563f326', followups=0, date='16 Nov 2026', build_min=13, kb=48, blurb='Medieval Village, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Hy4 Flash/pagoda.html', slug='hy4-flash-pagoda', model='Hy4 Flash', group='Hy4 Flash', harness='DeepSeek Harness', variant='', title='The Pagoda', prompt='the-pagoda', session='7b7e1752-5614-4e0a-8710-7ea429baa3d9', followups=2, date='16 Nov 2026', build_min=42, kb=667, blurb='The Pagoda, delivered in one prompt with 2 follow-ups — the session iterated on the first pass.'),
    dict(rel='Qwen3.8 Flash-Next/basalt-organ.html', slug='qwen3-8-flash-next-basalt-organ', model='Qwen3.8 Flash-Next', group='Qwen3.8 Flash-Next', harness='DeepSeek Harness', variant='', title='The Basalt Organ', prompt='the-basalt-organ', session='83d376cc-f64b-40f7-92be-7234534ae8da', followups=0, date='17 Nov 2026', build_min=38, kb=46, blurb='The Basalt Organ, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen3.8 Flash-Next/mangrove-after-dark.html', slug='qwen3-8-flash-next-mangrove-after-dark', model='Qwen3.8 Flash-Next', group='Qwen3.8 Flash-Next', harness='DeepSeek Harness', variant='', title='Mangrove After Dark', prompt='mangrove-after-dark', session='37460fcb-1449-4703-b8b7-eff2d9e11a69', followups=0, date='17 Nov 2026', build_min=39, kb=55, blurb='Mangrove After Dark, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen3.8 Flash-Next/rain_cathedral.html', slug='qwen3-8-flash-next-rain-cathedral', model='Qwen3.8 Flash-Next', group='Qwen3.8 Flash-Next', harness='DeepSeek Harness', variant='', title='The Rain Cathedral', prompt='the-rain-cathedral', session='5cf956d3-cde0-4186-9497-090bafed2bf9', followups=0, date='17 Nov 2026', build_min=36, kb=80, blurb='The Rain Cathedral, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen3.8 Flash-Next/sky_temple.html', slug='qwen3-8-flash-next-sky-temple', model='Qwen3.8 Flash-Next', group='Qwen3.8 Flash-Next', harness='DeepSeek Harness', variant='', title='The Pagoda', prompt='the-pagoda', session='7015be94-ef86-4510-b1aa-7075da64da01', followups=0, date='17 Nov 2026', build_min=33, kb=79, blurb='The Pagoda, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/cloudfall-pass.html', slug='qwen-4-max-cloudfall-pass', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness',
         variant='', title='Cloudfall Pass', prompt='cloudfall-pass', session='1cddf868-b51e-40c3-bf73-8eb1da5cd482',
         followups=0, date='18 Nov 2026', build_min=43, kb=49,
         blurb='Cloudfall Pass, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='Qwen 4 Max/glacial-heart.html', slug='qwen-4-max-glacial-heart', model='Qwen 4 Max', group='Qwen 4 Max', harness='DeepSeek Harness',
         variant='', title='Glacial Heart', prompt='glacial-heart', session='ac3bd038-6ce5-4b49-81c1-fba7b7c6a5df',
         followups=0, date='18 Nov 2026', build_min=42, kb=44,
         blurb='Glacial Heart, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='DeepSeek-V4.1-Flash-1017/THE-CROFT-AT-THE-WRACK-LINE.html', slug='deepseek-v41-croft-at-the-wrack-line', model='DeepSeek V4.1 Flash', group='DeepSeek V4.1 Flash', harness='DeepSeek Harness',
         variant='', title='The Croft at the Wrack Line', prompt='croft-at-the-wrack-line', session='02a39f80-6cf1-432a-abd1-e4b513cdcbbf',
         followups=8, date='19 Nov 2026', build_min=167, kb=912,
         blurb='The Croft at the Wrack Line, one prompt, 8 follow-ups.'),
    dict(rel='DeepSeek-V4.1-Flash-1017/the-beavers-spare-channel.html', slug='deepseek-v41-the-beavers-spare-channel', model='DeepSeek V4.1 Flash', group='DeepSeek V4.1 Flash', harness='DeepSeek Harness',
         variant='', title='The Beaver\'s Spare Channel', prompt='the-beavers-spare-channel', session='21faf606-9969-4f9a-95f8-c14588cd2156',
         followups=0, date='19 Nov 2026', build_min=82, kb=870,
         blurb='The Beaver\'s Spare Channel, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='DeepSeek-V4.1-Flash-1017/swallowtail-hayfield.html', slug='deepseek-v41-swallowtail-hayfield', model='DeepSeek V4.1 Flash', group='DeepSeek V4.1 Flash', harness='DeepSeek Harness',
         variant='', title='The Swallowtail Hayfield', prompt='swallowtail-hayfield', session='9d3990f7-ac51-4c9b-9931-59febbe6ee76',
         followups=0, date='19 Nov 2026', build_min=58, kb=803,
         blurb='The Swallowtail Hayfield, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='DeepSeek-V4.1-Flash-1017/kettle-lake.html', slug='deepseek-v41-kettle-lake', model='DeepSeek V4.1 Flash', group='DeepSeek V4.1 Flash', harness='DeepSeek Harness',
         variant='', title='The Two Shores of Kettle Lake', prompt='the-two-shores-of-kettle-lake', session='d05b0995-becb-4456-807f-eb52e3873223',
         followups=1, date='19 Nov 2026', build_min=1128, kb=856,
         blurb='The Two Shores of Kettle Lake, one prompt and one follow-up — the follow-up took the cutaway out and closed the block.'),
    dict(rel='DeepSeek-V4.1-Flash-1017/the-basalt-organ.html', slug='deepseek-v41-the-basalt-organ', model='DeepSeek V4.1 Flash', group='DeepSeek V4.1 Flash', harness='DeepSeek Harness',
         variant='', title='The Basalt Organ', prompt='the-basalt-organ', session='6ba07012-8646-467b-b862-d7007ff04273',
         followups=0, date='19 Nov 2026', build_min=53, kb=147,
         blurb='The Basalt Organ, one prompt, no follow-ups — built in a single pass.'),
    dict(rel='DeepSeek-V4.1-Flash-1017/the-rain-cathedral.html', slug='deepseek-v41-the-rain-cathedral', model='DeepSeek V4.1 Flash', group='DeepSeek V4.1 Flash', harness='DeepSeek Harness',
         variant='', title='The Rain Cathedral', prompt='the-rain-cathedral', session='3af62085-cd34-45d7-8a8a-8962b0a07208',
         followups=2, date='19 Nov 2026', build_min=1057, kb=209,
         blurb='The Rain Cathedral, one prompt and two follow-ups — the last two reshaped the hall and the rain.'),
    dict(rel='DeepSeek-V4.1-Flash-1017/salt-mirror.html', slug='deepseek-v41-salt-mirror', model='DeepSeek V4.1 Flash', group='DeepSeek V4.1 Flash', harness='DeepSeek Harness',
         variant='', title='Salt Mirror', prompt='salt-mirror', session='99afd5ae-9d40-4418-bf35-c939ef253dfc',
         followups=0, date='19 Nov 2026', build_min=57, kb=170,
         blurb='Salt Mirror, one prompt, no follow-ups — built in a single pass.'),
]

GROUP_ORDER = ["Qwen 4 Max", "Hy4 Flash", "Qwen3.8 Flash-Next", "Qwen3.8-27B", "Qwen 4 Preview", "DeepSeek V4.1 Flash", "HY4", "LongCat 2.5"]

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
STATS = json.load(open(DOCS / "model-testing-build-stats.json"))


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
.wrap{max-width:1200px;margin:0 auto;padding:0 32px}

/* top + headings */
.gal-top{padding:34px 0 0}
.gal-back{font-family:var(--mono);font-size:12px;letter-spacing:0;text-transform:none;color:var(--dim);border:0}
.gal-back:hover{color:var(--accent)}
.gal-h1{font-family:var(--display);font-weight:600;font-size:clamp(36px,6.2vw,58px);line-height:1.02;letter-spacing:.005em;margin:30px 0 0;color:var(--accent);max-width:26ch}
.gal-lede{font-size:15px;line-height:1.6;color:var(--dim);margin-top:14px;max-width:68ch}
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
.gal-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:18px}
.gal-card{display:flex;flex-direction:column;min-width:0;background:transparent;border:1px solid var(--line);color:inherit;transition:border-color .18s ease}
.gal-card:hover{border-color:var(--accent)}
.gal-card:focus-visible{border-color:var(--accent);outline:1px solid var(--accent);outline-offset:2px}
.gal-thumbwrap{display:block;aspect-ratio:4/3;overflow:hidden;border-bottom:1px solid var(--line);background:#0c0b08}
.gal-thumbwrap img{display:block;width:100%;height:100%;object-fit:cover;filter:saturate(.96) brightness(.94);transition:filter .25s var(--ease)}
.gal-card:hover .gal-thumbwrap img{filter:saturate(1.04) brightness(1)}
.gal-thumbwrap.empty{background:#12100c}
.gal-body{padding:14px 16px 16px;display:flex;flex-direction:column;gap:6px;flex:1;min-width:0}
.gal-t{font-family:var(--display);font-size:19px;font-weight:600;line-height:1.15;letter-spacing:.005em;color:var(--ink)}
.gal-m{font-family:var(--mono);font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);margin-top:2px}
.gal-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px 24px;margin-top:22px;padding:16px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.gal-stat{display:flex;flex-direction:column;gap:5px;min-width:0}
.gal-stat-k{font-family:var(--mono);font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--quiet)}
.gal-stat-v{font-family:var(--mono);font-size:12.5px;letter-spacing:.02em;color:var(--ink);white-space:nowrap}
.gal-time{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--dim)}
.gal-go{font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;color:var(--accent);margin-top:auto;padding-top:12px;transition:transform .2s var(--ease)}
.gal-card:hover .gal-go{transform:translateX(3px)}

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
.gal-chip{align-self:flex-start;display:inline-block;font-family:var(--mono);font-size:9.5px;letter-spacing:.13em;text-transform:uppercase;padding:3px 8px;border:1px solid var(--line-strong);color:var(--dim);margin-top:2px}
.gal-chip.local{color:var(--accent);border-color:rgba(216,167,60,.45)}
.gal-chip.cloud{color:var(--quiet)}
.gal-chip.unknown{color:var(--quiet);border-style:dashed}
.gal-hero{margin:38px 0 6px;border:1px solid var(--line);background:#0c0b08}
.gal-hero img{display:block;width:100%;height:auto}
.gal-hero figcaption{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-dim);padding:11px 16px;border-top:1px solid var(--line)}
.gal-dl{display:grid;grid-template-columns:170px 1fr;column-gap:0;margin-top:24px;border-top:1px solid var(--line)}
.gal-dl dt{font-family:var(--mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--quiet);padding:15px 18px 15px 0;border-bottom:1px solid var(--line)}
.gal-dl dd{font-size:14px;color:var(--dim);padding:15px 0;border-bottom:1px solid var(--line);line-height:1.62}

/* footer */
footer{border-top:1px solid var(--line);margin:84px 0 0;padding:26px 0 60px;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}
.gal-f1,.gal-f2{font-family:var(--mono);font-size:11px;letter-spacing:.06em;color:var(--quiet)}
.gal-f2 a{color:var(--quiet);border-bottom-color:var(--line-strong)}
.gal-f2 a:hover{color:var(--accent)}

@media(max-width:980px){ .gal-grid{grid-template-columns:repeat(2,minmax(0,1fr))} }
@media(max-width:640px){ .gal-grid{grid-template-columns:1fr} }
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
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon-32x32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
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
    thumb = ROOT / "demos" / "thumbs" / "model-testing" / f"{b['slug']}.jpg"
    hero = ""
    if thumb.exists() and thumb.stat().st_size > 15000:
        hero = (f'<figure class="gal-hero"><img src="../../demos/thumbs/model-testing/{b["slug"]}.jpg{thumb_ver(b)}" '
                f'alt="{html.escape(b["title"])} — {html.escape(b["model"])}, running" width="1280" height="800">'
                f'<figcaption>{html.escape(b["model"])} &middot; {html.escape(mt)} &middot; preview</figcaption></figure>')
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
  {stats_block(b)}
  {note}
  {hero}

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


def buildtime(b):
    m = b.get("build_min")
    if not m:
        return ""
    label = f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m} min"
    return f'<div class="gal-time">built in {label}</div>'


def stat_label(m):
    if m is None:
        return "—"
    return f"{m // 60} h {m % 60:02d} m" if m >= 60 else f"{m} min"


def stats_block(b):
    s = STATS.get(b["slug"])
    if not s:
        return ""
    cells = [
        ("goal sent", s["start"]),
        ("build finished", s["finish"]),
        ("goal &rarr; build", stat_label(s["minutes"])),
    ]
    if s.get("first_pass") is not None and s["first_pass"] != s["minutes"]:
        cells.append(("first pass", stat_label(s["first_pass"])))
    cells.append(("follow-ups", str(s["followups"])))
    cells.append(("model steps", str(s["steps"])))
    cells.append(("tool calls", str(s["tools"])))
    rows = "".join(f'<div class="gal-stat"><span class="gal-stat-k">{k}</span>'
                   f'<span class="gal-stat-v">{v}</span></div>' for k, v in cells)
    return f'<div class="gal-stats">{rows}</div>'


def card_html(b):
    sv = SERVING.get(b["slug"], {})
    kind = sv.get("kind", "")
    tag = {"local": f"{html.escape(sv.get('provider',''))} · .5",
           "cloud": html.escape(sv.get('provider',''))}.get(kind, "provider unrecorded")
    thumb = ROOT / "demos" / "thumbs" / "model-testing" / f"{b['slug']}.jpg"
    img = (f'<span class="gal-thumbwrap"><img src="demos/thumbs/model-testing/{b["slug"]}.jpg{thumb_ver(b)}" '
           f'alt="{html.escape(b["title"])} — {html.escape(b["model"])}" loading="lazy"></span>'
           if thumb.exists() and thumb.stat().st_size > 15000 else
           '<span class="gal-thumbwrap empty" aria-hidden="true"></span>')
    return f"""      <a class="gal-card" href="gallery/model-testing/{b['slug']}.html">
        {img}
        <div class="gal-body">
          <div class="gal-t">{html.escape(b['title'])}</div>
          <div class="gal-m">{html.escape(b['model'])}</div>
          <div class="gal-chip {kind or 'unknown'}">{tag}</div>
          {buildtime(b)}
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
  <p class="gal-lede">{total} browser demos written by AI models, grouped by the model that wrote them. Most are one prompt and one self-contained HTML file; a few ran as a short session with follow-ups. Published as they came out — defects and all. Every build records the harness it ran under and what served it: my own V100s, or a cloud plan.</p>

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

