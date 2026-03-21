"""
Seeding (balizamento) logic.

build_series(event, students) → list of series.

Each series is a list of Student-or-None entries of length event.athletes_per_series.
Position in the list = lane number (0-indexed).

Rules:
  1. Students eligible for this event are all passed-in students.
  2. No student swims twice in the same event.
  3. For mixed-year groups (e.g. "6º e 7º Ano") lanes alternate by school year.
  4. The series that starts first in one heat is inverted in the next heat.
  5. Fallback: if one year runs out, fill remaining lanes with the other year.
"""

from __future__ import annotations
from typing import Optional
from models import Student


# Groups that are considered "single-year" (no alternation needed)
_SINGLE_YEAR_GROUPS = {"ensino medio", "ensino médio"}

COMPETITION_GROUPS = [
    "6º e 7º Ano",
    "8º e 9º Ano",
    "Ensino Médio",
]

# Map each school_year to its canonical group
YEAR_TO_GROUP: dict[str, str] = {
    "6º Ano": "6º e 7º Ano",
    "7º Ano": "6º e 7º Ano",
    "8º Ano": "8º e 9º Ano",
    "9º Ano": "8º e 9º Ano",
    "1º Ano Médio": "Ensino Médio",
    "2º Ano Médio": "Ensino Médio",
    "3º Ano Médio": "Ensino Médio",
}


def _normalize(s: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def build_series(
    event,
    students: list[Student],
    event_group: Optional[str] = None
) -> list[list[Optional[Student]]]:
    """
    Distribute students across event.num_series heats, each with
    event.athletes_per_series lanes.

    Returns a list of series; each series is a list of Student|None.
    """
    num_series = max(1, event.num_series or 1)
    athletes_per_series = max(1, event.athletes_per_series or 8)
    group = event_group if event_group is not None else (event.competition_group or "")

    # Bucket students by year (preserving insertion order)
    from collections import defaultdict
    buckets: dict[str, list[Student]] = defaultdict(list)
    for s in students:
        buckets[s.school_year].append(s)

    # Determine year ordering inside this group
    group_years = [y for y in _year_order_for_group(group) if y in buckets]

    # Pool of remaining students — use deque for efficient popleft
    from collections import deque
    pools: dict[str, deque[Student]] = {y: deque(buckets[y]) for y in group_years}

    is_single = _normalize(group) in _SINGLE_YEAR_GROUPS or len(group_years) <= 1

    all_series: list[list[Optional[Student]]] = []

    if is_single:
        combined = _merge_pools(pools, group_years)

    for series_idx in range(num_series):
        series: list[Optional[Student]] = []

        if is_single:
            # No alternation — just pull from the combined pool in order
            for _ in range(athletes_per_series):
                series.append(combined.popleft() if combined else None)
        else:
            # Alternating: even series start with group_years[0], odd → group_years[1]
            if series_idx % 2 == 0:
                order = list(group_years)
            else:
                order = list(reversed(group_years))

            year_cycle = _cycle(order)
            for _ in range(athletes_per_series):
                placed = False
                # Try up to len(year_cycle) times to find a year with athletes
                for _ in range(len(order)):
                    year = next(year_cycle)
                    if pools.get(year):
                        series.append(pools[year].popleft())
                        placed = True
                        break
                if not placed:
                    series.append(None)

        all_series.append(series)

    return all_series


def _year_order_for_group(group: str) -> list[str]:
    """Return school years in display order for a given competition group."""
    g = _normalize(group)
    if "6" in g and "7" in g:
        return ["6º Ano", "7º Ano"]
    if "8" in g and "9" in g:
        return ["8º Ano", "9º Ano"]
    # Ensino Médio or unknown
    return ["1º Ano Médio", "2º Ano Médio", "3º Ano Médio"]


def _merge_pools(pools, years):
    """Merge all pools into a single deque (round-robin order)."""
    from collections import deque
    merged = deque()
    while any(pools.get(y) for y in years):
        for y in years:
            if pools.get(y):
                merged.append(pools[y].popleft())
    return merged


def _cycle(lst: list):
    """Infinite cycle over a list."""
    i = 0
    while True:
        yield lst[i % len(lst)]
        i += 1
