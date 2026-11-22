"""Record 60 s 1080p clips on the Windows box, driven from here over a CDP tunnel.

Rendering happens on the Windows GPU (Edge, ANGLE/D3D11); frames stream back over
the tunnel as JPEG and are muxed here. The finished mp4 is copied to the Windows
desktop under "Model Testing Videos/<Workspace>/".
"""
from __future__ import annotations

import asyncio
import base64
import io
import json
import pathlib
import re
import shutil
import socket
import subprocess
import time
import urllib.parse
import urllib.request

import websockets
from PIL import Image, ImageChops, ImageStat

from . import win

FFMPEG = "/home/eamon/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffmpeg"
FFPROBE = "/home/eamon/.hermes/tools/ffmpeg-9.0.1-linux-x64/bin/ffprobe"
SCRATCH = pathlib.Path.home() / ".hermes/profiles/dev/cache/scratch/dsh_daily"
THUMBS = pathlib.Path.home() / "portfolio-website/demos/thumbs/model-testing"
LOCAL_VIDEOS = pathlib.Path.home() / "video-demos/dsh-daily"
DESKTOP_SUBDIR = "Model Testing Videos"
DURATION = 60.0

LOADER = """(()=>{const l=document.querySelector('#loader,#loading,.loader,.loading,.preloader');
if(!l)return 'gone';const s=getComputedStyle(l);return s.display+'|'+s.opacity})()"""
RAF = """new Promise(r=>{let c=0,t0=performance.now();function f(){c++;
if(performance.now()-t0<1000) requestAnimationFrame(f); else r(c)} requestAnimationFrame(f)})"""
FIND = """(()=>{const SEL=['btnCinematic','cinematic','btn-cinematic','btn-cine','cin'];
  let b=null; for(const id of SEL){ b=document.getElementById(id); if(b) break; }
  if(!b){ b=[...document.querySelectorAll('button,[role=switch],[role=button],.btn,.ctl')]
    .find(e=>/cinematic/i.test((e.textContent||'')+' '+(e.id||'')+' '+(e.title||'')+' '+(e.className||'')))||null; }
  if(!b) return 'none';
  const ap=b.getAttribute('aria-pressed'), ac=b.getAttribute('aria-checked');
  const parts=String(b.className||'').split(' ');
  const onCls = parts.indexOf('on')>=0 || parts.indexOf('active')>=0;
  let js=null; try{ const g=window.HAY_CAMERA||window.CAMERA||window.camera;
    if(g && typeof g.cinematic!=='undefined') js=g.cinematic; }catch(e){}
  let ui=null; try{ if(typeof UI!=='undefined' && typeof UI.cinematic!=='undefined') ui=UI.cinematic; }catch(e){}
  const on = ap==='true' || ac==='true' || onCls || js===true || ui===true;
  return JSON.stringify({found:true,on:on,ap:ap,ac:ac,cls:b.className||''})})()"""
TOGGLE = """(()=>{const SEL=['btnCinematic','cinematic','btn-cinematic','btn-cine','cin'];
  let b=null; for(const id of SEL){ b=document.getElementById(id); if(b) break; }
  if(!b){ b=[...document.querySelectorAll('button,[role=switch],[role=button],.btn,.ctl')]
    .find(e=>/cinematic/i.test((e.textContent||'')+' '+(e.id||'')+' '+(e.title||'')+' '+(e.className||'')))||null; }
  if(!b) return 'none'; b.click(); return 'clicked'})()"""


def log(msg: str) -> None:
    print(f"[rec {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.168.1.1", 9))
        return s.getsockname()[0]
    finally:
        s.close()


def _diff(a: bytes, b: bytes) -> float:
    ia = Image.open(io.BytesIO(a)).convert("L")
    ib = Image.open(io.BytesIO(b)).convert("L")
    return ImageStat.Stat(ImageChops.difference(ia, ib)).mean[0]


async def _record_one(call, js, slug: str, url: str, out_mp4: pathlib.Path, state: dict, frames: list) -> dict:
    await call("Page.navigate", url=url)
    t0 = time.time()
    while time.time() - t0 < 180:
        st = await js(LOADER)
        if st == "gone" or (isinstance(st, str) and st.split("|")[1:2] == ["0"]):
            break
        await asyncio.sleep(2)
    rate = 0
    for _ in range(20):
        rate = await js(RAF) or 0
        if rate >= 20:
            break
        await asyncio.sleep(3)
    log(f"{slug}: warm rAF {rate}/s")

    cstate = await js(FIND) or "none"
    log(f"{slug}: cinematic {cstate}")
    clicked = False
    if '"on":true' not in cstate and cstate != "none":
        await js(TOGGLE)
        clicked = True
        await asyncio.sleep(1.5)
        cstate = await js(FIND) or "none"
    if '"on":true' not in cstate:
        for key in ("c", "C"):
            await call("Input.dispatchKeyEvent", type="keyDown", key=key, text=key)
            await call("Input.dispatchKeyEvent", type="keyUp", key=key)
            await asyncio.sleep(1)
            cstate = await js(FIND) or "none"
            if '"on":true' in cstate:
                break
    cinematic = '"on":true' in cstate
    if cstate == "none":
        log(f"{slug}: no cinematic control — recording as the build opens")
    elif not cinematic:
        log(f"{slug}: WARNING cinematic not confirmed ON ({cstate})")

    await asyncio.sleep(2)
    a = base64.b64decode((await call("Page.captureScreenshot", format="jpeg", quality=80))["data"])
    await asyncio.sleep(4)
    b = base64.b64decode((await call("Page.captureScreenshot", format="jpeg", quality=80))["data"])
    pre_motion = _diff(a, b)

    frames.clear()
    state["recording"] = True
    await call("Page.startScreencast", format="jpeg", quality=88, maxWidth=1920, maxHeight=1080, everyNthFrame=1)
    started = time.time()
    while time.time() - started < DURATION:
        await asyncio.sleep(0.5)
    await call("Page.stopScreencast")
    state["recording"] = False
    elapsed = time.time() - started
    log(f"{slug}: captured {len(frames)} frames in {elapsed:.1f}s = {len(frames)/elapsed:.1f} fps")
    if not frames:
        raise RuntimeError("no frames captured")

    tmp = SCRATCH / "frames" / slug
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    best = (0, None)
    for k, data in enumerate(frames):
        (tmp / f"f{k:05d}.jpg").write_bytes(data)
        if k % 30 == 0:
            lu = ImageStat.Stat(Image.open(io.BytesIO(data)).convert("L")).mean[0]
            if 20 <= lu <= 240 and lu > best[0]:
                best = (lu, data)
    fps = max(1.0, len(frames) / elapsed)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-framerate", f"{fps:.4f}",
                    "-i", str(tmp / "f%05d.jpg"), "-r", "30", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(out_mp4)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)

    if best[1]:
        THUMBS.mkdir(parents=True, exist_ok=True)
        Image.open(io.BytesIO(best[1])).convert("RGB").save(THUMBS / f"{slug}.jpg", quality=88)

    probe = json.loads(subprocess.run([FFPROBE, "-v", "error", "-show_entries",
        "stream=width,height,codec_name,duration:format=size", "-of", "json", str(out_mp4)],
        capture_output=True, text=True).stdout)
    st = probe["streams"][0]
    size = int(probe["format"]["size"])
    dur = float(st["duration"])
    log(f"{slug}: {st['width']}x{st['height']} {st['codec_name']} {dur:.1f}s {size/1e6:.1f} MB")
    problems = []
    if not 57 <= dur <= 63:
        problems.append(f"duration {dur:.1f}s")
    if (st["width"], st["height"]) != (1920, 1080):
        problems.append(f"{st['width']}x{st['height']}")
    if st["codec_name"] != "h264":
        problems.append(st["codec_name"])

    # motion measured from the encoded file, not from the live page
    samples = {}
    for t in (2, 30, 58):
        p = SCRATCH / f"{slug}-t{t}.jpg"
        subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-ss", str(t), "-i", str(out_mp4),
                        "-frames:v", "1", str(p)], check=True)
        samples[t] = p.read_bytes()
        p.unlink()
    motion = round(_diff(samples[2], samples[58]), 1)

    return dict(slug=slug, clip=str(out_mp4), bytes=size, seconds=round(dur, 1),
                fps=round(fps, 1), frames=len(frames), cinematic=cinematic,
                cinematic_clicked=clicked, pre_motion=round(pre_motion, 1),
                motion=motion, problems=problems, thumb=best[1] is not None)


async def _run(pairs, port: int, base: str, outdir: pathlib.Path) -> list[dict]:
    pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
    ws_url = next(p["webSocketDebuggerUrl"] for p in pages if p["type"] == "page")
    results = []
    async with websockets.connect(ws_url, max_size=1 << 28) as ws:
        seq = [0]
        pending: dict[int, asyncio.Future] = {}
        frames: list = []
        state = {"recording": False}

        async def reader():
            async for raw in ws:
                msg = json.loads(raw)
                if "id" in msg:
                    fut = pending.pop(msg["id"], None)
                    if fut and not fut.done():
                        fut.set_result(msg.get("result", {}))
                elif msg.get("method") == "Page.screencastFrame":
                    p = msg["params"]
                    if state["recording"]:
                        frames.append(base64.b64decode(p["data"]))
                    seq[0] += 1
                    # fire-and-forget ack; awaiting it here deadlocks this reader
                    await ws.send(json.dumps({"id": seq[0], "method": "Page.screencastFrameAck",
                                              "params": {"sessionId": p["sessionId"]}}))

        async def call(method, **p):
            seq[0] += 1
            mid = seq[0]
            fut = asyncio.get_event_loop().create_future()
            pending[mid] = fut
            await ws.send(json.dumps({"id": mid, "method": method, "params": p}))
            return await fut

        async def js(expr):
            r = await call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
            return r.get("result", {}).get("value")

        task = asyncio.create_task(reader())
        await call("Page.enable")
        await call("Emulation.setDeviceMetricsOverride", width=1920, height=1080,
                   deviceScaleFactor=1, mobile=False)
        for slug, rel in pairs:
            url = base + urllib.parse.quote(rel)
            try:
                res = await _record_one(call, js, slug, url, outdir / f"{slug}.mp4", state, frames)
            except Exception as exc:  # one bad build must not kill the batch
                log(f"{slug}: FAILED {exc}")
                res = dict(slug=slug, error=str(exc))
            results.append(res)
        task.cancel()
    return results


def record_builds(pairs: list[tuple[str, str]], *, port: int = 9223,
                  outdir: pathlib.Path = LOCAL_VIDEOS, copy_to_desktop: bool = True) -> list[dict]:
    """Launch the box's Edge, tunnel CDP, record each build, deliver the mp4s."""
    outdir.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    win.ps("edge_launch.ps1", str(port))
    tunnel = win.start_tunnel(port)
    try:
        if not win.cdp_ready(port, 30):
            raise RuntimeError("the box's CDP port never answered over the tunnel")
        base = f"http://{local_ip()}:8099/demos/model-testing/"
        results = asyncio.run(_run(pairs, port, base, outdir))
    finally:
        tunnel.terminate()
        try:
            win.ps("edge_kill.ps1", timeout=120)
        except Exception:
            pass
    if copy_to_desktop:
        for r in results:
            if "clip" not in r:
                continue
            local = pathlib.Path(r["clip"])
            workspace = r.get("workspace") or ""
            remote_rel = f"{DESKTOP_SUBDIR}/{workspace}/{local.name}"
            win.push(local, remote_rel)
            r["desktop"] = remote_rel
    return results
