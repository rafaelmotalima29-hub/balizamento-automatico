from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func
from models import Student, Result, Event, Group
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

    from sqlalchemy.orm import contains_eager

    # ── Results per event → corrida_num → school_year ───────────────────────
    # We pre-fill the dictionary with all events so even empty events show up
    all_events = Event.query.order_by(Event.name).all()
    event_results = {e: {} for e in all_events}

    # Fetch ALL results in a single heavily optimized query
    all_results = (
        Result.query
        .join(Result.student)
        .join(Result.event)
        .options(contains_eager(Result.student), contains_eager(Result.event))
        .order_by(
            Event.name.asc(),
            Result.corrida_num.asc(),
            Student.school_year.asc(),
            Result.placement.asc().nullslast(),
            Result.total_time.asc().nullslast(),
        )
        .all()
    )

    for r in all_results:
        evt = r.event
        if evt not in event_results:
            event_results[evt] = {}
        
        c_key = r.corrida_num or 1
        sy = r.student.school_year
        event_results[evt].setdefault(c_key, {}).setdefault(sy, []).append(r)

    has_results = Result.query.count() > 0

    student_count = Student.query.count()
    event_count   = Event.query.count()
    group_count   = Group.query.count()

    return render_template(
        "dashboard.html",
        team_ranking=team_ranking,
        event_results=event_results,
        has_results=has_results,
        student_count=student_count,
        event_count=event_count,
        group_count=group_count,
    )
