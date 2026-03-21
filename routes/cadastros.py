from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models import Student, Event
from services.seeding import COMPETITION_GROUPS, YEAR_TO_GROUP
from collections import defaultdict

cadastros_bp = Blueprint("cadastros", __name__)

# Map group → years (derived from seeding constants)
_GROUP_YEARS = defaultdict(list)
for _y, _g in YEAR_TO_GROUP.items():
    _GROUP_YEARS[_g].append(_y)


@cadastros_bp.route("/cadastros")
def cadastros():
    students = Student.query.order_by(Student.school_year, Student.full_name).all()
    events   = Event.query.order_by(Event.name).all()

    # ── Metrics ──────────────────────────────────────────────────────
    # Students per year
    year_counts = defaultdict(int)
    for s in students:
        year_counts[s.school_year] += 1

    # Students per group
    group_student_counts = {}
    for group in COMPETITION_GROUPS:
        years = _GROUP_YEARS.get(group, [])
        group_student_counts[group] = sum(year_counts[y] for y in years)

    # Events per group
    group_event_counts = defaultdict(int)
    for e in events:
        group_event_counts[e.competition_group or "Sem Grupo"] += 1

    return render_template(
        "cadastros.html",
        students=students,
        events=events,
        competition_groups=COMPETITION_GROUPS,
        year_counts=dict(year_counts),
        group_student_counts=group_student_counts,
        group_event_counts=dict(group_event_counts),
    )


# ── Student CRUD ─────────────────────────────────────────────────────

@cadastros_bp.route("/cadastros/aluno", methods=["POST"])
def add_student():
    full_name    = request.form.get("full_name", "").strip()
    registration = request.form.get("registration", "").strip()
    school_year  = request.form.get("school_year", "").strip()
    classroom    = request.form.get("classroom", "").strip() or None

    if not all([full_name, registration, school_year]):
        flash("Preencha todos os campos obrigatórios do aluno.", "error")
        return redirect(url_for("cadastros.cadastros"))

    existing = Student.query.filter_by(registration=registration).first()
    if existing:
        flash(f"Matrícula '{registration}' já cadastrada.", "error")
        return redirect(url_for("cadastros.cadastros"))

    student = Student(
        full_name=full_name,
        registration=registration,
        school_year=school_year,
        classroom=classroom,
    )
    db.session.add(student)
    db.session.commit()
    flash(f"Aluno '{full_name}' cadastrado com sucesso!", "success")
    return redirect(url_for("cadastros.cadastros"))


@cadastros_bp.route("/cadastros/aluno/<int:student_id>", methods=["PUT"])
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    data    = request.get_json(force=True) or {}

    full_name    = data.get("full_name", "").strip()
    registration = data.get("registration", "").strip()
    school_year  = data.get("school_year", "").strip()
    classroom    = data.get("classroom", "").strip() or None

    if not all([full_name, registration, school_year]):
        return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400

    dup = Student.query.filter(
        Student.registration == registration,
        Student.id != student_id,
    ).first()
    if dup:
        return jsonify({"error": f"Matrícula '{registration}' já está em uso."}), 409

    student.full_name    = full_name
    student.registration = registration
    student.school_year  = school_year
    student.classroom    = classroom
    db.session.commit()

    return jsonify({
        "ok": True,
        "student": {
            "id":           student.id,
            "full_name":    student.full_name,
            "registration": student.registration,
            "school_year":  student.school_year,
            "classroom":    student.classroom or "",
        },
    })


@cadastros_bp.route("/cadastros/aluno/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({"ok": True, "message": f"Aluno '{student.full_name}' removido."})


# ── Event CRUD ────────────────────────────────────────────────────────

@cadastros_bp.route("/cadastros/prova", methods=["POST"])
def add_event():
    name              = request.form.get("name", "").strip()
    competition_group = request.form.get("competition_group", "").strip() or None
    try:
        num_corridas = max(1, min(10, int(request.form.get("num_corridas", 1))))
    except (ValueError, TypeError):
        num_corridas = 1
    try:
        num_series = max(1, min(50, int(request.form.get("num_series", 1))))
    except (ValueError, TypeError):
        num_series = 1
    try:
        athletes_per_series = max(1, min(20, int(request.form.get("athletes_per_series", 8))))
    except (ValueError, TypeError):
        athletes_per_series = 8

    if not name:
        flash("Informe o nome da prova.", "error")
        return redirect(url_for("cadastros.cadastros"))

    existing = Event.query.filter_by(name=name).first()
    if existing:
        flash(f"Prova '{name}' já cadastrada.", "error")
        return redirect(url_for("cadastros.cadastros"))

    event = Event(
        name=name,
        num_corridas=num_corridas,
        competition_group=competition_group,
        num_series=num_series,
        athletes_per_series=athletes_per_series,
    )
    db.session.add(event)
    db.session.commit()
    flash(f"Prova '{name}' cadastrada! ({num_series} série(s) × {athletes_per_series} raias)", "success")
    return redirect(url_for("cadastros.cadastros"))


@cadastros_bp.route("/cadastros/prova/<int:event_id>", methods=["PUT"])
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    data  = request.get_json(force=True) or {}

    name              = data.get("name", "").strip()
    competition_group = data.get("competition_group", "").strip() or None
    try:
        num_series = max(1, min(50, int(data.get("num_series", 1))))
    except (ValueError, TypeError):
        num_series = 1
    try:
        athletes_per_series = max(1, min(20, int(data.get("athletes_per_series", 8))))
    except (ValueError, TypeError):
        athletes_per_series = 8

    if not name:
        return jsonify({"error": "Informe o nome da prova."}), 400

    dup = Event.query.filter(Event.name == name, Event.id != event_id).first()
    if dup:
        return jsonify({"error": f"Prova '{name}' já cadastrada."}), 409

    event.name              = name
    event.competition_group = competition_group
    event.num_series        = num_series
    event.athletes_per_series = athletes_per_series
    db.session.commit()

    return jsonify({
        "ok": True,
        "event": {
            "id":                 event.id,
            "name":               event.name,
            "competition_group":  event.competition_group or "",
            "num_series":         event.num_series,
            "athletes_per_series": event.athletes_per_series,
        },
    })


@cadastros_bp.route("/cadastros/prova/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({"ok": True, "message": f"Prova '{event.name}' removida."})
