import json, os, re, urllib.request

USER = "reviewbd"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
if TOKEN:
    headers["Authorization"] = f"Bearer {TOKEN}"

def get(url):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

profile = get(f"https://api.github.com/users/{USER}")
repos = []
page = 1
while True:
    batch = get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}&type=owner")
    if not batch:
        break
    repos.extend(batch)
    if len(batch) < 100:
        break
    page += 1

public_repos = [r for r in repos if not r.get("fork")]
stars = sum(r.get("stargazers_count", 0) for r in repos)
forks = sum(r.get("forks_count", 0) for r in repos)
commit_search = get(f"https://api.github.com/search/commits?q=author:{USER}&per_page=1")
stats = {
    "{{repos}}": str(profile.get("public_repos", len(repos))),
    "{{stars}}": str(stars),
    "{{commits}}": str(commit_search.get("total_count", 0)),
    "{{followers}}": str(profile.get("followers", 0)),
    "{{forks}}": str(forks),
}
for path in ("assets/terminal.svg", "assets/terminal-light.svg"):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    for key, value in stats.items():
        content = content.replace(key, value)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
print("Updated GitHub profile statistics:", stats)
