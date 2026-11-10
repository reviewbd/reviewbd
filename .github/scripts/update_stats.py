import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

USER = "reviewbd"
PROFILE_TOKEN = os.environ.get("PROFILE_TOKEN", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
TOKEN = PROFILE_TOKEN or GITHUB_TOKEN

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def request_json(url, method="GET", payload=None, headers=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers or HEADERS,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def replace_svg_value(content, element_id, value):
    pattern = re.compile(
        r'(<tspan[^>]*id="' + re.escape(element_id) + r'"[^>]*>).*?(</tspan>)',
        re.DOTALL,
    )
    updated, count = pattern.subn(
        lambda match: match.group(1) + str(value) + match.group(2),
        content,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"SVG field not found exactly once: {element_id}")
    return updated


profile = request_json(f"https://api.github.com/users/{USER}")
repositories = []
page = 1
while True:
    batch = request_json(
        f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"
    )
    if not batch:
        break
    repositories.extend(batch)
    if len(batch) < 100:
        break
    page += 1

stars = sum(repo.get("stargazers_count", 0) for repo in repositories)
now = datetime.now(timezone.utc).replace(microsecond=0)
created = datetime.fromisoformat(profile["created_at"].replace("Z", "+00:00"))
start = created.replace(hour=0, minute=0, second=0, microsecond=0)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to, includePrivateContributions: true) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""

# GitHub limits each contributionsCollection query to a maximum one-year window.
# Use 364-day windows to safely cover the account's full history without gaps.
commits = 0
contributions = 0
private_activity = 0
window_count = 0
cursor = start

while cursor < now:
    window_end = min(cursor + timedelta(days=364), now)
    graphql_payload = {
        "query": query,
        "variables": {
            "login": USER,
            "from": cursor.isoformat().replace("+00:00", "Z"),
            "to": window_end.isoformat().replace("+00:00", "Z"),
        },
    }
    graphql = request_json(
        "https://api.github.com/graphql",
        method="POST",
        payload=graphql_payload,
        headers={**HEADERS, "Content-Type": "application/json"},
    )
    if graphql.get("errors"):
        messages = "; ".join(e.get("message", "unknown") for e in graphql["errors"])
        raise RuntimeError(f"GitHub GraphQL error for {cursor.date()}–{window_end.date()}: {messages}")

    user = graphql.get("data", {}).get("user")
    if not user:
        raise RuntimeError("GitHub returned no contribution data; check PROFILE_TOKEN access.")

    collection = user["contributionsCollection"]
    commits += collection.get("totalCommitContributions", 0)
    contributions += collection.get("contributionCalendar", {}).get("totalContributions", 0)
    private_activity += collection.get("restrictedContributionsCount", 0)
    window_count += 1
    cursor = window_end

stats = {
    "repo_data": profile.get("public_repos", len(repositories)),
    "star_data": stars,
    "commit_data": commits,
    "private_data": private_activity,
    "contribution_data": contributions,
    "follower_data": profile.get("followers", 0),
}

for path in ("assets/terminal.svg", "assets/terminal-light.svg"):
    with open(path, encoding="utf-8") as file:
        content = file.read()
    for element_id, value in stats.items():
        rendered = f"{value:,}" if isinstance(value, int) else value
        content = replace_svg_value(content, element_id, rendered)
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)

print(f"Updated ReviewB statistics across {window_count} yearly windows: {stats}")
