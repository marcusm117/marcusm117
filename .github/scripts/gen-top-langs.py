"""Generate a top-languages donut chart SVG matching github-readme-stats style.

Queries ALL repos the user has access to (personal, org, collaborator)
via the GitHub GraphQL API, unlike the default action which only fetches
personal repos (ownerAffiliations: OWNER).
"""

import json, math, os, urllib.request

# --- Config (mirrors the workflow options) ---
USERNAME = os.environ["GITHUB_REPOSITORY_OWNER"]
TOKEN = os.environ["STATS_TOKEN"]
OUTPUT = os.environ.get("OUTPUT_PATH", "profile/top-langs.svg")
HIDE = {"Makefile", "HTML"}
LANGS_COUNT = 5
SIZE_WEIGHT = 0.5
COUNT_WEIGHT = 0.5
FALLBACK_COLOR = "#858585"

# Explicit colors for languages missing from GitHub Linguist.
# Add entries here as needed.
LANG_COLORS = {
    "Lean": "#858585",
}

# --- Fetch language data from GitHub GraphQL API ---
QUERY = """
query userInfo($login: String!) {
  user(login: $login) {
    repositories(
      ownerAffiliations: [OWNER, ORGANIZATION_MEMBER, COLLABORATOR]
      isFork: false
      first: 100
    ) {
      nodes {
        name
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { color, name }
          }
        }
      }
    }
  }
}
"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode(),
    headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

repos = data["data"]["user"]["repositories"]["nodes"]

# --- Aggregate languages across repos ---
langs = {}
for repo in repos:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        if name in HIDE:
            continue
        color = edge["node"]["color"] or LANG_COLORS.get(name, FALLBACK_COLOR)
        if name in langs:
            langs[name]["size"] += edge["size"]
            langs[name]["count"] += 1
        else:
            langs[name] = {"name": name, "color": color, "size": edge["size"], "count": 1}

# Fix any remaining null colors
for l in langs.values():
    if not l["color"]:
        l["color"] = LANG_COLORS.get(l["name"], FALLBACK_COLOR)

# Weighted score: size^size_weight * count^count_weight
# (same formula as github-readme-stats)
for l in langs.values():
    l["score"] = math.pow(l["size"], SIZE_WEIGHT) * math.pow(l["count"], COUNT_WEIGHT)

top = sorted(langs.values(), key=lambda x: x["score"], reverse=True)[:LANGS_COUNT]
total = sum(l["score"] for l in top)
for l in top:
    l["pct"] = l["score"] / total * 100

# --- SVG generation ---
CX = CY = 116.66666666666667
R = 56.66666666666667
START_ANGLE = 270  # SVG degrees, 12 o'clock


def point(deg):
    rad = math.radians(deg)
    return CX + R * math.cos(rad), CY + R * math.sin(rad)


# Cumulative angles going clockwise from 12 o'clock
angles = [START_ANGLE]
for l in top:
    angles.append(angles[-1] + l["pct"] / 100 * 360)

# Legend items
legend_items = []
for i, l in enumerate(top):
    legend_items.append(
        f'<g transform="translate(0, {i * 32})">\n'
        f'    <g class="stagger" style="animation-delay: {450 + i * 150}ms">\n'
        f'      <circle cx="5" cy="6" r="5" fill="{l["color"]}" />\n'
        f"      <text data-testid=\"lang-name\" x=\"15\" y=\"10\" class='lang-name'>\n"
        f'        {l["name"]} {l["pct"]:.2f}%\n'
        f"      </text>\n"
        f"    </g>\n"
        f"  </g>"
    )

# Donut arcs (drawn counterclockwise from segment end to start, sweep=0)
arc_items = []
for i, l in enumerate(top):
    span = l["pct"] / 100 * 360
    large = 1 if span > 180 else 0
    sx, sy = point(angles[i + 1])  # arc M (moveto) = segment end
    ex, ey = point(angles[i])      # arc target = segment start
    arc_items.append(
        f'   <g class="stagger" style="animation-delay: {600 + i * 100}ms">\n'
        f"        <path\n"
        f'          data-testid="lang-donut"\n'
        f'          size="{l["pct"]:.2f}"\n'
        f'          d="M {sx} {sy} A {R} {R} 0 {large} 0 {ex} {ey}"\n'
        f'          stroke="{l["color"]}"\n'
        f'          fill="none"\n'
        f'          stroke-width="12">\n'
        f"        </path>\n"
        f"      </g>"
    )

svg = f"""\
      <svg
        width="350"
        height="215"
        viewBox="0 0 350 215"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        role="img"
        aria-labelledby="descId"
      >
        <title id="titleId"></title>
        <desc id="descId"></desc>
        <style>
          .header {{
            font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif;
            fill: #7957d5;
            animation: fadeInAnimation 0.8s ease-in-out forwards;
          }}
          @supports(-moz-appearance: auto) {{
            /* Selector detects Firefox */
            .header {{ font-size: 15.5px; }}
          }}

    @keyframes slideInAnimation {{
      from {{
        width: 0;
      }}
      to {{
        width: calc(100%-100px);
      }}
    }}
    @keyframes growWidthAnimation {{
      from {{
        width: 0;
      }}
      to {{
        width: 100%;
      }}
    }}
    .stat {{
      font: 600 14px 'Segoe UI', Ubuntu, "Helvetica Neue", Sans-Serif; fill: #363636;
    }}
    @supports(-moz-appearance: auto) {{
      /* Selector detects Firefox */
      .stat {{ font-size:12px; }}
    }}
    .bold {{ font-weight: 700 }}
    .lang-name {{
      font: 400 11px "Segoe UI", Ubuntu, Sans-Serif;
      fill: #363636;
    }}
    .stagger {{
      opacity: 0;
      animation: fadeInAnimation 0.3s ease-in-out forwards;
    }}
    #rect-mask rect{{
      animation: slideInAnimation 1s ease-in-out forwards;
    }}
    .lang-progress{{
      animation: growWidthAnimation 0.6s ease-in-out forwards;
    }}



      /* Animations */
      @keyframes scaleInAnimation {{
        from {{
          transform: translate(-5px, 5px) scale(0);
        }}
        to {{
          transform: translate(-5px, 5px) scale(1);
        }}
      }}
      @keyframes fadeInAnimation {{
        from {{
          opacity: 0;
        }}
        to {{
          opacity: 1;
        }}
      }}


        </style>



        <rect
          data-testid="card-bg"
          x="0.5"
          y="0.5"
          rx="4.5"
          height="99%"
          stroke="#e4e2e2"
          width="349"
          fill="#ffffff"
          stroke-opacity="1"
        />


      <g
        data-testid="card-title"
        transform="translate(25, 35)"
      >
        <g transform="translate(0, 0)">
      <text
        x="0"
        y="0"
        class="header"
        data-testid="header"
      >Most Used Languages</text>
    </g>
      </g>


        <g
          data-testid="main-card-body"
          transform="translate(0, 55)"
        >

    <svg data-testid="lang-items" x="25">

    <g transform="translate(0, 0)">
      <g transform="translate(0, 0)">
        {"".join(legend_items)}
      </g>

      <g transform="translate(125, -45)">
        <svg width="350" height="350">
      {"".join(arc_items)}
      </svg>
      </g>
    </g>

    </svg>

        </g>
      </svg>
    """

with open(OUTPUT, "w") as f:
    f.write(svg)

print(f"Generated {OUTPUT} with {len(top)} languages:")
for l in top:
    print(f"  {l['name']:15s} {l['pct']:.2f}%  ({l['color']})")
