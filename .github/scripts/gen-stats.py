"""Fetch the public GitHub stats card for the profile README."""

import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from xml.etree import ElementTree


def validate_card(card, username):
    root = ElementTree.fromstring(card)
    svg = "{http://www.w3.org/2000/svg}"
    title = root.findtext(f"{svg}title") or ""
    if root.tag != f"{svg}svg" or not title.startswith(f"{username}'s GitHub Stats"):
        raise ValueError("The public stats service did not return the user's stats card")
    for field in ("stars", "commits", "prs", "reviews", "issues", "contribs"):
        value = root.findtext(f".//{svg}text[@data-testid='{field}']")
        if not value or not value.strip():
            raise ValueError(f"The public stats card is missing the {field} total")


if __name__ == "__main__":
    username = os.environ["GITHUB_REPOSITORY_OWNER"]
    options = urlencode({
        "username": username,
        "rank_icon": "default",
        "show_icons": "true",
        "show": "reviews",
        "include_all_commits": "true",
        "bg_color": "30,e96443,904e95",
        "title_color": "fff",
        "text_color": "fff",
    })
    with urlopen(f"https://github-readme-stats.vercel.app/api?{options}", timeout=30) as response:
        card = response.read()
    validate_card(card, username)
    lines = (line.rstrip() for line in card.strip().splitlines())
    Path("profile/stats.svg").write_bytes(b"\n".join(lines) + b"\n")
