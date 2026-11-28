"""Ship the gallery: branch, commit, push, merge, deploy, verify."""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys

SITE = pathlib.Path.home() / "portfolio-website"
MIRROR = pathlib.Path.home() / "Local-LLM-Testing"
SITE_REPO = "EamonMcKiernan05/Portfolio-Website"
MIRROR_REPO = "EamonMcKiernan05/Local-LLM-Testing"


def sh(cmd: str, cwd: pathlib.Path, timeout: int = 600) -> str:
    p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"{cmd} failed in {cwd.name}: {(p.stderr or p.stdout)[-600:]}")
    return p.stdout.strip()


def gh_env() -> dict:
    """gh needs a token; take GH_TOKEN from the environment or from Bitwarden at run time."""
    env = os.environ.copy()
    if env.get("GH_TOKEN") or env.get("GITHUB_TOKEN"):
        return env
    bws = pathlib.Path.home() / ".hermes/tools/bws-2.0.0-linux-x64/bws"
    env_file = pathlib.Path.home() / ".hermes/.env"
    bws_token = None
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("BWS_ACCESS_TOKEN="):
                bws_token = line.split("=", 1)[1].strip()
    if not bws_token or not bws.exists():
        raise RuntimeError("no GH_TOKEN and no Bitwarden access token available for gh")
    # the token is an EU account; bws defaults to the US server and answers 401
    run_env = {**env, "BWS_ACCESS_TOKEN": bws_token, "BWS_SERVER_URL": "https://vault.bitwarden.eu"}
    out = subprocess.run([str(bws), "secret", "list", "b6e7789d-ae5c-4604-9807-b4da01052f22",
                          "-o", "json"],
                         capture_output=True, text=True, timeout=120, env=run_env)
    if out.returncode != 0:
        raise RuntimeError(f"bws secret list failed: {out.stderr[-300:]}")
    for item in json.loads(out.stdout):
        if item.get("key") == "GITHUB_PAT" and item.get("value"):
            env["GH_TOKEN"] = item["value"]
            return env
    raise RuntimeError("GITHUB_PAT not found in the Bitwarden project")


def _merge(branch: str, repo: str) -> str:
    out = subprocess.run(["gh", "api", "-X", "POST", f"repos/{repo}/merges",
                          "-f", "base=main", "-f", f"head={branch}", "--jq", ".sha"],
                         capture_output=True, text=True, timeout=300, env=gh_env())
    sha = out.stdout.strip()
    if out.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise RuntimeError(f"merge of {branch} into {repo} failed: {(out.stderr or out.stdout)[-400:]}")
    return sha


def ship(commit_msg: str, *, deploy: bool = True) -> dict:
    # regenerate first: thumb URLs carry a ?v=<mtime>-<bytes> cache-buster, so replacing a thumb
    # without rebuilding leaves the old stamp in gallery.html and Cloudflare serves the old image
    subprocess.run([sys.executable, str(SITE / "tools/build_model_gallery.py")],
                   check=True, capture_output=True)
    branch = "dsh-daily/" + subprocess.run(
        ["date", "+%Y-%m-%d"], capture_output=True, text=True).stdout.strip()
    out = {}
    for path, repo, label in ((SITE, SITE_REPO, "site"), (MIRROR, MIRROR_REPO, "mirror")):
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=path,
                               capture_output=True, text=True).stdout.strip()
        if not dirty:
            out[label] = {"changed": False}
            continue
        sh("git checkout -B " + branch, path)
        sh("git add -A", path)
        sh(f'git -c user.name=dev -c user.email=dev@eamonmckiernan.im commit -q -m "{commit_msg}"', path)
        head = sh("git rev-parse --short HEAD", path)
        sh(f"git push -q -f -u origin {branch}", path, timeout=900)
        out[label] = {"changed": True, "branch": branch, "head": head}
    if not any(v.get("changed") for v in out.values()):
        out["deployed"] = False
        return out
    if out["site"].get("changed"):
        out["site"]["merge"] = _merge(branch, SITE_REPO)
        out["deployed"] = bool(deploy)
        if deploy:
            deploy_site()
    if out["mirror"].get("changed"):
        out["mirror"]["merge"] = _merge(branch, MIRROR_REPO)
    return out


def deploy_site() -> str:
    cmd = ("cd /var/www/portfolio && git update-ref -d refs/remotes/origin/main 2>/dev/null; "
           "git fetch -q origin && git reset -q --hard origin/main && git log -1 --format=%h")
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "portfolio", cmd],
                       capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(f"deploy on the live host failed: {p.stderr[-400:]}")
    return p.stdout.strip().splitlines()[0]


def live_check() -> dict:
    def fetch(url: str) -> str:
        return subprocess.run(["curl", "-s", url], capture_output=True, text=True, timeout=60).stdout

    gallery = fetch("https://eamonmckiernan.im/gallery.html")
    cards = len(re.findall(r'class="gal-card"', gallery))
    imgs = len(re.findall(r'<img[^>]+demos/thumbs/model-testing/', gallery))
    return {"cards": cards, "thumbs": imgs}
