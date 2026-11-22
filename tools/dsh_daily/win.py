"""Windows box helpers for the dsh daily pipeline: ssh, powershell, scp."""
from __future__ import annotations

import json
import pathlib
import shlex
import subprocess

HOST = "wsl30"
WIN_HOME = r"C:\Users\eamon"
REMOTE_DIR = WIN_HOME + r"\dsh"
HERE = pathlib.Path(__file__).resolve().parent
PS_DIR = HERE / "win"

SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]


def _clean(txt: str) -> str:
    """Drop the noisy post-quantum warning banner OpenSSH prints on this host."""
    keep = []
    for line in txt.splitlines():
        low = line.lower()
        if "post-quantum" in low or "store now" in low or low.startswith("** this session"):
            continue
        if "warning: perman" in low:
            continue
        keep.append(line)
    return "\n".join(keep)


def ssh(cmd: str, timeout: int = 300) -> str:
    p = subprocess.run(["ssh", *SSH_OPTS, HOST, cmd], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"ssh failed ({p.returncode}): {_clean(p.stderr)[-800:]}")
    return _clean(p.stdout)


def push_script(name: str) -> str:
    """Copy tools/dsh_daily/win/<name> to the box and return its remote path."""
    remote = f"{REMOTE_DIR}\\{name}".replace("\\", "/")
    ssh(f'if not exist "{REMOTE_DIR}" mkdir "{REMOTE_DIR}"')
    src = PS_DIR / name
    subprocess.run(["scp", *SSH_OPTS, "-q", str(src), f"{HOST}:{remote}"], check=True, timeout=120)
    return REMOTE_DIR + "\\" + name


def ps(file_name: str, *args: str, timeout: int = 300) -> str:
    """Run an installed .ps1 by name (single quotes keep backslashes intact)."""
    remote = push_script(file_name)
    # cmd.exe does not strip single quotes, so the -File path must use double quotes.
    tail = "".join(' "' + a + '"' for a in args)
    return ssh(f'powershell -NoProfile -ExecutionPolicy Bypass -File "{remote}"{tail}', timeout=timeout)


def decode_workspace(encoded: str) -> str:
    """--C-Users-Eamon-Desktop-Model~0020Testing-<name>--  ->  <name>"""
    name = encoded.strip("-")
    name = name.split("-Desktop-Model~0020Testing-", 1)[-1]
    return name.replace("~0020", " ").replace("~0028", "(").replace("~0029", ")").strip()


def inventory(since_iso: str) -> dict:
    out = ps("inventory.ps1", since_iso, timeout=600)
    start = out.find("{")
    if start < 0:
        raise RuntimeError(f"inventory gave no JSON: {out[:400]}")
    return json.loads(out[start:])


def pull(remote_rel: str, dest: pathlib.Path) -> int:
    """scp one file from the box (path relative to C:\\Users\\Eamon)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    remote = "C:/Users/eamon/" + remote_rel.replace("\\", "/")
    # the Windows scp speaks SFTP, so a literal space works and %20 or quotes do not
    subprocess.run(["scp", *SSH_OPTS, "-q", f"{HOST}:{remote}", str(dest)], check=True, timeout=600)
    return dest.stat().st_size


def push(local: pathlib.Path, remote_rel: str) -> None:
    import shutil as _sh
    remote = "C:/Users/eamon/" + remote_rel.replace("\\", "/")
    parts = remote_rel.replace("\\", "/").split("/")[:-1]
    win_dir = WIN_HOME + "\\" + "\\".join(parts)
    ssh(f'if not exist "{win_dir}" mkdir "{win_dir}"')
    subprocess.run(["scp", *SSH_OPTS, "-q", str(local), f"{HOST}:{remote}"], check=True, timeout=1800)


def start_tunnel(local_port: int, remote_port: int | None = None):
    """ssh -N -L so a CDP port on the box answers on this host."""
    remote_port = remote_port or local_port
    cmd = ["ssh", *SSH_OPTS, "-o", "ExitOnForwardFailure=yes", "-N",
           "-L", f"{local_port}:127.0.0.1:{remote_port}", HOST]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def cdp_ready(port: int, timeout: float = 20.0) -> bool:
    import time, urllib.request
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False
