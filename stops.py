"""
osm_bus_stops_with_lines.py

Fetch all bus stops in a city and write a JSON file where each stop includes
a "lines" array listing the bus routes that actually reference that stop in OSM.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

import requests

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {
    "User-Agent": "osm-bus-stops-with-lines.py/1.0 (personal script)",
    "Accept": "application/json",
}

VALID_STOP_ROLES = {
    "stop",
    "platform",
    "stop_entry_only",
    "stop_exit_only",
    "platform_entry_only",
    "platform_exit_only",
}


def _escape_ql_string(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "city"


def _run_query(query: str) -> dict[str, Any]:
    response = requests.post(
        OVERPASS_URL,
        data={"data": query},
        headers=HEADERS,
        timeout=180,
    )

    if not response.ok:
        raise RuntimeError(
            f"Overpass HTTP {response.status_code}: {response.text[:500]}"
        )

    return response.json()


def _city_area_block(city: str) -> str:
    city_q = _escape_ql_string(city)
    return f"""
[out:json][timeout:120];
rel["boundary"="administrative"]["name"="{city_q}"]["admin_level"="8"];
map_to_area -> .searchArea;
"""


def get_bus_stops(city: str) -> dict[int, dict[str, Any]]:
    """
    Fetch all bus-stop-related nodes in the city.

    Returns a dict keyed by OSM node id.
    """
    query = _city_area_block(city) + """
(
  node["highway"="bus_stop"](area.searchArea);
  node["public_transport"="platform"](area.searchArea);
  node["public_transport"="stop_position"](area.searchArea);
);
out body;
"""

    data = _run_query(query)
    elements = data.get("elements", [])

    stops: dict[int, dict[str, Any]] = {}

    for el in elements:
        if el.get("type") != "node":
            continue

        tags = el.get("tags", {})
        stop_id = el.get("id")
        if stop_id is None:
            continue

        stop_kind = ""
        if tags.get("highway") == "bus_stop":
            stop_kind = "bus_stop"
        elif tags.get("public_transport") == "platform":
            stop_kind = "platform"
        elif tags.get("public_transport") == "stop_position":
            stop_kind = "stop_position"

        stops[stop_id] = {
            "id": stop_id,
            "lat": el.get("lat"),
            "lon": el.get("lon"),
            "name": tags.get("name", ""),
            "ref": tags.get("ref", ""),
            "kind": stop_kind,
            "lines": [],
        }

    return stops


def get_bus_line_mapping(city: str) -> dict[int, list[dict[str, Any]]]:
    """
    Build mapping from stop node id -> list of bus line objects.

    This reads route relation members directly, which is the correct way to
    associate a stop with its routes in OSM.
    """
    query = _city_area_block(city) + """
relation["type"="route"]["route"="bus"](area.searchArea);
out body;
"""

    data = _run_query(query)
    elements = data.get("elements", [])

    stop_to_lines: dict[int, list[dict[str, Any]]] = defaultdict(list)
    seen: dict[int, set[tuple[Any, ...]]] = defaultdict(set)

    for el in elements:
        if el.get("type") != "relation":
            continue

        tags = el.get("tags", {})
        line = {
            "id": el.get("id"),
            "name": tags.get("name", ""),
            "ref": tags.get("ref", ""),
            "operator": tags.get("operator", ""),
            "from": tags.get("from", ""),
            "to": tags.get("to", ""),
            "colour": tags.get("colour", ""),
            "direction": tags.get("direction", ""),
        }

        members = el.get("members", [])
        for member in members:
            if member.get("type") != "node":
                continue

            role = member.get("role", "")
            if role not in VALID_STOP_ROLES:
                continue

            stop_id = member.get("ref")
            if stop_id is None:
                continue

            signature = (
                line["id"],
                line["ref"],
                line["name"],
                line["operator"],
                line["from"],
                line["to"],
                line["colour"],
                line["direction"],
            )

            if signature in seen[stop_id]:
                continue

            seen[stop_id].add(signature)
            stop_to_lines[stop_id].append(line)

    return stop_to_lines


def build_city_bus_stops_with_lines(city: str) -> list[dict[str, Any]]:
    stops = get_bus_stops(city)
    stop_to_lines = get_bus_line_mapping(city)

    for stop_id, stop in stops.items():
        stop["lines"] = stop_to_lines.get(stop_id, [])

    return list(stops.values())


if __name__ == "__main__":
    city = input("Enter city name: ").strip()
    if not city:
        raise SystemExit("City name cannot be empty.")

    print(f"Fetching bus stops with lines for {city!r}...")

    data = build_city_bus_stops_with_lines(city)
    filename = f"{_slugify(city)}_bus_stops_with_lines.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(data)} stops to {filename}")
    print(json.dumps(data[:3], indent=2, ensure_ascii=False))