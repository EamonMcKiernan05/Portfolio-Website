#!/usr/bin/env python3
"""Capture preview thumbnails for gallery builds that build their world slowly.

Launches its own headless Chrome (SwiftShader WebGL), navigates each build, polls the page's
#loader until the intro overlay clears, then grabs a 1280x800 JPEG. Unattended: run in the
background and check the log.
"""
import asyncio
import base64
import json
import pathlib
import subprocess
import sys
import time
import urllib.parse
import urllib.request

import websockets

PORT = 9337
OUT = pathlib.Path("/home/eamon/portfolio-website/demos/thumbs/model-testing")
OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://127.0.0.1:8099/demos/model-testing/"

PENDING = [
    ("qwen4-preview-liberty", "Qwen 4 Preview/liberty-1886.html"),
    ("qwen4-preview-village", "Qwen 4 Preview/medieval-village.html"),
    ("qwen-code-liberty", "QwenCode/liberty-1886.html"),
    ("qwen-code-liberty-baseline", "QwenCode/lbuild/baseline-gap.html"),
    ("qwen-code-village", "QwenCode/medieval-village.html"),
    ("deepseek-v41-castle", "DeepSeek-V4.1-Flash-1017/THE-CASTLE.html"),
    ("deepseek-v41-sky-temple", "DeepSeek-V4.1-Flash-1017/sky-temple-DeepSeek-V4.1-Flash-1017.html"),
    ("deepseek-v41-nightfall", "DeepSeek-V4.1-Flash-1017/test1-deepseek-v4.1-flash-1017.html"),
    ("minimax-m31-sky-temple", "MiniMax M3.1-Flash Tests/sky-temple-minimax-m3-1-flash.html"),
    ("minimax-m31-dusk-cityline", "MiniMax M3.1-Flash Tests/dusk-cityline-minimax-m3.1-flash.html"),
    ("hy4-castle", "HY4/THE-CASTLE.html"),
    ("longcat-25-sky-temple", "LongCat-2.5/sky-temple.html"),
]

LOADER_STATE = """(()=>{const l=document.querySelector('#loader,#loading,.loader,.loading,.preloader');
if(!l)return 'gone';const s=getComputedStyle(l);
return s.display+'|'+s.opacity+'|'+((l.innerText||'').trim().split('\\n').pop()||'').slice(0,30)})()"""


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


async def main():
    chrome = subprocess.Popen([
        "google-chrome", "--headless=new", "--no-sandbox", "--hide-scrollbars",
        "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
        f"--remote-debugging-port={PORT}", "--window-size=1280,800",
        "--user-data-dir=/tmp/thumb-chrome", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ws_url = None
    for _ in range(40):
        try:
            pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
            page = next(p for p in pages if p["type"] == "page")
            ws_url = page["webSocketDebuggerUrl"]
            break
        except Exception:
            time.sleep(0.5)
    if not ws_url:
        log("could not attach to chrome")
        chrome.kill()
        return

    async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
        n = [0]

        async def call(method, **params):
            n[0] += 1
            await ws.send(json.dumps({"id": n[0], "method": method, "params": params}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == n[0]:
                    return msg.get("result", {})

        async def js(expr):
            r = await call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
            return r.get("result", {}).get("value")

        await call("Page.enable")
        await call("Emulation.setDeviceMetricsOverride", width=1280, height=800,
                   deviceScaleFactor=1, mobile=False)

        for slug, rel in PENDING:
            dest = OUT / f"{slug}.jpg"
            if dest.exists() and dest.stat().st_size > 45000:
                log(f"{slug}: already good, skip")
                continue
            url = BASE + urllib.parse.quote(rel)
            await call("Page.navigate", url=url)
            await asyncio.sleep(4)
            t0 = time.time()
            state = "?"
            while time.time() - t0 < 480:
                state = await js(LOADER_STATE)
                if state == "gone" or state.startswith("none") or state.split("|")[1:2] == ["0"]:
                    break
                await asyncio.sleep(3)
            await asyncio.sleep(3)
            shot = await call("Page.captureScreenshot", format="jpeg", quality=84)
            dest.write_bytes(base64.b64decode(shot["data"]))
            log(f"{slug}: {round(time.time()-t0)}s state={state[:34]!r} -> {dest.stat().st_size//1024} KB")

    chrome.kill()
    log("done")


asyncio.run(main())
