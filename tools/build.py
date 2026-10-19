#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assemble index.html from tools/site-data.json + the SVG builders.

The site is static: index.html is generated from the data file, so every word
on the page traces back to tools/site-data.json and nothing is hand-typed.

    python3 tools/build.py
"""
import json, html, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import svgs as p2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = json.load(open(os.path.join(HERE, "site-data.json"), encoding="utf-8"))
OUT = os.path.join(ROOT, "index.html")

e = html.escape


def raw(s):
    """Already-HTML content (project bullets) — pass through."""
    return s


# ------------------------------------------------------------------ helpers
def hicon(cls, size=None):
    return f'<i class="hgi-stroke {cls}" aria-hidden="true"></i>'


SECTIONS = [
    ("siteplan", "Site plan", "THE HOMELAB"),
    ("capability", "Capability", "EIGHT DISCIPLINES &#183; 60 TECHNOLOGIES"),
    ("experience", "Experience", "HELPDESK &#183; INFRASTRUCTURE"),
    ("impact", "Impact", "MEASURED, NOT CLAIMED"),
    ("measurements", "Measurements", "FIGURES TAKEN FROM THE REPOSITORIES"),
    ("projects", "Work", "NINE BUILDS &#183; 134 DOCUMENTED DECISIONS"),
    ("credentials", "Credentials", "CERTIFICATION &#183; EDUCATION"),
    ("contact", "Contact", "ISLE OF MAN &#183; REMOTE &amp; ON-SITE"),
]


def section_head(num, title, desc, anchor=""):
    return f'''<header class="shead rv">
      <span class="snum">{num}</span>
      <h2 id="{anchor}">{title}</h2>
      <span class="sdesc">{desc}</span>
    </header>'''


# ------------------------------------------------------------------ sections
def build_capability():
    rows = []
    for i, s in enumerate(D["skills"]):
        items = "".join(f"<li>{e(x)}</li>" for x in s["items"])
        rows.append(f'''<div class="sk rv d{(i % 3) + 1}">
        <h3>{e(s["name"])}</h3>
        <ul class="sk-list">{items}</ul>
      </div>''')
    return f'''<section class="sec" id="capability">
  <div class="wrap">
    {section_head("01", "Capability", "EIGHT DISCIPLINES &#183; 60 TECHNOLOGIES", "capability")}
    <div class="sched">
      {"".join(rows)}
    </div>
  </div>
</section>'''


def build_experience():
    """Scaled duration chart beside the role entries.
    The chart and the axis share one coordinate space so bars line up with dates."""
    T0, T1 = 2024.58, 2026.79          # Aug 2024 .. Oct 2026, in years
    span = T1 - T0

    def pos(y):
        return (y - T0) / span * 100

    jobs = [
        ("SynergyIT", "Junior Support Technician", 2024.58, 2026.0, False),
        ("Manx Technology Group", "IT Support Engineer", 2026.0, T1, True),
    ]
    rows = []
    for i, (co, title, y1, y2, live) in enumerate(jobs):
        left, width = pos(y1), pos(y2) - pos(y1)
        livecls = " live" if live else ""
        rows.append(f'''<div class="dur-job{livecls}">
        <div class="dur-head">
          <span class="dur-who">{e(co)}</span>
          <span class="dur-span">{e(D["jobs"][1 - i]["when"])}</span>
        </div>
        <div class="dur-bar"><i style="--l:{left:.2f}%;--w:{width:.2f}%"></i></div>
      </div>''')

    ticks = [(2024.58, "AUG '24"), (2025.0, "JAN '25"), (2025.5, "JUL '25"),
             (2026.0, "JAN '26"), (2026.5, "JUL '26")]
    tickhtml = "".join(
        f'<span class="dur-tick" style="left:{pos(y):.2f}%">{lab}</span>' for y, lab in ticks)

    entries = []
    for j in D["jobs"]:
        bullets = "".join(f"<li>{e(b)}</li>" for b in j["bullets"])
        entries.append(f'''<div class="exp-item rv">
      <div class="exp-when">{e(j["when"])}</div>
      <div class="exp-body">
        <h3 class="exp-co">{e(j["co"])}</h3>
        <div class="exp-role">{e(j["title"])}</div>
        <ul class="exp-list">{bullets}</ul>
      </div>
    </div>''')

    return f'''<section class="sec" id="experience">
  <div class="wrap">
    {section_head("02", "Experience", "HELPDESK &#183; INFRASTRUCTURE", "experience")}
    <div class="exp-layout">
      <div class="exp">
        {"".join(entries)}
      </div>
      <aside class="dur rv" aria-label="Employment timeline">
        <div class="dur-cap">TENURE</div>
        <div class="dur-ticks">{tickhtml}</div>
        <div class="dur-axis"></div>
        <div class="dur-now"><span>NOW</span></div>
        {"".join(rows)}
      </aside>
    </div>
  </div>
</section>'''


def build_impact():
    cells = []
    for i, s in enumerate(D["impact"]):
        cells.append(f'''<div class="meas-cell rv d{i+1}">
        <div class="meas-n tnum" data-count="{e(s['count'])}" data-prefix="{e(s['prefix'])}" data-suffix="{e(s['suffix'])}">{e(s['prefix'])}{e(s['count'])}{e(s['suffix'])}</div>
        <div class="meas-l">{e(s['label'])}</div>
        <div class="meas-s">{e(s['sub'])}</div>
      </div>''')
    return f'''<section class="sec sec--band" id="impact">
  <div class="wrap">
    {section_head("03", "Impact", "MEASURED, NOT CLAIMED", "impact")}
    <div class="meas">
      {"".join(cells)}
    </div>
  </div>
</section>'''


def build_measurements():
    """Charts built from figures already published on the site."""
    figs = [
        ("Prefill throughput by prompt depth", "PROJECT MAYA &#183; 262,144 CTX",
         p2.chart_prefill(),
         "Mean of three fresh-load runs per depth on the 313B IQ2_XXS quant, "
         "streamed KV cache, speculative drafting off."),
        ("Decode throughput before and after the engine bump", "STRATA v0.1.32 &#8594; v0.1.39",
         p2.chart_decode(),
         "Same model and config byte-for-byte. Decode gained 22&#8211;31% at every depth; "
         "prefill gained 23&#8211;26% from 60k up, peaking at 1,973 tok/s."),
        ("Strategy against equal-weight buy-and-hold", "TRADING BOT &#183; WALK-FORWARD",
         p2.chart_backtest(),
         "Rules committed to a written receipt before any price data was inspected. "
         "The higher gates only won by trading less, so the gate is an off-switch, not alpha."),
        ("Code-review findings, all remediated", "FFIOM &#183; AUGUST 2026",
         p2.chart_findings(),
         "34 findings from a structured audit of the whole codebase, run as parallel "
         "subagent reviews. Every one was remediated and verified."),
    ]
    cards = []
    for i, (t, s, svg, note) in enumerate(figs):
        wide = " fig-wide" if i == 3 else ""
        cards.append(f'''<div class="fig{wide} rv d{(i % 2) + 1}">
        <div class="fig-cap">
          <span class="fig-t">{t}</span>
          <span class="fig-s">{s}</span>
        </div>
        {svg}
        <p class="fig-note">{note}</p>
      </div>''')
    return f'''<section class="sec" id="measurements">
  <div class="wrap">
    {section_head("04", "Measurements", "FIGURES TAKEN FROM THE REPOSITORIES", "measurements")}
    <div class="mgrid">
      {"".join(cards)}
    </div>
  </div>
</section>'''


def build_projects():
    idx = []
    sheets = []
    for i, p in enumerate(D["projects"]):
        n = f"{i+1:02d}"
        idx.append(f'<a href="#proj-{i+1}"><b>{n}</b> {e(p["title"])}</a>')

        secs = []
        for s in p["sections"]:
            items = "".join(f"<li>{raw(x)}</li>" for x in s["items"])
            two = " two" if len(s["items"]) > 5 else ""
            secs.append(f'''<div class="spec">
          <div class="slabel">{e(s["label"])}</div>
          <ul class="spec-items{two}">{items}</ul>
        </div>''')

        tags = ""
        if p["tags"]:
            tags = ('<div class="ptags"><b>TAGS</b>' +
                    "<i>&#183;</i>".join(f"<span>{e(t)}</span>" for t in p["tags"]) + "</div>")

        sheets.append(f'''<details class="psheet rv" id="proj-{i+1}"{" open" if i == 0 else ""}>
      <summary>
        <span class="pnum">{n}</span>
        <span class="ptitle">{e(p["title"])}</span>
        <span class="pmeta">{e(p["meta"])}</span>
        <span class="px" aria-hidden="true"></span>
      </summary>
      <div class="pbody">
        <p class="pdesc">{raw(p["desc_html"])}</p>
        {"".join(secs)}
        {tags}
      </div>
    </details>''')

    return f'''<section class="sec" id="projects">
  <div class="wrap">
    {section_head("05", "Work", "NINE BUILDS &#183; 134 DOCUMENTED DECISIONS", "projects")}
    <div class="pindex rv">{"".join(idx)}</div>
    <div class="sheets">
      {"".join(sheets)}
    </div>
  </div>
</section>'''


def build_credentials():
    c = D["cert"]
    edu = []
    for b in D["edu"]:
        grades = "".join(
            f'''<div class="grade">
          <div class="gbox{' pass' if ' ' in g['grade'] else ''}">{e(g['grade'])}</div>
          <div class="grade-sub">{e(g['subject'])}</div>
        </div>''' for g in b["grades"])
        edu.append(f'''<div class="edu-block rv d2">
      <div class="edu-when">{e(b["when"])}</div>
      <h3>{e(b["title"])}</h3>
      <div class="edu-sub">{e(b["sub"])}</div>
      <div class="grades">{grades}</div>
    </div>''')

    return f'''<section class="sec" id="credentials">
  <div class="wrap">
    {section_head("06", "Credentials", "CERTIFICATION &#183; EDUCATION", "credentials")}

    <div class="cert rv">
      <div class="cert-badge">{c["badge"]}</div>
      <div>
        <h3>{e(c["name"])}</h3>
        <div class="cert-meta">{e(c["meta"])}</div>
      </div>
      <div class="yr">{e(c["year"])}</div>
    </div>

    <div class="edu">
      {"".join(edu)}
    </div>
  </div>
</section>'''


def build_contact():
    links = []
    for i, l in enumerate(D["contact"]):
        if l["tag"] == "a":
            tgt = ' target="_blank" rel="noopener"' if l["target"] else ""
            links.append(f'''<a href="{e(l["href"])}"{tgt}>
        <span class="cl-ico">{hicon(l["icon"])}</span>
        {e(l["label"])}
      </a>''')
        else:
            links.append(f'''<span>
        <span class="cl-ico">{hicon(l["icon"])}</span>
        {e(l["label"])}
      </span>''')

    return f'''<section class="sec sec--band" id="contact">
  <div class="wrap">
    {section_head("07", "Contact", "ISLE OF MAN &#183; REMOTE &amp; ON-SITE", "contact")}
    <div class="contact">
      <div>
        <p class="contact-lead">Open to <em>remote and on-site</em> work across Microsoft 365, virtualisation and self-hosted AI.</p>
        <p class="contact-note">
          <b>enquiries@eamonmckiernan.im</b><br>
          Based in the Isle of Man &#183; available for new work
        </p>
      </div>
      <div class="contact-list">
        {"".join(links)}
      </div>
    </div>
  </div>
</section>'''


# ------------------------------------------------------------------ hero
def build_hero():
    h = D["hero"]
    links = []
    for l in h["links"]:
        if l["href"].endswith("gallery.html"):
            continue
        tgt = ' target="_blank" rel="noopener"' if l["target"] else ""
        cls = "lk-mail" if l["href"].startswith("mailto:") else ""
        links.append(f'<a class="{cls}" href="{e(l["href"])}"{tgt}>{hicon(l["icon"])}{e(l["label"])}</a>')
    links.append('<a href="gallery.html">' + hicon("hgi-cube") + "Demo gallery</a>")

    ident = [
        ("Role", "IT Support Engineer"),
        ("Discipline", "Self-hosted AI infrastructure"),
        ("Base", "Isle of Man"),
        ("Availability", "Remote &amp; on-site"),
        ("AI hardware", "2&#215; Tesla V100 32 GB"),
        ("Cluster", "3-node Proxmox VE 9.2"),
    ]
    idrows = "".join(
        f'<div class="id-row"><dt>{k}</dt><dd>{v}</dd></div>' for k, v in ident)

    return f'''<header class="hero" id="top">
  <div class="wrap">
    <div class="hero-grid">
      <div class="hero-left">
        <h1 class="hero-name">
          <span class="ln" style="--l:0"><span>Eamon</span></span>
          <span class="ln" style="--l:1"><span>McKiernan</span></span>
        </h1>
        <p class="hero-role">{e(h["role"]).replace("&amp;#183;", "&#183;")}</p>
        <p class="hero-sum">{e(h["summary"])}</p>
        <p class="hero-status"><span class="pip"></span><span>Based in the <b>Isle of Man</b> &#183; open to remote and on-site work</span></p>
        <div class="hero-links">
          {"".join(links)}
        </div>
      </div>
      <div class="hero-right">
        <div class="ident">
          <div class="ident-cap">
            <span class="ident-t">Identification</span>
            <span class="ident-r">Rev A</span>
          </div>
          <dl class="ident-list">{idrows}</dl>
        </div>
      </div>
    </div>
  </div>
</header>'''


def build_siteplan():
    return f'''<section class="sec sec-plan" id="siteplan">
  <div class="wrap">
    {section_head("00", "Site plan", "THE HOMELAB, DRAWN TO SCALE OF WHAT IT IS", "siteplan")}
    <figure class="plan-figure rv">
      <div class="plan-scroll">
        {p2.site_plan()}
      </div>
      <p class="plan-scroll-hint" aria-hidden="true">SCROLL &#8594; for the full sheet</p>
      <figcaption class="plan-cap-note">
        <span class="pcn-l">Figure 00 &#183; Homelab site plan</span>
        <span class="pcn-r">Public and consumer traffic terminates at the OPNsense router, which
        separates it from the VLAN-segmented server subnet &#8212; three Proxmox nodes over Ceph
        replication, the local AI node, and the media and private-cloud host.</span>
      </figcaption>
    </figure>
  </div>
</section>'''


# ------------------------------------------------------------------ assemble
def build():
    parts = []
    parts.append(f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Eamon McKiernan — IT Support Engineer &#183; Self-Hosted AI Infrastructure</title>
<meta name="description" content="IT Support Engineer on the Isle of Man — Microsoft 365 support, self-hosted infrastructure and a local AI stack running on used hardware.">
<meta name="theme-color" content="#F4F1EA">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://use.hugeicons.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Instrument+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://use.hugeicons.com/font/icons.css">
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<header class="rail">
  <div class="rail-prog" id="prog"></div>
  <div class="rail-in">
    <a class="brand" href="#top">
      <span class="brand-mark"><span>EM</span></span>
      <span class="brand-txt">Eamon <i>McKiernan</i></span>
    </a>
    <nav class="rail-nav" aria-label="Sections">
      {"".join(f'<a href="#{a}">{t.upper()}</a>' for a, t, _ in SECTIONS)}
    </nav>
    <span class="rail-where">{hicon("hgi-location-01")}Isle of Man</span>
    <button class="rail-btn" id="menuBtn" aria-expanded="false" aria-controls="menu">{hicon("hgi-menu-01")}Menu</button>
  </div>
</header>

<div class="msheet" id="menu" hidden>
  <button class="msheet-close" id="menuClose">{hicon("hgi-cancel-01")}Close</button>
  <nav aria-label="Sections">
    {"".join(f'<a href="#{a}"><span>{i:02d}</span>{t}</a>' for i, (a, t, _) in enumerate(SECTIONS, 1))}
    <a href="gallery.html"><span>07</span>Demo gallery</a>
  </nav>
</div>
''')

    parts.append(build_hero())
    parts.append(build_siteplan())
    parts.append(build_capability())
    parts.append(build_experience())
    parts.append(build_impact())
    parts.append(build_measurements())
    parts.append(build_projects())
    parts.append(build_credentials())
    parts.append(build_contact())

    parts.append('''<footer class="foot">
  <div class="wrap foot-in">
    <div class="foot-l">&#169; 2026 Eamon McKiernan</div>
    <div class="foot-r">
      <a href="#top">Top</a>
      <a href="gallery.html">Demo gallery</a>
      <a href="https://github.com/EamonMcKiernan05" target="_blank" rel="noopener">GitHub</a>
    </div>
  </div>
</footer>

<script>
(function () {
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.documentElement.classList.add('js');

  // ---- scroll reveal (additive only; content visible if JS or IO fails)
  var reveals = Array.prototype.slice.call(document.querySelectorAll('.rv'));
  function showAll() { reveals.forEach(function (el) { el.classList.add('in'); }); }
  if (reduce || !('IntersectionObserver' in window)) {
    showAll();
  } else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { threshold: 0, rootMargin: '0px 0px -8% 0px' });
    reveals.forEach(function (el) { io.observe(el); });
    setTimeout(showAll, 4000);
  }

  // ---- count-up
  function fmt(n) { return n.toLocaleString('en-US'); }
  function run(el) {
    var target = parseFloat(el.dataset.count);
    var pre = el.dataset.prefix || '';
    var suf = el.dataset.suffix || '';
    if (isNaN(target)) { el.textContent = pre + suf; return; }
    if (reduce) { el.textContent = pre + fmt(target) + suf; return; }
    var dur = 1200, t0 = performance.now();
    function tick(t) {
      var p = Math.min(1, (t - t0) / dur);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = pre + fmt(Math.round(eased * target)) + suf;
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = pre + fmt(target) + suf;
    }
    requestAnimationFrame(tick);
  }
  var nums = Array.prototype.slice.call(document.querySelectorAll('.meas-n[data-count]'));
  if (reduce || !('IntersectionObserver' in window)) {
    nums.forEach(run);
  } else {
    var nio = new IntersectionObserver(function (es) {
      es.forEach(function (en) { if (en.isIntersecting) { run(en.target); nio.unobserve(en.target); } });
    }, { threshold: 0.5 });
    nums.forEach(function (n) { nio.observe(n); });
  }

  // ---- the site plan inks itself in when it scrolls into view
  var plan = document.querySelector('.plan-svg');
  if (plan && !reduce) {
    if ('IntersectionObserver' in window) {
      var pio = new IntersectionObserver(function (es) {
        es.forEach(function (en) {
          if (en.isIntersecting) { plan.classList.add('drawn'); pio.unobserve(en.target); }
        });
      }, { threshold: 0.15 });
      pio.observe(plan);
    } else {
      plan.classList.add('drawn');
    }
    // safety net: if the observer never fires, show the finished sheet
    setTimeout(function () { plan.classList.add('drawn'); }, 6000);
  } else if (plan) {
    plan.classList.add('drawn');
  }

  // ---- duration bars
  var bars = Array.prototype.slice.call(document.querySelectorAll('.dur-bar i'));
  function grow(el) { el.style.transform = 'scaleX(1)'; }
  if (reduce || !('IntersectionObserver' in window)) {
    bars.forEach(grow);
  } else {
    var bio = new IntersectionObserver(function (es) {
      es.forEach(function (en) { if (en.isIntersecting) { grow(en.target); bio.unobserve(en.target); } });
    }, { threshold: 0.4 });
    bars.forEach(function (b) { bio.observe(b); });
  }

  // ---- hero name rises out of its mask
  var heroName = document.querySelector('.hero-name');
  if (heroName) {
    requestAnimationFrame(function () { heroName.classList.add('lit'); });
  }

  // ---- scroll progress
  var prog = document.getElementById('prog');
  function onScroll() {
    var h = document.documentElement.scrollHeight - window.innerHeight;
    var p = h > 0 ? Math.min(1, Math.max(0, window.scrollY / h)) : 0;
    prog.style.transform = 'scaleX(' + p + ')';
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();

  // ---- section scroll-spy
  var links = Array.prototype.slice.call(document.querySelectorAll('.rail-nav a'));
  var map = {};
  links.forEach(function (a) {
    var id = a.getAttribute('href').slice(1);
    var el = document.getElementById(id);
    if (el) map[id] = a;
  });
  if ('IntersectionObserver' in window) {
    var sio = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        var a = map[en.target.id];
        if (!a) return;
        if (en.isIntersecting) {
          links.forEach(function (l) { l.classList.remove('on'); });
          a.classList.add('on');
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    Object.keys(map).forEach(function (id) { sio.observe(document.getElementById(id)); });
  }

  // ---- mobile menu
  var btn = document.getElementById('menuBtn');
  var sheet = document.getElementById('menu');
  function setMenu(open) {
    sheet.hidden = !open;
    if (open) {
      sheet.classList.add('open');
      requestAnimationFrame(function () { sheet.classList.add('open'); });
    } else {
      sheet.classList.remove('open');
    }
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    document.body.style.overflow = open ? 'hidden' : '';
  }
  btn.addEventListener('click', function () { setMenu(sheet.hidden); });
  document.getElementById('menuClose').addEventListener('click', function () { setMenu(false); });
  sheet.addEventListener('click', function (ev) {
    if (ev.target.tagName === 'A') setMenu(false);
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape' && !sheet.hidden) setMenu(false);
  });

  // ---- details: only one project open at a time
  var sheets = Array.prototype.slice.call(document.querySelectorAll('.psheet'));
  sheets.forEach(function (d) {
    d.addEventListener('toggle', function () {
      if (!d.open) return;
      sheets.forEach(function (o) { if (o !== d) o.open = false; });
    });
  });
})();
</script>
</body>
</html>
''')

    out = "\n".join(parts)
    open(OUT, "w", encoding="utf-8").write(out)
    print("wrote", OUT, len(out), "bytes")


if __name__ == "__main__":
    build()
