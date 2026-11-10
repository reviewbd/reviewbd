"""Fetch reviewbd's own GitHub contribution calendar for the animated board."""
import json
import os
import urllib.request
from pathlib import Path

LOGIN = os.environ.get("GH_LOGIN", "reviewbd")
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
QUERY = """
query($login:String!) {
  user(login:$login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date weekday contributionCount contributionLevel }
        }
      }
    }
  }
}
"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

if not TOKEN:
    raise SystemExit("PROFILE_TOKEN or GITHUB_TOKEN is required")

body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=body,
    headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=30) as response:
    payload = json.load(response)

if payload.get("errors"):
    raise SystemExit(json.dumps(payload["errors"], indent=2))

calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = []
for week in calendar["weeks"]:
    slots = [None] * 7
    for day in week["contributionDays"]:
        slots[day["weekday"]] = {
            "date": day["date"],
            "count": day["contributionCount"],
            "level": LEVELS[day["contributionLevel"]],
        }
    weeks.append(slots)

out = Path("cache/calendar.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps({"total": calendar["totalContributions"], "weeks": weeks}, indent=1), encoding="utf-8")
print(f"Fetched {len(weeks)} weeks and {calendar['totalContributions']:,} contributions for {LOGIN}")
