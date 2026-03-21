from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


def load_user(user_id):
    """Callback for Flask-Login's user_loader."""
    return db.session.get(User, int(user_id))


def _has_users():
    """Check if at least one user exists in the database."""
    return db.session.query(User.id).first() is not None


# ── Routes ──────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if not _has_users():
        return redirect(url_for("auth.register"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard.index"))

        flash("Usuário ou senha incorretos.", "error")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if _has_users():
        flash("Cadastro desabilitado. Já existe um usuário registrado.", "warning")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not password:
            flash("Preencha todos os campos.", "error")
            return render_template("register.html")

        if len(username) < 3:
            flash("O nome de usuário deve ter pelo menos 3 caracteres.", "error")
            return render_template("register.html")

        if len(password) < 4:
            flash("A senha deve ter pelo menos 4 caracteres.", "error")
            return render_template("register.html")

        if password != confirm:
            flash("As senhas não coincidem.", "error")
            return render_template("register.html")

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user, remember=True)
        flash(f"Conta '{username}' criada com sucesso! Bem-vindo ao SwimRank.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for("auth.login"))
