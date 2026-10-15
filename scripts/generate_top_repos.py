
import html
import os
from collections import defaultdict
from datetime import datetime, timezone

import requests

USERNAME = "Vorpalin"
OUTPUT = "profile/top-contributed.svg"
TOKEN = os.environ["PROFILE_STATS_TOKEN"]

API_URL = "https://api.github.com/graphql"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

def graphql(query):
    response = requests.post(
        API_URL,
        headers=HEADERS,
        json={"query": query},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])

    return data["data"]


def fetch_top_repositories():
    user_query = f"""
    {{
      user(login: "{USERNAME}") {{
        contributionsCollection {{
          contributionYears
        }}
      }}
    }}
    """

    user = graphql(user_query)["user"]
    if user is None:
        raise RuntimeError(f"GitHub user {USERNAME} not found")

    years = user["contributionsCollection"]["contributionYears"]
    totals = defaultdict(int)
    repositories = {}

    for year in years:
        query = f"""
        {{
          user(login: "{USERNAME}") {{
            contributionsCollection(
              from: "{year}-01-01T00:00:00Z"
              to: "{year}-12-31T23:59:59Z"
            ) {{
              commitContributionsByRepository(maxRepositories: 100) {{
                contributions {{
                  totalCount
                }}
                repository {{
                  nameWithOwner
                  url
                }}
              }}
            }}
          }}
        }}
        """

        collection = graphql(query)["user"]["contributionsCollection"]

        for item in collection["commitContributionsByRepository"]:
            repo = item["repository"]
            name = repo["nameWithOwner"]

            totals[name] += item["contributions"]["totalCount"]
            repositories[name] = repo["url"]

    return sorted(
        totals.items(),
        key=lambda item: (-item[1], item[0].lower()),
    )[:5], repositories


def generate_svg(top, repositories):
    width = 650
    row_height = 58
    height = 100 + row_height * max(len(top), 1)

    rows = []

    for index, (name, count) in enumerate(top, start=1):
        y = 90 + (index - 1) * row_height
        safe_name = html.escape(name)
        safe_url = html.escape(repositories[name], quote=True)

        rows.append(f"""
        <a href="{safe_url}" target="_blank">
          <text x="28" y="{y}" class="rank">#{index}</text>
          <text x="78" y="{y}" class="repo">{safe_name}</text>
          <text x="620" y="{y}" text-anchor="end" class="count">
            {count:,} commits
          </text>
        </a>
        <line x1="24" y1="{y + 17}" x2="626" y2="{y + 17}"
              stroke="#30363d"/>
        """)

    if not rows:
        rows.append(
            '<text x="28" y="90" class="repo">'
            'No contributions found</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
      width="{width}" height="{height}" viewBox="0 0 {width} {height}">
      <style>
        text {{ font-family: Arial, sans-serif; }}
        .title {{ font-size: 22px; font-weight: bold; fill: #e6edf3; }}
        .subtitle {{ font-size: 12px; fill: #8b949e; }}
        .rank {{ font-size: 15px; font-weight: bold; fill: #a371f7; }}
        .repo {{ font-size: 14px; fill: #e6edf3; }}
        .count {{ font-size: 13px; fill: #8b949e; }}
        a {{ text-decoration: none; }}
      </style>
      <rect width="100%" height="100%" rx="12"
            fill="#0d1117" stroke="#30363d"/>
      <text x="24" y="34" class="title">
        Top Contributed Repositories
      </text>
      <text x="24" y="57" class="subtitle">
        @{USERNAME} · All available contribution years
      </text>
      {''.join(rows)}
    </svg>
    """

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as file:
        file.write(svg)


if __name__ == "__main__":
    top, repositories = fetch_top_repositories()
    generate_svg(top, repositories)
    print(f"Generated {OUTPUT} at "
          f"{datetime.now(timezone.utc).isoformat()}")

