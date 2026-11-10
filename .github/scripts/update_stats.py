import json
import os
import re
import urllib.request

USER = "reviewbd"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def github_get(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)

def replace_svg_value(content, element_id, value):
    pattern = re.compile(
        r'(<tspan\\b[^>]*\\bid="' + re.escape(element_id) + r'"[^>]*>).*?(</tspan>)',
        re.DOTALL,
    )
    updated, count = pattern.subn(lambda match: match.group(1) + str(value) + match.group(2), content, count=1)
    if count != 1:
        raise RuntimeError(f"Could not find SVG field: {element_id}")
    return updated

profile = github_get(f"https://api.github.com/users/{USER}")
repositories = []
page = 1
while True:
    batch = github_get(
        f"https://api.github.com/users/{USER}/repos?type=owner&per_page=100&page={page}"
    )
    if not batch:
        break
    repositories.extend(batch)
    if len(batch) < 100:
        break
    page += 1

stars = sum(repo.get("stargazers_count", 0) for repo in repositories)
forks = sum(repo.get("forks_count", 0) for repo in repositories)
commits = github_get(
    f"https://api.github.com/search/commits?q=author:{USER}&per_page=1"
).get("total_count", 0)

stats = {
    "repo_data": profile.get("public_repos", len(repositories)),
    "star_data": stars,
    "commit_data": commits,
    "follower_data": profile.get("followers", 0),
    "fork_data": forks,
}

for path in ("assets/terminal.svg", "assets/terminal-light.svg"):
    with open(path, encoding="utf-8") as file:
        content = file.read()
    for element_id, value in stats.items():
        content = replace_svg_value(content, element_id, f"{value:,}")
    with open(path, "w", encoding="utf-8") as file:
        file.write(content)

print("Updated GitHub profile statistics:", stats)
