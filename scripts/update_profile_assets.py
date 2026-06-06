#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


LOGIN = "TiKVaWeb"
ASSETS_DIR = Path("assets")
GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

PYTHON_ICON = (
    "M14.25.18l.9.2.73.26.59.3.45.32.34.34.25.34.16.33.1.3.04.26.02.2-.01.13V8.5l-.05.63-.13.55-.21.46-.26.38-.3.31-.33.25-.35.19-.35.14-.33.1-.3.07-.26.04-.21.02H8.77l-.69.05-.59.14-.5.22-.41.27-.33.32-.27.35-.2.36-.15.37-.1.35-.07.32-.04.27-.02.21v3.06H3.17l-.21-.03-.28-.07-.32-.12-.35-.18-.36-.26-.36-.36-.35-.46-.32-.59-.28-.73-.21-.88-.14-1.05-.05-1.23.06-1.22.16-1.04.24-.87.32-.71.36-.57.4-.44.42-.33.42-.24.4-.16.36-.1.32-.05.24-.01h.16l.06.01h8.16v-.83H6.18l-.01-2.75-.02-.37.05-.34.11-.31.17-.28.25-.26.31-.23.38-.2.44-.18.51-.15.58-.12.64-.1.71-.06.77-.04.84-.02 1.27.05zm-6.3 1.98l-.23.33-.08.41.08.41.23.34.33.22.41.09.41-.09.33-.22.23-.34.08-.41-.08-.41-.23-.33-.33-.22-.41-.09-.41.09zm13.09 3.95l.28.06.32.12.35.18.36.27.36.35.35.47.32.59.28.73.21.88.14 1.04.05 1.23-.06 1.23-.16 1.04-.24.86-.32.71-.36.57-.4.45-.42.33-.42.24-.4.16-.36.09-.32.05-.24.02-.16-.01h-8.22v.82h5.84l.01 2.76.02.36-.05.34-.11.31-.17.29-.25.25-.31.24-.38.2-.44.17-.51.15-.58.13-.64.09-.71.07-.77.04-.84.01-1.27-.04-1.07-.14-.9-.2-.73-.25-.59-.3-.45-.33-.34-.34-.25-.34-.16-.33-.1-.3-.04-.25-.02-.2.01-.13v-5.34l.05-.64.13-.54.21-.46.26-.38.3-.32.33-.24.35-.2.35-.14.33-.1.3-.06.26-.04.21-.02.13-.01h5.84l.69-.05.59-.14.5-.21.41-.28.33-.32.27-.35.2-.36.15-.36.1-.35.07-.32.04-.28.02-.21V6.07h2.09l.14.01zm-6.47 14.25l-.23.33-.08.41.08.41.23.33.33.23.41.08.41-.08.33-.23.23-.33.08-.41-.08-.41-.23-.33-.33-.23-.41-.08-.41.08z"
)
GIT_ICON = (
    "M13.09 23.549a1.54 1.54 0 0 1-2.18 0L.451 13.089a1.54 1.54 0 0 1 0-2.179l7.191-7.19 2.733 2.733a1.85 1.85 0 0 0 .964 2.326v6.66a1.849 1.849 0 1 0 1.54 0V8.957l2.508 2.508a1.85 1.85 0 1 0 1.09-1.09l-2.634-2.634a1.85 1.85 0 0 0-2.378-2.377L8.73 2.63 10.91.451a1.54 1.54 0 0 1 2.179 0l10.459 10.46a1.54 1.54 0 0 1 0 2.179z"
)


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    panel: str
    card: str
    border: str
    text: str
    muted: str
    mono: str
    blue: str
    green: str
    purple: str
    yellow: str
    grid: str
    heatmap: tuple[str, str, str, str, str]


@dataclass(frozen=True)
class Language:
    name: str
    percent: float
    color: str


@dataclass(frozen=True)
class ActivityCount:
    label: str
    value: int
    color: str


@dataclass(frozen=True)
class Day:
    iso_date: str
    count: int
    level: int


@dataclass(frozen=True)
class ProfileData:
    repo_count: int
    commit_count: int
    star_count: int
    follower_count: int
    total_contributions: int
    activities: tuple[ActivityCount, ...]
    languages: tuple[Language, ...]
    weeks: tuple[tuple[Day, ...], ...]
    updated_at: str


PALETTES = {
    "dark": Palette(
        name="dark",
        bg="#0d1117",
        panel="#0d1117",
        card="#161b22",
        border="#30363d",
        text="#f0f6fc",
        muted="#8b949e",
        mono="#58a6ff",
        blue="#58a6ff",
        green="#3fb950",
        purple="#bc8cff",
        yellow="#d29922",
        grid="#21262d",
        heatmap=("#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"),
    ),
    "light": Palette(
        name="light",
        bg="#ffffff",
        panel="#ffffff",
        card="#f6f8fa",
        border="#d0d7de",
        text="#24292f",
        muted="#57606a",
        mono="#0969da",
        blue="#0969da",
        green="#2da44e",
        purple="#8250df",
        yellow="#9a6700",
        grid="#d0d7de",
        heatmap=("#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"),
    ),
}


def compact_number(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m".replace(".0", "")
    if value >= 1_000:
        return f"{value / 1_000:.1f}k".replace(".0", "")
    return str(value)


def full_number(value: int) -> str:
    return f"{value:,}"


def text(value: str) -> str:
    return escape(str(value), {'"': "&quot;"})


def write_svg(path: Path, content: str) -> None:
    lines = (line.rstrip() for line in content.strip().splitlines())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    request = urllib.request.Request(
        GITHUB_GRAPHQL_URL,
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "TiKVaWeb-profile-assets",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        raise RuntimeError(f"GitHub GraphQL request failed: {error.code} {body}") from error

    if errors := result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL returned errors: {errors}")
    return result["data"]


def fetch_profile_data(login: str, token: str) -> ProfileData:
    now = datetime.now(UTC).replace(microsecond=0)
    since = now - timedelta(days=365)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!, $after: String) {
      user(login: $login) {
        followers { totalCount }
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
              }
            }
          }
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
        }
        repositories(
          first: 100,
          after: $after,
          privacy: PUBLIC,
          ownerAffiliations: OWNER,
          orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes {
            stargazerCount
            languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
      }
    }
    """
    variables = {"login": login, "from": since.isoformat(), "to": now.isoformat(), "after": None}
    all_repositories: list[dict[str, Any]] = []
    user: dict[str, Any] | None = None

    while True:
        page = graphql(token, query, variables)["user"]
        if page is None:
            raise RuntimeError(f"GitHub user {login!r} was not found")
        user = page
        repositories = page["repositories"]
        all_repositories.extend(repositories["nodes"])
        if not repositories["pageInfo"]["hasNextPage"]:
            break
        variables["after"] = repositories["pageInfo"]["endCursor"]

    assert user is not None
    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    language_sizes: dict[str, tuple[int, str]] = {}

    for repo in all_repositories:
        for edge in repo["languages"]["edges"]:
            language = edge["node"]["name"]
            color = edge["node"]["color"] or "#8b949e"
            current_size, _ = language_sizes.get(language, (0, color))
            language_sizes[language] = (current_size + int(edge["size"]), color)

    total_language_size = sum(size for size, _ in language_sizes.values()) or 1
    languages = tuple(
        Language(name, round(size / total_language_size * 100, 1), color)
        for name, (size, color) in sorted(language_sizes.items(), key=lambda item: item[1][0], reverse=True)[:4]
    )

    level_map = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
    weeks = tuple(
        tuple(
            Day(
                iso_date=day["date"],
                count=int(day["contributionCount"]),
                level=level_map.get(day["contributionLevel"], 0),
            )
            for day in week["contributionDays"]
        )
        for week in calendar["weeks"]
    )

    commit_count = int(collection["totalCommitContributions"])
    activities = (
        ActivityCount("Commits", commit_count, "#3fb950"),
        ActivityCount("Pull requests", int(collection["totalPullRequestContributions"]), "#58a6ff"),
        ActivityCount("Code review", int(collection["totalPullRequestReviewContributions"]), "#bc8cff"),
        ActivityCount("Issues", int(collection["totalIssueContributions"]), "#d29922"),
    )
    return ProfileData(
        repo_count=int(user["repositories"]["totalCount"]),
        commit_count=commit_count,
        star_count=sum(int(repo["stargazerCount"]) for repo in all_repositories),
        follower_count=int(user["followers"]["totalCount"]),
        total_contributions=int(calendar["totalContributions"]),
        activities=activities,
        languages=languages or (Language("Python", 100.0, "#3572A5"),),
        weeks=weeks,
        updated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
    )


def sample_weeks() -> tuple[tuple[Day, ...], ...]:
    rng = random.Random(7)
    end = date.today()
    start = end - timedelta(days=370)
    start -= timedelta(days=(start.weekday() + 1) % 7)
    weeks: list[tuple[Day, ...]] = []

    for week_index in range(53):
        days: list[Day] = []
        for weekday in range(7):
            current = start + timedelta(days=week_index * 7 + weekday)
            if current > end:
                count = 0
            elif current.month in {6, 7}:
                count = rng.choice([0, 0, 1, 3, 6, 10])
            elif current.month in {8, 9, 10, 11, 12, 1, 2, 3, 4, 5}:
                count = rng.choice([0, 6, 12, 18, 24, 32, 45])
            else:
                count = rng.choice([0, 2, 8, 12])
            level = 0 if count == 0 else min(4, max(1, count // 10 + 1))
            days.append(Day(current.isoformat(), count, level))
        weeks.append(tuple(days))
    return tuple(weeks)


def sample_profile_data() -> ProfileData:
    return ProfileData(
        repo_count=5,
        commit_count=5905,
        star_count=3,
        follower_count=1,
        total_contributions=7770,
        activities=(
            ActivityCount("Commits", 5905, "#3fb950"),
            ActivityCount("Pull requests", 1865, "#58a6ff"),
            ActivityCount("Code review", 0, "#bc8cff"),
            ActivityCount("Issues", 0, "#d29922"),
        ),
        languages=(Language("Python", 96.1, "#3572A5"), Language("Makefile", 3.9, "#427819")),
        weeks=sample_weeks(),
        updated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    )


def render_metric_card(x: int, title: str, value: str, icon: str, palette: Palette) -> str:
    icons = {
        "repo": f'<path d="M3.5 6.5H9L11 9H20.5C21.9 9 23 10.1 23 11.5V18.5C23 19.9 21.9 21 20.5 21H3.5C2.1 21 1 19.9 1 18.5V9C1 7.6 2.1 6.5 3.5 6.5Z" transform="translate(94 20)" stroke="{palette.blue}" stroke-width="2" stroke-linejoin="round"/>',
        "git": f'<path d="{GIT_ICON}" transform="translate(94 20) scale(0.92)" fill="#F05033"/>',
        "star": f'<path d="M12 2.5L14.9 8.7L21.5 9.5L16.6 14L17.9 20.5L12 17.2L6.1 20.5L7.4 14L2.5 9.5L9.1 8.7L12 2.5Z" transform="translate(94 20)" fill="{palette.yellow}"/>',
        "user": f'<path d="M12 12.5A5.5 5.5 0 1 0 12 1.5A5.5 5.5 0 0 0 12 12.5ZM3.5 22C4.7 16.7 7.8 14 12 14C16.2 14 19.3 16.7 20.5 22" transform="translate(94 20)" stroke="{palette.purple}" stroke-width="2" stroke-linecap="round"/>',
    }
    return f"""
    <g transform="translate({x} 78)">
      <rect x="0" y="0" width="132" height="68" rx="12" fill="{palette.card}" stroke="{palette.border}"/>
      <text x="18" y="31" fill="{palette.text}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="26" font-weight="800">{text(value)}</text>
      <text x="18" y="54" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13" font-weight="700">{text(title)}</text>
      {icons[icon]}
    </g>"""


def render_language_tile(x: int, language: Language, palette: Palette) -> str:
    is_python = language.name.lower() == "python"
    label = "Py" if is_python else ("Mk" if language.name.lower() == "makefile" else language.name[:2].title())
    if is_python:
        icon = f"""
      <rect x="18" y="13" width="42" height="36" rx="12" fill="#f6f8fa" stroke="{palette.border}"/>
      <path d="{PYTHON_ICON}" fill="#3776AB" transform="translate(27 20) scale(0.9167)"/>"""
    else:
        icon = f"""
      <rect x="18" y="13" width="42" height="36" rx="12" fill="{language.color}" stroke="{palette.border}"/>
      <text x="30" y="36" fill="#ffffff" font-family="SFMono-Regular, Consolas, Liberation Mono, monospace" font-size="13" font-weight="900">{text(label)}</text>"""

    return f"""
    <g transform="translate({x} 116)">
      <rect x="0" y="0" width="214" height="62" rx="12" fill="{palette.card}" stroke="{palette.border}"/>
      {icon}
      <text x="78" y="27" fill="{palette.text}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="17" font-weight="800">{text(language.name)}</text>
      <text x="78" y="49" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13" font-weight="600">{language.percent:.1f}% public code</text>
    </g>"""


def render_profile_metrics(data: ProfileData, palette: Palette) -> str:
    languages = data.languages[:2]
    first = languages[0]
    second = languages[1] if len(languages) > 1 else Language("Other", max(0.0, 100 - first.percent), palette.muted)
    first_width = max(4, round(448 * first.percent / 100))
    second_width = max(2, 448 - first_width)
    follower_label = "follower" if data.follower_count == 1 else "followers"
    return f"""
<svg width="1200" height="242" viewBox="0 0 1200 242" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">TiKVaWeb GitHub activity signal ({palette.name})</title>
  <desc id="desc">Compact GitHub activity metrics and public repository language mix for TiKVaWeb.</desc>
  <defs>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M32 0H0V32" stroke="{palette.grid}" stroke-opacity="0.42"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="1198" height="240" rx="16" fill="{palette.bg}" stroke="{palette.border}"/>
  <rect x="1" y="1" width="1198" height="240" rx="16" fill="url(#grid)" opacity="0.16"/>
  <g transform="translate(40 34)">
    <text x="0" y="18" fill="{palette.muted}" font-family="SFMono-Regular, Consolas, Liberation Mono, monospace" font-size="14" font-weight="700">activity.runtime</text>
    <text x="0" y="52" fill="{palette.mono}" font-family="SFMono-Regular, Consolas, Liberation Mono, monospace" font-size="18" font-weight="800">$ gh signal --compact</text>
    {render_metric_card(0, "repos", compact_number(data.repo_count), "repo", palette)}
    {render_metric_card(152, "commits", compact_number(data.commit_count), "git", palette)}
    {render_metric_card(304, "stars", compact_number(data.star_count), "star", palette)}
    {render_metric_card(456, follower_label, compact_number(data.follower_count), "user", palette)}
    <text x="0" y="178" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="16" font-weight="600">backend platforms / product architecture / reliable delivery</text>
  </g>
  <path d="M650 42V201" stroke="{palette.border}"/>
  <g transform="translate(690 34)">
    <text x="0" y="18" fill="{palette.muted}" font-family="SFMono-Regular, Consolas, Liberation Mono, monospace" font-size="14" font-weight="700">language.mix</text>
    <text x="0" y="52" fill="{palette.text}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="24" font-weight="800">Python-heavy public code</text>
    <rect x="0" y="74" width="450" height="14" rx="7" fill="{palette.card}" stroke="{palette.border}"/>
    <rect x="1" y="75" width="{first_width}" height="12" rx="6" fill="{first.color}"/>
    <rect x="{1 + first_width}" y="75" width="{second_width}" height="12" rx="6" fill="{second.color}"/>
    {render_language_tile(0, first, palette)}
    {render_language_tile(236, second, palette)}
  </g>
</svg>"""


def render_activity_bar(y: int, activity: ActivityCount, total: int, palette: Palette) -> str:
    percent = 0 if total == 0 else activity.value / total * 100
    width = round(310 * percent / 100)
    return f"""
    <g transform="translate(0 {y})">
      <text x="0" y="14" fill="{palette.text}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14" font-weight="800">{text(activity.label)}</text>
      <text x="260" y="14" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13" font-weight="700" text-anchor="end">{percent:.0f}%</text>
      <rect x="0" y="24" width="310" height="9" rx="4.5" fill="{palette.card}" stroke="{palette.border}"/>
      <rect x="1" y="25" width="{max(3, width)}" height="7" rx="3.5" fill="{activity.color}"/>
    </g>"""


def month_labels(weeks: tuple[tuple[Day, ...], ...], cell: int, gap: int) -> str:
    labels: list[str] = []
    seen: set[tuple[int, int]] = set()
    for week_index, week in enumerate(weeks):
        if not week:
            continue
        parsed = date.fromisoformat(week[0].iso_date)
        key = (parsed.year, parsed.month)
        if key in seen or parsed.day > 7:
            continue
        seen.add(key)
        labels.append(
            f'<text x="{week_index * (cell + gap)}" y="0" fill="currentColor" '
            f'font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14" font-weight="700">'
            f'{parsed.strftime("%b")}</text>'
        )
    return "\n".join(labels)


def render_activity_overview(data: ProfileData, palette: Palette) -> str:
    cell = 10
    gap = 4
    heatmap_rows: list[str] = []
    for week_index, week in enumerate(data.weeks[-53:]):
        for weekday, day in enumerate(week):
            heatmap_rows.append(
                f'<rect x="{week_index * (cell + gap)}" y="{weekday * (cell + gap)}" '
                f'width="{cell}" height="{cell}" rx="3" fill="{palette.heatmap[day.level]}">'
                f'<title>{text(day.iso_date)}: {day.count} contributions</title></rect>'
            )

    activities_total = sum(activity.value for activity in data.activities)
    bars = "\n".join(render_activity_bar(index * 45, activity, activities_total, palette) for index, activity in enumerate(data.activities))
    legend = "".join(
        f'<rect x="{index * 20}" y="0" width="14" height="14" rx="3" fill="{color}"/>'
        for index, color in enumerate(palette.heatmap)
    )

    return f"""
<svg width="1200" height="342" viewBox="0 0 1200 342" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">TiKVaWeb contribution activity ({palette.name})</title>
  <desc id="desc">Custom contribution calendar and activity overview for TiKVaWeb.</desc>
  <defs>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M32 0H0V32" stroke="{palette.grid}" stroke-opacity="0.42"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="1198" height="340" rx="16" fill="{palette.bg}" stroke="{palette.border}"/>
  <rect x="1" y="1" width="1198" height="340" rx="16" fill="url(#grid)" opacity="0.13"/>
  <g transform="translate(40 34)">
    <text x="0" y="18" fill="{palette.muted}" font-family="SFMono-Regular, Consolas, Liberation Mono, monospace" font-size="14" font-weight="700">contribution.graph</text>
    <text x="0" y="54" fill="{palette.text}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="30" font-weight="850">{full_number(data.total_contributions)} contributions</text>
    <text x="342" y="54" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="18" font-weight="700">last 12 months</text>
    <g transform="translate(0 94)" color="{palette.muted}">
      {month_labels(data.weeks[-53:], cell, gap)}
    </g>
    <g transform="translate(0 116)">
      {''.join(heatmap_rows)}
    </g>
    <text x="0" y="268" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="14" font-weight="700">updated {text(data.updated_at)}</text>
    <g transform="translate(610 254)">
      <text x="0" y="12" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13" font-weight="700">Less</text>
      <g transform="translate(37 0)">{legend}</g>
      <text x="147" y="12" fill="{palette.muted}" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="13" font-weight="700">More</text>
    </g>
  </g>
  <path d="M838 44V299" stroke="{palette.border}"/>
  <g transform="translate(884 52)">
    <text x="0" y="18" fill="{palette.muted}" font-family="SFMono-Regular, Consolas, Liberation Mono, monospace" font-size="14" font-weight="700">activity.mix</text>
    <text x="0" y="50" fill="{palette.mono}" font-family="SFMono-Regular, Consolas, Liberation Mono, monospace" font-size="17" font-weight="800">$ gh overview --year</text>
    <g transform="translate(0 80)">
      {bars}
    </g>
  </g>
</svg>"""


def render_all(data: ProfileData) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for name, palette in PALETTES.items():
        write_svg(ASSETS_DIR / f"profile-metrics-{name}-v1.svg", render_profile_metrics(data, palette))
        write_svg(ASSETS_DIR / f"activity-overview-{name}-v1.svg", render_activity_overview(data, palette))


def main() -> int:
    parser = argparse.ArgumentParser(description="Render TiKVaWeb GitHub profile SVG assets.")
    parser.add_argument("--login", default=os.environ.get("PROFILE_LOGIN", LOGIN))
    parser.add_argument("--sample", action="store_true", help="Render deterministic sample data without GitHub API access.")
    args = parser.parse_args()

    if args.sample:
        data = sample_profile_data()
    else:
        token = os.environ.get("GH_PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GH_PROFILE_TOKEN or GITHUB_TOKEN is required unless --sample is used.")
        data = fetch_profile_data(args.login, token)

    render_all(data)
    print(f"Rendered profile assets for {args.login}: {data.total_contributions} contributions")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
