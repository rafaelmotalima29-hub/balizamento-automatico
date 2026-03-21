from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from extensions import db
from models import Student, Event, Result
from services.seeding import COMPETITION_GROUPS

cancelamentos_bp = Blueprint("cancelamentos", __name__)

# Map competition group → list of school years
GROUP_TO_YEARS = {
    "6º e 7º Ano":  ["6º Ano", "7º Ano"],
    "8º e 9º Ano":  ["8º Ano", "9º Ano"],
    "Ensino Médio": ["1º Ano Médio", "2º Ano Médio", "3º Ano Médio"],
}


@cancelamentos_bp.route("/cancelamentos")
@login_required
def cancelamentos():
    events = Event.query.order_by(Event.competition_group, Event.name).all()
    return render_template(
        "cancelamentos.html",
        events=events,
        competition_groups=COMPETITION_GROUPS,
    )


@cancelamentos_bp.route("/api/event/<int:event_id>/students")
@login_required
def event_students(event_id):
    event = Event.query.get_or_404(event_id)
    group = event.competition_group or ""

    years = []
    if group:
        for g in group.split(","):
            years.extend(GROUP_TO_YEARS.get(g.strip(), []))
    if years:
        students = (
            Student.query
            .filter(Student.school_year.in_(years))
            .order_by(Student.school_year, Student.full_name)
            .all()
        )
    else:
        students = Student.query.order_by(Student.school_year, Student.full_name).all()

    # Build result map: student_id → Result (any corrida)
    results = Result.query.filter_by(event_id=event_id).all()
    result_map = {}
    for r in results:
        # Keep only the first corrida per student for display
        if r.student_id not in result_map:
            result_map[r.student_id] = r

    out = []
    for s in students:
        r = result_map.get(s.id)
        out.append({
            "id": s.id,
            "full_name": s.full_name,
            "registration": s.registration,
            "school_year": s.school_year,
            "classroom": s.classroom or "",
            "result": {
                "id": r.id,
                "is_dq": r.is_dq,
                "total_time": r.total_time,
                "points": r.points,
                "time_display": r.time_display(),
            } if r else None,
        })

    return jsonify({
        "students": out,
        "event": {
            "id": event.id,
            "name": event.name,
            "competition_group": group,
        },
    })


@cancelamentos_bp.route("/api/result/toggle-dq", methods=["POST"])
@login_required
def toggle_dq():
    data = request.get_json(force=True) or {}
    student_id = data.get("student_id")
    event_id = data.get("event_id")

    if not student_id or not event_id:
        return jsonify({"error": "student_id e event_id são obrigatórios"}), 400

    student = Student.query.get(student_id)
    event = Event.query.get(event_id)
    if not student or not event:
        return jsonify({"error": "Aluno ou prova não encontrado"}), 404

    result = Result.query.filter_by(
        student_id=student_id,
        event_id=event_id,
        corrida_num=1,
    ).first()

    if result:
        result.is_dq = not result.is_dq
        if result.is_dq:
            result.points = 0
            result.placement = None
            result.total_time = None
            result.minutes = 9
            result.seconds = 99
            result.centesimos = 99
        db.session.commit()
        return jsonify({"ok": True, "is_dq": result.is_dq, "action": "updated"})
    else:
        result = Result(
            student_id=student_id,
            event_id=event_id,
            corrida_num=1,
            minutes=9,
            seconds=99,
            centesimos=99,
            total_time=None,
            placement=None,
            points=0,
            is_dq=True,
        )
        db.session.add(result)
        db.session.commit()
        return jsonify({"ok": True, "is_dq": True, "action": "created"})
