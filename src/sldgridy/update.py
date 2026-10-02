"""Checks GitHub for a newer release. Pure Python apart from the network call."""

import json
import re
import urllib.request
from dataclasses import dataclass

from sldgridy.project import API_LATEST, LATEST_RELEASE_URL

TIMEOUT = 10  # seconds


@dataclass(frozen=True)
class UpdateResult:
    ok: bool
    available: bool = False
    version: str = ""
    release_url: str = LATEST_RELEASE_URL
    download_url: str | None = None


def parse_version(text: str) -> tuple[int, ...]:
    numbers = re.findall(r"\d+", text)
    return tuple(int(n) for n in numbers[:3]) if numbers else ()


def evaluate(current: str, release: dict) -> UpdateResult:
    """Compare the running version with a GitHub release JSON object."""
    tag = str(release.get("tag_name", ""))
    latest = parse_version(tag)
    if not latest:
        return UpdateResult(ok=False)
    download = None
    for asset in release.get("assets", []):
        name = str(asset.get("name", ""))
        if name.endswith("_all.deb"):
            download = asset.get("browser_download_url")
            break
    return UpdateResult(
        ok=True,
        available=latest > parse_version(current),
        version=tag.lstrip("v"),
        release_url=str(release.get("html_url") or LATEST_RELEASE_URL),
        download_url=download,
    )


def check(current: str) -> UpdateResult:
    request = urllib.request.Request(
        API_LATEST,
        headers={"Accept": "application/vnd.github+json", "User-Agent": f"SLDGridy/{current}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            release = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError):
        return UpdateResult(ok=False)
    if not isinstance(release, dict):
        return UpdateResult(ok=False)
    return evaluate(current, release)
