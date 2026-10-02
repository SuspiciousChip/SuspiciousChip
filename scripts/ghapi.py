"""Tiny GitHub API helper (stdlib only). Reads GH_USER and GH_TOKEN from env."""
import json
import os
import urllib.request

USER = os.environ["GH_USER"]
TOKEN = os.environ.get("GH_TOKEN", "")


def _req(url, data=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-gen"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def rest(path):
    return _req(path if path.startswith("http") else f"https://api.github.com{path}")


def gql(query, **variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    out = _req("https://api.github.com/graphql", body)
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


def repos():
    out, page = [], 1
    while True:
        batch = rest(f"/users/{USER}/repos?per_page=100&type=owner&page={page}")
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def calendar():
    q = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{totalContributions weeks{contributionDays{
      date contributionCount weekday}}}}}}"""
    cal = gql(q, login=USER)["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["totalContributions"], cal["weeks"]


def streaks(weeks):
    """-> (current streak, longest streak, busiest day)"""
    counts = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    # today may not have a contribution yet; don't let that zero out the streak
    trail = counts[:-1] if counts and counts[-1] == 0 else counts
    cur = 0
    for c in reversed(trail):
        if not c:
            break
        cur += 1
    return cur, longest, max(counts, default=0)
