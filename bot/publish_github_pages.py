#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pages publisher
======================
Commits a generated article to your GitHub repository via the GitHub REST API.
GitHub Pages then rebuilds and publishes it automatically.

Environment variables:
  GITHUB_TOKEN  - a GitHub personal access token (fine-grained, Contents: Read & Write)
  GITHUB_REPO   - owner/repository, e.g. "yourname/yourname.github.io"

Usage:
  python3 publish_github_pages.py _posts/2026-09-28-brr-strategy.md
  python3 publish_github_pages.py _posts/2026-09-28-brr-strategy.md --remote-dir _posts
"""
import argparse
import base64
import os
import sys

API = "https://api.github.com"


def put_file(repo, local_path, remote_path, message, branch, token):
    import requests

    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    url = "%s/repos/%s/contents/%s" % (API, repo, remote_path.lstrip("/"))

    # If the file already exists we must supply its sha to update it.
    r = requests.get(url, headers=headers, params={"branch": branch}, timeout=30)
    body = {"message": message, "content": content, "branch": branch}
    if r.status_code == 200:
        body["sha"] = r.json()["sha"]
    elif r.status_code != 404:
        sys.exit("GitHub lookup failed (%s): %s" % (r.status_code, r.text[:200]))

    r = requests.put(url, json=body, headers=headers, timeout=60)
    if r.status_code not in (200, 201):
        sys.exit("GitHub commit failed (%s): %s" % (r.status_code, r.text[:300]))
    return r.json()["commit"]["html_url"]


def main():
    ap = argparse.ArgumentParser(description="Publish a file to your GitHub Pages repo.")
    ap.add_argument("file", help="Local file to commit (e.g. a generated article)")
    ap.add_argument("--remote-dir", default="_posts",
                    help="Folder inside the repo (default: _posts)")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPO"),
                    help="owner/repo (or set GITHUB_REPO env var)")
    ap.add_argument("--branch", default=os.environ.get("GITHUB_BRANCH", "main"))
    ap.add_argument("--message", default="New property article (auto-published)")
    args = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN (a personal access token with Contents: Read & Write).")
    if not args.repo:
        sys.exit("Set GITHUB_REPO (e.g. yourname/yourname.github.io) or pass --repo.")
    if not os.path.exists(args.file):
        sys.exit("File not found: " + args.file)

    remote_path = args.remote_dir.strip("/") + "/" + os.path.basename(args.file)
    commit_url = put_file(args.repo, args.file, remote_path, args.message, args.branch, token)
    print("Committed to " + args.repo + " (" + args.branch + "):")
    print("  " + remote_path)
    print("  " + commit_url)
    print("GitHub Pages will rebuild and publish within a minute or two.")


if __name__ == "__main__":
    main()
