#!/usr/bin/env python3
"""Render the PNG fallbacks for assets/favicon.svg.

The SVG is the master. Browsers that support SVG favicons use it directly;
these rasters are the fallback for anything that does not, plus the
apple-touch-icon iOS looks for.

    python3 tools/icons.py
"""
import functools
import http.server
import os
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, "assets")
SVG = os.path.join(ASSETS, "favicon.svg")

TARGETS = [("favicon-32.png", 32), ("apple-touch-icon.png", 180)]


def find_chrome():
    for c in ("google-chrome", "chromium", "chromium-browser", "chrome",
              "/usr/bin/google-chrome", "/usr/bin/chromium"):
        path = shutil_which(c)
        if path:
            return path
    raise SystemExit("no Chrome/Chromium found")


def shutil_which(name):
    from shutil import which
    return which(name)


def render(chrome, size, dest, port, http_port):
    """Screenshot the SVG at an exact pixel size.

    Chrome's window has a minimum size, so the page is rendered in a large
    window and the viewport is overridden down to the icon size with the
    DevTools protocol before the capture.
    """
    page = os.path.join(HERE, "_icon_render.html")
    with open(page, "w", encoding="utf-8") as f:
        f.write(
            '<!doctype html><meta charset="utf-8">'
            '<style>html,body{margin:0;padding:0;overflow:hidden;background:#F4F1EA}'
            'img{display:block;width:%dpx;height:%dpx}</style>'
            '<img src="/assets/favicon.svg">' % (size, size))

    profile = tempfile.mkdtemp(prefix="icon-prof-")
    proc = subprocess.Popen(
        [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
         "--remote-debugging-port=%d" % port, "--user-data-dir=" + profile,
         "--window-size=420,420", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import json
        import socket
        import struct
        import base64
        import urllib.request

        ws = None
        for _ in range(60):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=2) as r:
                    ws = json.loads(r.read().decode())["webSocketDebuggerUrl"]
                break
            except Exception:
                time.sleep(0.3)
        if not ws:
            raise SystemExit("chrome did not start")

        u = ws.split("://", 1)[1]
        hostport, path = u.split("/", 1)
        host, ps = hostport.split(":")
        sock = socket.create_connection((host, int(ps)), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        sock.sendall(("GET /%s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n"
                      "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
                      "Sec-WebSocket-Version: 13\r\n\r\n" % (path, hostport, key)).encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += sock.recv(4096)

        mid = [0]

        def send(method, params=None, session=None):
            mid[0] += 1
            pl = {"id": mid[0], "method": method, "params": params or {}}
            if session:
                pl["sessionId"] = session
            data = json.dumps(pl).encode()
            h = bytearray([0x81])
            n = len(data)
            if n < 126:
                h.append(0x80 | n)
            elif n < 65536:
                h.append(0x80 | 126)
                h += struct.pack(">H", n)
            else:
                h.append(0x80 | 127)
                h += struct.pack(">Q", n)
            mask = os.urandom(4)
            h += mask
            sock.sendall(bytes(h) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))
            return mid[0]

        def recv():
            h = sock.recv(2)
            ln = h[1] & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", sock.recv(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", sock.recv(8))[0]
            d = b""
            while len(d) < ln:
                d += sock.recv(ln - len(d))
            return json.loads(d.decode())

        def wait(m, timeout=45):
            end = time.time() + timeout
            while time.time() < end:
                sock.settimeout(max(1, end - time.time()))
                r = recv()
                if r.get("id") == m:
                    return r
            raise SystemExit("timeout waiting for %s" % m)

        t = wait(send("Target.createTarget", {"url": "about:blank"}))
        sess = wait(send("Target.attachToTarget",
                          {"targetId": t["result"]["targetId"], "flatten": True}))["result"]["sessionId"]
        wait(send("Page.enable", {}, sess))
        wait(send("Emulation.setDeviceMetricsOverride",
                  {"width": size, "height": size, "deviceScaleFactor": 1, "mobile": False}, sess))
        wait(send("Page.navigate", {"url": "http://127.0.0.1:%d/tools/_icon_render.html" % http_port}, sess))
        time.sleep(1.4)
        r = wait(send("Page.captureScreenshot", {"format": "png"}, sess))
        with open(dest, "wb") as f:
            f.write(base64.b64decode(r["result"]["data"]))
        sock.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        if os.path.exists(page):
            os.remove(page)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not os.path.exists(SVG):
        raise SystemExit("missing %s" % SVG)
    chrome = find_chrome()

    # serve the repo so the SVG resolves over http rather than file://
    handler = functools.partial(Quiet, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    http_port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    port = 9333
    try:
        for name, size in TARGETS:
            dest = os.path.join(ASSETS, name)
            render(chrome, size, dest, port, http_port)
            port += 1
            print("wrote %s (%d bytes)" % (dest, os.path.getsize(dest)))
    finally:
        httpd.shutdown()
