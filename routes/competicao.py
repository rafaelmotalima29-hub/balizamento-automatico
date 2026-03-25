"""
Montar Competição — assign students to events.

Each student can be registered in at most MAX_EVENTS_PER_STUDENT events.
The page lets the user pick an event, see eligible students (filtered by
competition group and gender), and toggle assignments with checkboxes.
"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from extensions import db
from models import Student, Event, EventRegistration
from services.seeding import COMPETITION_GROUPS, YEAR_TO_GROUP
from collections import defaultdict

competicao_bp = Blueprint("competicao", __name__)

MAX_EVENTS_PER_STUDENT = 4


def _years_for_group(group: str) -> list[str]:
    return [y for y, g in YEAR_TO_GROUP.items() if g == group]


# ── Main page ────────────────────────────────────────────────────────

@competicao_bp.route("/competicao")
@login_required
def competicao():
    events = Event.query.order_by(Event.name).all()
    selected_event_id = request.args.get("event_id", type=int)

    selected_event = None
    eligible_students = []
    assigned_ids = set()
    student_event_counts = {}

    if selected_event_id:
        selected_event = Event.query.get(selected_event_id)

    if selected_event:
        # Get eligible students (filter by competition group + gender)
        sq = Student.query.order_by(Student.school_year, Student.full_name)

        if selected_event.competition_group:
            eligible_years = []
            for g in selected_event.competition_group.split(","):
                eligible_years.extend(_years_for_group(g.strip()))
            if eligible_years:
                sq = sq.filter(Student.school_year.in_(eligible_years))

        if selected_event.group_id:
            sq = sq.filter_by(group_id=selected_event.group_id)

        if selected_event.gender and selected_event.gender != "MISTO":
            sq = sq.filter_by(gender=selected_event.gender)

        eligible_students = sq.all()

        # Currently assigned student IDs for this event
        assigned_ids = {
            r.student_id
            for r in EventRegistration.query.filter_by(event_id=selected_event_id).all()
        }

        # Count how many events each eligible student is registered in
        student_ids = [s.id for s in eligible_students]
        if student_ids:
            all_regs = EventRegistration.query.filter(
                EventRegistration.student_id.in_(student_ids)
            ).all()
            counts = defaultdict(int)
            for reg in all_regs:
                counts[reg.student_id] += 1
            student_event_counts = dict(counts)

    # Summary: count assigned per event
    event_reg_counts = {}
    reg_counts = db.session.query(
        EventRegistration.event_id, db.func.count(EventRegistration.id)
    ).group_by(EventRegistration.event_id).all()
    for eid, cnt in reg_counts:
        event_reg_counts[eid] = cnt

    return render_template(
        "competicao.html",
        events=events,
        selected_event=selected_event,
        selected_event_id=selected_event_id,
        eligible_students=eligible_students,
        assigned_ids=assigned_ids,
        student_event_counts=student_event_counts,
        event_reg_counts=event_reg_counts,
        max_events=MAX_EVENTS_PER_STUDENT,
    )


# ── Toggle assignment (AJAX) ─────────────────────────────────────────

@competicao_bp.route("/competicao/toggle", methods=["POST"])
@login_required
def toggle_registration():
    data = request.get_json(force=True) or {}
    student_id = data.get("student_id")
    event_id = data.get("event_id")

    if not student_id or not event_id:
        return jsonify({"error": "Dados incompletos."}), 400

    student = Student.query.get(student_id)
    event = Event.query.get(event_id)
    if not student or not event:
        return jsonify({"error": "Aluno ou prova não encontrado."}), 404

    existing = EventRegistration.query.filter_by(
        student_id=student_id, event_id=event_id
    ).first()

    if existing:
        # Remove assignment
        db.session.delete(existing)
        db.session.commit()
        count = EventRegistration.query.filter_by(student_id=student_id).count()
        return jsonify({"ok": True, "action": "removed", "event_count": count})
    else:
        # Check max events
        current_count = EventRegistration.query.filter_by(student_id=student_id).count()
        if current_count >= MAX_EVENTS_PER_STUDENT:
            return jsonify({
                "error": f"Aluno já está inscrito em {MAX_EVENTS_PER_STUDENT} provas (máximo).",
                "event_count": current_count,
            }), 400

        reg = EventRegistration(student_id=student_id, event_id=event_id)
        db.session.add(reg)
        db.session.commit()
        return jsonify({"ok": True, "action": "added", "event_count": current_count + 1})
