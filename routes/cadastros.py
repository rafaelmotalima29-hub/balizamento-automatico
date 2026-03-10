from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from extensions import db
from models import Student, Event
from services.seeding import COMPETITION_GROUPS

cadastros_bp = Blueprint("cadastros", __name__)


@cadastros_bp.route("/cadastros")
def cadastros():
    students = Student.query.order_by(Student.school_year, Student.full_name).all()
    events = Event.query.order_by(Event.name).all()
    return render_template(
        "cadastros.html",
        students=students,
        events=events,
        competition_groups=COMPETITION_GROUPS,
    )


@cadastros_bp.route("/cadastros/aluno", methods=["POST"])
def add_student():
    full_name = request.form.get("full_name", "").strip()
    registration = request.form.get("registration", "").strip()
    school_year = request.form.get("school_year", "").strip()
    classroom = request.form.get("classroom", "").strip() or None

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


@cadastros_bp.route("/cadastros/aluno/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    db.session.delete(student)
    db.session.commit()
    return jsonify({"ok": True, "message": f"Aluno '{student.full_name}' removido."})


@cadastros_bp.route("/cadastros/prova", methods=["POST"])
def add_event():
    name = request.form.get("name", "").strip()
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
    flash(
        f"Prova '{name}' cadastrada! ({num_series} série(s) × {athletes_per_series} raias)",
        "success",
    )
    return redirect(url_for("cadastros.cadastros"))


@cadastros_bp.route("/cadastros/prova/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({"ok": True, "message": f"Prova '{event.name}' removida."})
