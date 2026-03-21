from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from models import Student, Result, Event
from extensions import db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    # ── Team ranking: sum of points per school_year ──────────────────────────
    team_ranking = (
        db.session.query(
            Student.school_year,
            func.sum(Result.points).label("total_points"),
            func.count(Result.id).label("total_results"),
        )
        .join(Result, Result.student_id == Student.id)
        .group_by(Student.school_year)
        .order_by(func.sum(Result.points).desc())
        .all()
    )

    # ── Results per event → corrida_num → school_year ───────────────────────
    events = Event.query.order_by(Event.name).all()
    event_results = {}
    for event in events:
        by_corrida = {}
        results = (
            Result.query
            .filter_by(event_id=event.id)
            .join(Student)
            .order_by(
                Result.corrida_num.asc(),
                Student.school_year,
                Result.placement.asc().nullslast(),
                Result.total_time.asc().nullslast(),
            )
            .all()
        )
        for r in results:
            c_key = r.corrida_num or 1
            sy = r.student.school_year
            by_corrida.setdefault(c_key, {}).setdefault(sy, []).append(r)
        event_results[event] = by_corrida

    has_results = Result.query.count() > 0

    return render_template(
        "dashboard.html",
        team_ranking=team_ranking,
        event_results=event_results,
        has_results=has_results,
    )
