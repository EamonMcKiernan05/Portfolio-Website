#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
"""SVG builders: the homelab site plan + real-data charts."""

INK = "#1A1917"
RULE = "#CFC9BB"
RULE2 = "#B3AC9B"
RULE3 = "#DDD8CB"
DIM = "#6E6B5F"
ACC = "#B23A1C"

MONO = "'IBM Plex Mono',ui-monospace,monospace"
SANS = "'Instrument Sans',system-ui,sans-serif"


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- site plan
def site_plan():
    """Homelab site plan, drawn to drafting conventions.
    Geometry is laid out on explicit channels so no label ever crosses a box."""
    W, H = 1080, 700
    o = []
    a = o.append
    M = "'IBM Plex Mono',ui-monospace,monospace"
    CH = 5.9  # mono advance per char at 8.5px + letter-spacing

    # Draw-on ordering. Three counters so the sheet stages cleanly:
    # the ink lines draw first, then the structure boxes, then the annotation.
    _i = {"p": 0, "b": 0, "t": 0}

    def ip():
        _i["p"] += 1
        return _i["p"]

    def ib():
        _i["b"] += 1
        return _i["b"]

    def it():
        _i["t"] += 1
        return _i["t"]

    def rect(cls, x, y, w, h, rx=0, extra=""):
        r = f'rx="{rx}" ' if rx else ""
        return (f'<rect class="{cls}" style="--i:{ib()}" {r}x="{x}" y="{y}" '
                f'width="{w}" height="{h}" {extra}/>')

    a(f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="planTitle planDesc" '
      f'class="plan-svg" xmlns="http://www.w3.org/2000/svg">')
    a('<title id="planTitle">Homelab site plan</title>')
    a('<desc id="planDesc">Schematic plan of the homelab. Public and consumer traffic '
      'reaches an OPNsense router, which separates it from a VLAN-segmented server subnet: '
      'a three-node Proxmox cluster with Ceph replication and scheduled backups, a local AI '
      'node holding two Tesla V100 cards, and a media and private-cloud host on TrueNAS. '
      'A Cloudflare tunnel reaches the game server inside the Proxmox cluster.</desc>')

    a('<defs>')
    a('<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
      '<line x1="0" y1="0" x2="0" y2="7" stroke="%s" stroke-width="1"/></pattern>' % RULE)
    a('<marker id="arw" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
      '<path d="M0 0 L10 5 L0 10 z" fill="%s"/></marker>' % RULE2)
    a('</defs>')

    # ---------------------------------------------------------------- frame
    a(rect("pl-frame", 16, 16, W - 32, H - 32))
    for cx, cy, sx, sy in ((16, 16, 1, 1), (W-16, 16, -1, 1), (16, H-16, 1, -1), (W-16, H-16, -1, -1)):
        a(f'<path class="pl-ln2" pathLength="1" style="--i:{ip()}" '
          f'd="M{cx} {cy+18*sy} L{cx} {cy} L{cx+18*sx} {cy}"/>')

    # ---------------------------------------------------------------- header
    a('<text class="pl-tb" x="46" y="48">EAMON McKIERNAN</text>')
    a('<text class="pl-t" x="46" y="64">HOMELAB SITE PLAN &#183; ISLE OF MAN</text>')
    a(f'<line class="pl-ln2" pathLength="1" style="--i:{ip()}" x1="46" y1="76" x2="{W-46}" y2="76"/>')
    a(f'<text class="pl-t" x="{W-46}" y="48" text-anchor="end">SHEET 00 &#183; REV A &#183; 2026</text>')
    a(f'<text class="pl-t" x="{W-46}" y="64" text-anchor="end">NOT TO SCALE</text>')

    # ---------------------------------------------------------------- zones
    ZY, ZH = 116, 372
    ZB = ZY + ZH                      # 488
    PX1, PX2 = 46, 250                # PUBLIC
    EX1, EX2 = 274, 480               # EDGE
    SX1, SX2 = 504, 1034              # SERVER SUBNET

    a(rect("pl-zone", PX1, ZY, PX2 - PX1, ZH))
    a(f'<text class="pl-zl" x="76" y="{ZY+24}">PUBLIC</text>')
    a(f'<text class="pl-zs" x="76" y="{ZY+38}">CONSUMER + INTERNET</text>')

    a(rect("pl-zone", EX1, ZY, EX2 - EX1, ZH))
    a(f'<text class="pl-zl" x="{EX1+14}" y="{ZY+24}">EDGE</text>')
    a(f'<text class="pl-zs" x="{EX1+14}" y="{ZY+38}">ROUTER + NETWORK</text>')

    a(rect("pl-zone2", SX1, ZY, SX2 - SX1, ZH))
    a(f'<text class="pl-zl" x="{SX1+16}" y="{ZY+22}" fill="{ACC}">SERVER SUBNET</text>')
    a(f'<text class="pl-zs" x="{SX1+16}" y="{ZY+36}">ISOLATED &#183; VLAN-SEGREGATED &#183; 3 NODES</text>')

    # ---------------------------------------------------------------- PUBLIC bay
    a(rect("pl-box2", 76, 150, 160, 52, 2))
    a('<text class="pl-t9" x="88" y="172">CONSUMER DEVICES</text>')
    a('<text class="pl-t" x="88" y="188">LAPTOPS &#183; PHONES &#183; TV</text>')
    a(rect("pl-box2", 76, 218, 160, 52, 2))
    a('<text class="pl-t9" x="88" y="240">PUBLIC INTERNET</text>')
    a('<text class="pl-t" x="88" y="256">CLOUDFLARE TUNNEL</text>')
    a(f'<text class="pl-zs" x="60" y="296">INBOUND</text>')
    a(f'<text class="pl-t" x="60" y="310">FFIOM.COM</text>')
    a(f'<text class="pl-t" x="60" y="324">APPS &#183; DOWNLOADS</text>')

    # ---------------------------------------------------------------- EDGE bay
    a(rect("pl-box", 288, 150, 178, 72, 2))
    a('<text class="pl-t9" x="300" y="172">OPNSENSE</text>')
    a('<text class="pl-t" x="300" y="188">HP 280 G2 SFF</text>')
    a('<text class="pl-t" x="300" y="202">INTEL i350 NIC</text>')
    a('<text class="pl-t" x="300" y="216">IDS / IPS</text>')
    for i, (nm, sub) in enumerate([("PI-HOLE", "DNS FILTERING"), ("TAILSCALE", "VPN &#183; ZERO TRUST"),
                                   ("MANAGED SWITCH", "VLAN TAGGING")]):
        yy = 238 + i * 50
        a(rect("pl-box2", 288, yy, 178, 38, 2))
        a(f'<text class="pl-t9" x="300" y="{yy+16}">{nm}</text>')
        a(f'<text class="pl-t" x="300" y="{yy+30}">{sub}</text>')

    # ---------------------------------------------------------------- server bays
    BY1, BY2 = 176, 326               # upper row
    CY1, CY2 = 342, 478               # lower row
    LX1, LX2 = 522, 776               # left column
    RX1, RX2 = 796, 1014              # right column
    CH_L, CH_R = 512, 786             # vertical channels
    BUS_Y, LINK_Y = 166, 452

    # -- PROXMOX
    a(rect("pl-box2", LX1, BY1, LX2 - LX1, BY2 - BY1, 2))
    a(f'<text class="pl-th2" x="{LX1+12}" y="{BY1+22}">PROXMOX VE 9.2</text>')
    a(f'<text class="pl-t" x="{LX1+12}" y="{BY1+36}">3-NODE HA CLUSTER</text>')
    for i, (n1, n2) in enumerate([("NODE 01", "DELL 3050"), ("NODE 02", "HP PRODESK"),
                                  ("NODE 03", "HP ELITEDESK")]):
        yy = BY1 + 46 + i * 30
        a(rect("pl-box", LX1 + 12, yy, LX2 - LX1 - 24, 24, 2))
        a(f'<text class="pl-t9" x="{LX1+24}" y="{yy+16}">{n1}</text>')
        a(f'<text class="pl-t" x="{LX2-24}" y="{yy+16}" text-anchor="end">{n2}</text>')
    a(f'<text class="pl-t" x="{LX1+12}" y="{BY2-10}">HA FAILOVER &#183; CLOUD INIT</text>')

    # -- LOCAL AI
    a(rect("pl-box", RX1, BY1, RX2 - RX1, BY2 - BY1, 2))
    a(f'<text class="pl-th2" x="{RX1+12}" y="{BY1+22}">LOCAL AI</text>')
    a(f'<text class="pl-t" x="{RX1+12}" y="{BY1+36}">INFERENCE NODE</text>')
    a(rect("pl-hatch", RX1 + 12, BY1 + 46, RX2 - RX1 - 24, 26, 2))
    a(f'<text class="pl-t9" x="{RX1+22}" y="{BY1+63}">2&#215; TESLA V100 32 GB</text>')
    for i, t in enumerate(["Xeon E5-2680 v4", "CUDA 12.9 &#183; sm_70", "llama.cpp &#183; Strata",
                           "HERMES AGENT &#183; DISCORD"]):
        a(f'<text class="pl-t" x="{RX1+12}" y="{BY1+90+i*13}">{t}</text>')
    a(f'<text class="pl-tc" x="{RX1+12}" y="{BY2-8}">262,144 CTX</text>')

    # -- STORAGE
    a(rect("pl-box2", LX1, CY1, LX2 - LX1, CY2 - CY1, 2))
    a(f'<text class="pl-th2" x="{LX1+12}" y="{CY1+22}">STORAGE + OBSERVABILITY</text>')
    for i, (n1, n2) in enumerate([("CEPH SQUID 19.2.5", "REPLICATED POOLS"),
                                  ("PROXMOX BACKUP SERVER", "SCHEDULED SNAPSHOTS"),
                                  ("24 MONITORS", "LIBRENMS &#183; UPTIME KUMA")]):
        yy = CY1 + 46 + i * 30
        a(f'<text class="pl-t9" x="{LX1+12}" y="{yy}">{n1}</text>')
        a(f'<text class="pl-t" x="{LX1+12}" y="{yy+13}">{n2}</text>')

    # -- MEDIA
    a(rect("pl-box2", RX1, CY1, RX2 - RX1, CY2 - CY1, 2))
    a(f'<text class="pl-th2" x="{RX1+12}" y="{CY1+22}">MEDIA + PRIVATE CLOUD</text>')
    for i, (n1, n2) in enumerate([("TRUENAS ZFS", "REDUNDANT STORAGE"),
                                  ("JELLYFIN &#183; SONARR &#183; RADARR", "GTX 1650 NVENC"),
                                  ("NEXTCLOUD 35", "NGINX PROXY MANAGER")]):
        yy = CY1 + 46 + i * 28
        a(f'<text class="pl-t9" x="{RX1+12}" y="{yy}">{n1}</text>')
        a(f'<text class="pl-t" x="{RX1+12}" y="{yy+13}">{n2}</text>')

    # ---------------------------------------------------------------- bus + stubs
    # bus
    a(f'<path class="pl-ln" d="M{CH_L} {BUS_Y} L1020 {BUS_Y}"/>')
    # left channel spine: bus -> proxmox, storage, and the inbound link
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{CH_L} {BUS_Y} L{CH_L} {LINK_Y}"/>')
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{CH_L} 250 L{LX1} 250"/>')
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{CH_L} 410 L{LX1} 410"/>')
    # right channel spine
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{CH_R} {BUS_Y} L{CH_R} 410"/>')
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{CH_R} 250 L{RX1} 250"/>')
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{CH_R} 410 L{RX1} 410"/>')
    # junction dots
    for cx, cy in ((CH_L, BUS_Y), (CH_R, BUS_Y), (CH_L, 250), (CH_L, 410),
                   (CH_R, 250), (CH_R, 410)):
        a(f'<circle cx="{cx}" cy="{cy}" r="2.8" fill="{INK}"/>')

    # public -> edge -> server
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{PX2} {LINK_Y} L{EX1} {LINK_Y}"/>')
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{EX2} {LINK_Y} L{SX1} {LINK_Y}"/>')
    a(f'<path class="pl-ln" pathLength="1" style="--i:{ip()}" d="M{SX1} {LINK_Y} L{CH_L} {LINK_Y}"/>')
    a(f'<circle cx="{PX2}" cy="{LINK_Y}" r="2.8" fill="{INK}"/>')
    a(f'<circle cx="{EX1}" cy="{LINK_Y}" r="2.8" fill="{INK}"/>')
    a(f'<circle cx="{SX1}" cy="{LINK_Y}" r="3" fill="{ACC}"/>')
    # firewall gate marker on the edge->server hop
    a(f'<line class="pl-ln3" pathLength="1" style="--i:{ip()}" x1="492" y1="{LINK_Y-9}" x2="492" y2="{LINK_Y+9}"/>')

    # cloudflare tunnel: public internet -> proxmox bay, routed over the top
    a(f'<path class="pl-tun" style="--i:{ip()}" d="M76 262 L60 262 L60 98 L494 98 L494 250 L{CH_L} 250"/>')
    tl = "CLOUDFLARE TUNNEL &#8594; FFIOM VM"
    tw = 30 * CH
    a(f'<rect x="170" y="90" width="{tw:.0f}" height="15" fill="#F4F1EA"/>')
    a(f'<text class="pl-t" x="170" y="{98}" dominant-baseline="middle">{tl}</text>')

    # ---------------------------------------------------------------- dimension line
    dly = ZB + 26
    a(f'<line class="pl-dim" pathLength="1" style="--i:{ip()}" x1="{SX1}" y1="{dly}" x2="{SX2}" y2="{dly}"/>')
    a(f'<text class="pl-t" x="{(SX1+SX2)/2}" y="{dly-9}" text-anchor="middle">'
      f'SERVER SUBNET &#183; 3 PROXMOX NODES &#183; CEPH REPLICATION</text>')

    # ---------------------------------------------------------------- footer
    fy = 546
    a(f'<line class="pl-ln2" pathLength="1" style="--i:{ip()}" x1="46" y1="{fy}" x2="{W-46}" y2="{fy}"/>')

    # legend
    a(f'<text class="pl-tc" x="46" y="{fy+22}">LEGEND</text>')
    legend = [("host", "RACK / HOST"), ("svc", "SERVICE"), ("flow", "NETWORK FLOW"),
              ("tun", "CLOUDFLARE TUNNEL"), ("gpu", "GPU / ACCELERATOR"), ("fw", "FIREWALL GATE")]
    rows = [legend[:3], legend[3:]]
    lx = 46
    for ri, row in enumerate(rows):
        lx = 46
        ly = fy + 44 + ri * 30
        for kind, label in row:
            if kind == "host":
                a(rect("pl-box", lx, ly - 9, 18, 12, 1))
            elif kind == "svc":
                a(rect("pl-box2", lx, ly - 9, 18, 12, 1))
            elif kind == "flow":
                a(f'<path class="pl-ln" d="M{lx} {ly-3} L{lx+18} {ly-3}"/>')
                a(f'<circle cx="{lx+18}" cy="{ly-3}" r="2.6" fill="{ACC}"/>')
            elif kind == "tun":
                a(f'<path class="pl-tun" style="--i:{ip()}" d="M{lx} {ly-3} L{lx+18} {ly-3}"/>')
            elif kind == "gpu":
                a(rect("pl-hatch", lx, ly - 9, 18, 12, 1))
            else:
                a(f'<path class="pl-ln2" d="M{lx} {ly-3} L{lx+18} {ly-3}"/>')
                a(f'<line class="pl-ln3" x1="{lx+9}" y1="{ly-13}" x2="{lx+9}" y2="{ly+7}"/>')
            a(f'<text class="pl-t" x="{lx+25}" y="{ly}">{label}</text>')
            lx += 25 + len(label) * CH + 26

    # title block
    tbx0, tbx1 = 640, W - 46
    tby0, tby1 = fy + 20, H - 46
    a(rect("pl-tbf", tbx0, tby0, tbx1 - tbx0, tby1 - tby0))
    for yy in (tby0 + 30, tby0 + 60):
        a(f'<line class="pl-ln2" pathLength="1" style="--i:{ip()}" x1="{tbx0}" y1="{yy}" x2="{tbx1}" y2="{yy}"/>')
    a(f'<line class="pl-ln2" pathLength="1" style="--i:{ip()}" x1="{tbx0+160}" y1="{tby0}" x2="{tbx0+160}" y2="{tby1}"/>')
    a(f'<line class="pl-ln2" pathLength="1" style="--i:{ip()}" x1="{tbx0+300}" y1="{tby0}" x2="{tbx0+300}" y2="{tby1}"/>')
    rows = [("PROJECT", "EAMON McKIERNAN", "REV A"),
            ("DRAWING", "HOMELAB SITE PLAN", "SHEET 00 OF 00"),
            ("ISSUED", "2026", "SCALE NTS")]
    for i, (k, v1, v2) in enumerate(rows):
        yy = tby0 + 20 + i * 30
        a(f'<text class="pl-t" x="{tbx0+10}" y="{yy}">{k}</text>')
        a(f'<text class="pl-t9" x="{tbx0+170}" y="{yy}">{v1}</text>')
        a(f'<text class="pl-t9" x="{tbx0+310}" y="{yy}">{v2}</text>')

    a('</svg>')
    svg = "\n".join(o)

    # Annotation stages last: number every <text> in document order.
    def _num(m):
        tag = m.group(0)
        if "style=" in tag:
            return tag
        return tag.replace("<text ", '<text style="--i:%d" ' % it(), 1)

    svg = re.sub(r"<text\b[^>]*>", _num, svg)
    return svg


# ---------------------------------------------------------------- charts
def chart_prefill():
    """Project Maya: prefill tok/s vs context depth. Real published figures."""
    W, H = 520, 300
    L, R, T, B = 62, 20, 28, 52
    pw, ph = W - L - R, H - T - B
    pts = [("20K", 714), ("200K", 870), ("250K", 851)]
    ymax = 1000
    o = []
    a = o.append
    a(f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-labelledby="cpT">')
    a('<title id="cpT">Project Maya prefill throughput: 714 tok/s at 20K context, '
      '870 tok/s at 200K, 851 tok/s at 250K</title>')
    # gridlines
    for i in range(0, 5):
        v = ymax * i / 4
        y = T + ph - (v / ymax) * ph
        a(f'<line class="pl-grid" x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}"/>')
        a(f'<text class="pl-vals" x="{L-10}" y="{y+3.5:.1f}" text-anchor="end">{int(v)}</text>')
    a(f'<line class="pl-axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    a(f'<text class="pl-vals" x="{L}" y="{T-12}">TOK/S</text>')
    a(f'<text class="pl-vals" x="{L+pw}" y="{T-12}" text-anchor="end">PREFILL THROUGHPUT</text>')
    # area + line
    xs = [L + 40 + i * (pw - 80) / (len(pts) - 1) for i in range(len(pts))]
    ys = [T + ph - (v / ymax) * ph for _, v in pts]
    area = f"M {xs[0]:.1f} {T+ph} " + " ".join(f"L {x:.1f} {y:.1f}" for x, y in zip(xs, ys)) + f" L {xs[-1]:.1f} {T+ph} Z"
    a(f'<path d="{area}" fill="{ACC}" opacity=".10"/>')
    a(f'<path d="{" ".join(f"M{x:.1f} {y:.1f}" if i==0 else f"L{x:.1f} {y:.1f}" for i,(x,y) in enumerate(zip(xs,ys)))}" '
      f'fill="none" stroke="{ACC}" stroke-width="2"/>')
    for (lab, v), x, y in zip(pts, xs, ys):
        a(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{ACC}"/>')
        a(f'<text class="pl-val" x="{x:.1f}" y="{y-14:.1f}" text-anchor="middle">{v}</text>')
        a(f'<text class="pl-vals" x="{x:.1f}" y="{T+ph+20}" text-anchor="middle">{lab}</text>')
    a(f'<text class="pl-vals" x="{L+pw/2}" y="{T+ph+40}" text-anchor="middle">PROMPT DEPTH (TOKENS)</text>')
    a('</svg>')
    return "\n".join(o)


def chart_depths():
    """Engine 0.2.0-beta: prefill across six depths, 20K to 250K."""
    W, H = 520, 300
    L, R, T, B = 62, 20, 34, 62
    pw, ph = W - L - R, H - T - B
    ymax = 2400
    vals = [1568, 2098, 2149, 2127, 2055, 1974]
    o = []
    a = o.append
    a(f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-labelledby="cdT">')
    a('<title id="cdT">Prefill across six depths on engine 0.2.0-beta: 1568, 2098, '
      '2149, 2127, 2055 and 1974 tokens per second, from 20K to 250K</title>')
    for i in range(0, 5):
        v = ymax * i / 4
        y = T + ph - (v / ymax) * ph
        a(f'<line class="pl-grid" x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}"/>')
        a(f'<text class="pl-vals" x="{L-10}" y="{y+3.5:.1f}" text-anchor="end">{int(v):,}</text>')
    a(f'<line class="pl-axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    a(f'<text class="pl-vals" x="{L}" y="{T-16}">TOK/S</text>')
    a(f'<text class="pl-vals" x="{L+pw}" y="{T-16}" text-anchor="end">PREFILL, SIX DEPTHS</text>')

    slot = pw / len(vals)
    bw = slot * 0.52
    for i, v in enumerate(vals):
        bx = L + slot * i + (slot - bw) / 2
        bh = (v / ymax) * ph
        hot = (v == max(vals))
        cls = "pl-bar2" if hot else "pl-bar"
        a(f'<rect class="{cls}" x="{bx:.1f}" y="{T+ph-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}"/>')
        a(f'<text class="pl-val" x="{bx+bw/2:.1f}" y="{T+ph-bh-8:.1f}" text-anchor="middle">{v:,}</text>')
    # depth labels: only the two the source names
    a(f'<text class="pl-vals" x="{L+slot*0.5:.1f}" y="{T+ph+20}" text-anchor="middle">20K</text>')
    a(f'<text class="pl-vals" x="{L+slot*5.5:.1f}" y="{T+ph+20}" text-anchor="middle">250K</text>')
    a(f'<text class="pl-vals" x="{L+pw/2:.1f}" y="{T+ph+42}" text-anchor="middle">'
      f'SIX DEPTHS, 20K &#8594; 250K &#183; DECODE 73.7 &#8594; 64.2</text>')
    a('</svg>')
    return "\n".join(o)


def chart_shard():
    """Where the shard lived: SATA boot SSD vs NVMe, 250K prefill."""
    W, H = 520, 300
    L, R, T, B = 62, 20, 40, 62
    pw, ph = W - L - R, H - T - B
    ymax = 2400
    groups = [("SATA BOOT SSD", 1314), ("NVMe", 1974)]
    o = []
    a = o.append
    a(f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-labelledby="csT">')
    a('<title id="csT">Prefill at 250K context: 1314 tokens per second with the shard on '
      'the SATA boot SSD against 1974 on NVMe</title>')
    for i in range(0, 5):
        v = ymax * i / 4
        y = T + ph - (v / ymax) * ph
        a(f'<line class="pl-grid" x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}"/>')
        a(f'<text class="pl-vals" x="{L-10}" y="{y+3.5:.1f}" text-anchor="end">{int(v):,}</text>')
    a(f'<line class="pl-axis" x1="{L}" y1="{T+ph}" x2="{L+pw}" y2="{T+ph}"/>')
    a(f'<text class="pl-vals" x="{L}" y="{T-18}">TOK/S</text>')
    a(f'<text class="pl-vals" x="{L+pw}" y="{T-18}" text-anchor="end">PREFILL AT 250K</text>')
    gw = pw / len(groups)
    for i, (lab, v) in enumerate(groups):
        gx = L + gw * i
        bw = 76
        bx = gx + (gw - bw) / 2
        bh = (v / ymax) * ph
        cls = "pl-barg" if i == 0 else "pl-bar2"
        a(f'<rect class="{cls}" x="{bx:.1f}" y="{T+ph-bh:.1f}" width="{bw}" height="{bh:.1f}"/>')
        a(f'<text class="pl-val" x="{bx+bw/2:.1f}" y="{T+ph-bh-8:.1f}" text-anchor="middle">{v:,}</text>')
        a(f'<text class="pl-vals" x="{bx+bw/2:.1f}" y="{T+ph+20}" text-anchor="middle">{lab}</text>')
    # a dimension span between the two bars, in the drawing's own idiom
    sata_right = L + gw * 0 + (gw - 76) / 2 + 76
    nvme_left = L + gw * 1 + (gw - 76) / 2
    sata_top = T + ph - (groups[0][1] / ymax) * ph
    nvme_top = T + ph - (groups[1][1] / ymax) * ph
    by = T + 58
    a(f'<path class="pl-ln3" d="M{sata_right:.1f} {sata_top:.1f} L{sata_right:.1f} {by} '
      f'L{nvme_left:.1f} {by} L{nvme_left:.1f} {nvme_top:.1f}"/>')
    a(f'<text class="pl-tc" x="{(sata_right+nvme_left)/2:.1f}" y="{by-10:.1f}" '
      f'text-anchor="middle">+54.2%</text>')
    a(f'<text class="pl-vals" x="{L+pw/2:.1f}" y="{T+ph+42}" text-anchor="middle">'
      f'SAME ENGINE, SAME QUANT &#8212; ONLY THE STORAGE MOVED</text>')
    a('</svg>')
    return "\n".join(o)


def chart_backtest():
    """Trading bot: strategy vs equal-weight buy-and-hold, backtest and out-of-sample."""
    W, H = 520, 300
    L, R, T, B = 62, 20, 34, 52
    pw, ph = W - L - R, H - T - B
    ymin, ymax = -25, 45
    groups = [("BLIND BACKTEST", 35.9, -14.5), ("OUT-OF-SAMPLE", 16.5, 0.6)]
    o = []
    a = o.append
    a(f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-labelledby="cbT">')
    a('<title id="cbT">Strategy return against equal-weight buy-and-hold: 35.9 percent '
      'versus minus 14.5 percent in the blind backtest, 16.5 versus 0.6 percent '
      'out of sample</title>')
    zero = T + ph - ((0 - ymin) / (ymax - ymin)) * ph
    for v in (40, 20, 0, -20):
        y = T + ph - ((v - ymin) / (ymax - ymin)) * ph
        a(f'<line class="pl-grid" x1="{L}" y1="{y:.1f}" x2="{L+pw}" y2="{y:.1f}"/>')
        a(f'<text class="pl-vals" x="{L-10}" y="{y+3.5:.1f}" text-anchor="end">{v:+d}</text>')
    a(f'<line class="pl-axis" x1="{L}" y1="{zero:.1f}" x2="{L+pw}" y2="{zero:.1f}"/>')
    a(f'<text class="pl-vals" x="{L}" y="{T-14}">RETURN %</text>')
    a(f'<text class="pl-vals" x="{L+pw}" y="{T-14}" text-anchor="end">STRATEGY vs BUY-AND-HOLD</text>')
    gw = (pw - 60) / len(groups)
    for gi, (lab, s, b) in enumerate(groups):
        gx = L + 30 + gi * gw
        bw = 44
        for bi, (v, cls, cap) in enumerate([(s, "pl-bar2", "STRATEGY"), (b, "pl-barg", "BUY & HOLD")]):
            bx = gx + bi * (bw + 12)
            bh = abs(v) / (ymax - ymin) * ph
            y = zero - bh if v >= 0 else zero
            a(f'<rect class="{cls}" x="{bx:.1f}" y="{y:.1f}" width="{bw}" height="{bh:.1f}"/>')
            vy = y - 7 if v >= 0 else y + bh + 13
            a(f'<text class="pl-val" x="{bx+bw/2:.1f}" y="{vy:.1f}" text-anchor="middle">{v:+.1f}%</text>')
            a(f'<text class="pl-vals" x="{bx+bw/2:.1f}" y="{T+ph+20}" text-anchor="middle">{cap}</text>')
        a(f'<text class="pl-vals" x="{gx+bw:.1f}" y="{T+ph+40}" text-anchor="middle">{lab}</text>')
    a('</svg>')
    return "\n".join(o)


def chart_findings():
    """FFIOM: code-review findings by severity, 34 total."""
    W, H = 520, 220
    L, R, T, B = 62, 20, 46, 40
    pw, ph = W - L - R, H - T - B
    segs = [("HIGH", 10, "#B23A1C"), ("MEDIUM", 15, "#C77A4A"), ("LOW", 9, "#D8D2C4")]
    total = sum(s[1] for s in segs)
    o = []
    a = o.append
    a(f'<svg viewBox="0 0 {W} {H}" class="chart-svg" role="img" aria-labelledby="cfT">')
    a('<title id="cfT">Code review findings: 10 high, 15 medium, 9 low, 34 in total, '
      'all remediated</title>')
    a(f'<text class="pl-vals" x="{L}" y="{T-16}">FINDINGS BY SEVERITY</text>')
    a(f'<text class="pl-tc" x="{L+pw}" y="{T-16}" text-anchor="end">{total} TOTAL &#183; ALL REMEDIATED</text>')
    x = L
    for name, v, col in segs:
        w = (v / total) * pw
        a(f'<rect x="{x:.1f}" y="{T}" width="{w:.1f}" height="26" fill="{col}"/>')
        tc = "#fff" if name != "LOW" else INK
        a(f'<text x="{x+w/2:.1f}" y="{T+18}" text-anchor="middle" '
          f'font-family="{MONO}" font-size="11" fill="{tc}">{v}</text>')
        x += w
    a(f'<line class="pl-axis" x1="{L}" y1="{T+26}" x2="{L+pw}" y2="{T+26}"/>')
    x = L
    for name, v, col in segs:
        w = (v / total) * pw
        a(f'<text class="pl-vals" x="{x+w/2:.1f}" y="{T+46}" text-anchor="middle">{name}</text>')
        x += w
    a('</svg>')
    return "\n".join(o)


