"""
Resultados: detailed competition results dashboard.

Groups results by competition_group and provides:
  - Podium (top 3 overall per group)
  - Full group ranking
  - Per-school-year sub-rankings
"""

from collections import defaultdict
from flask import Blueprint, render_template

from extensions import db
from models import Student, Event, Result

resultados_bp = Blueprint("resultados", __name__)


@resultados_bp.route("/resultados")
def resultados():
    has_results = Result.query.count() > 0
    if not has_results:
        return render_template("resultados.html", groups=[], has_results=False)

    # Load all results with students/events
    results = (
        Result.query
        .filter(Result.is_dq == False, Result.total_time.isnot(None))
        .join(Student)
        .join(Event)
        .order_by(Result.total_time.asc())
        .all()
    )

    # Build per-group data
    # {competition_group: [result, ...]}
    by_group: dict[str, list] = defaultdict(list)
    for r in results:
        group = r.event.competition_group or "Sem Grupo"
        by_group[group].append(r)

    # Order groups
    from services.seeding import COMPETITION_GROUPS
    group_order = [g for g in COMPETITION_GROUPS if g in by_group]
    if "Sem Grupo" in by_group and "Sem Grupo" not in group_order:
        group_order.append("Sem Grupo")

    groups_data = []
    for group_name in group_order:
        group_results = by_group[group_name]
        # Sort by total_time ascending
        group_results.sort(key=lambda r: r.total_time)

        # Podium: top 3 unique students (by best time)
        seen_students = set()
        podium = []
        for r in group_results:
            if r.student_id not in seen_students:
                seen_students.add(r.student_id)
                podium.append(r)
            if len(podium) == 3:
                break

        # Full ranking: deduplicate students (best time wins)
        seen2 = set()
        full_ranking = []
        rank_counter = 1
        prev_time = None
        for r in group_results:
            if r.student_id in seen2:
                continue
            seen2.add(r.student_id)
            if r.total_time != prev_time:
                current_rank = rank_counter
                prev_time = r.total_time
            full_ranking.append({"rank": current_rank, "result": r})
            rank_counter += 1

        # Per-year rankings
        year_rankings: dict[str, list] = defaultdict(list)
        for entry in full_ranking:
            yr = entry["result"].student.school_year
            year_rankings[yr].append(entry)

        # Re-rank within each year
        for yr in year_rankings:
            entries = year_rankings[yr]
            entries.sort(key=lambda e: e["result"].total_time)
            for i, entry in enumerate(entries):
                entry["year_rank"] = i + 1

        groups_data.append({
            "name": group_name,
            "podium": podium,
            "full_ranking": full_ranking,
            "year_rankings": dict(year_rankings),
            "years": sorted(year_rankings.keys()),
        })

    return render_template(
        "resultados.html",
        groups=groups_data,
        has_results=True,
    )


def _fmt_time(total: float) -> str:
    """Format float seconds as M:SS.cc"""
    m = int(total // 60)
    s = int(total % 60)
    c = round((total - int(total)) * 100)
    return f"{m}:{s:02d}.{c:02d}"
