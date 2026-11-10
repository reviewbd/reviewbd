import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

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
        r'(<tspan\b(?=[^>]*\bid="' + re.escape(element_id) + r'")[^>]*>).*?(</tspan>)',
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
now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""
graphql_payload = {
    "query": query,
    "variables": {
        "login": USER,
        "from": "2000-01-01T00:00:00Z",
        "to": now,
    },
}

try:
    graphql = request_json(
        "https://api.github.com/graphql",
        method="POST",
        payload=graphql_payload,
        headers={**HEADERS, "Content-Type": "application/json"},
    )
    if graphql.get("errors"):
        raise RuntimeError("; ".join(e.get("message", "unknown") for e in graphql["errors"]))
    user = graphql.get("data", {}).get("user")
    if not user:
        raise RuntimeError("GitHub returned no contribution data")
    collection = user["contributionsCollection"]
    commits = collection.get("totalCommitContributions", 0)
    contributions = collection.get("contributionCalendar", {}).get("totalContributions", 0)
    private_activity = collection.get("restrictedContributionsCount", 0)
except Exception as error:
    if PROFILE_TOKEN:
        raise RuntimeError(f"Could not read contribution data with PROFILE_TOKEN: {error}") from error
    print(f"GraphQL unavailable; using public commit search only: {error}", file=sys.stderr)
    search = request_json(
        f"https://api.github.com/search/commits?q=author:{USER}&per_page=1",
        headers={**HEADERS, "Accept": "application/vnd.github+json"},
    )
    commits = search.get("total_count", 0)
    contributions = commits
    private_activity = "add PROFILE_TOKEN"

if not PROFILE_TOKEN:
    private_activity = "add PROFILE_TOKEN"

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

print("Updated ReviewB GitHub statistics:", stats)
