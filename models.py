from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class Group(db.Model):
    """
    Grupo/Turma ao qual um aluno pode pertencer ou que uma prova pode restringir.
    """
    __tablename__ = "groups"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Group {self.name}>"

class User(UserMixin, db.Model):
    """Application user for authentication."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


class ScoreConfig(db.Model):
    """
    Tabela de pontuação configurável.
    Cada linha associa uma colocação (1º, 2º, …) a uma quantidade de pontos.
    """
    __tablename__ = "score_config"

    placement = db.Column(db.Integer, primary_key=True)   # 1, 2, 3 …
    points    = db.Column(db.Integer, nullable=False, default=0)

    def __repr__(self):
        return f"<ScoreConfig {self.placement}º → {self.points} pts>"


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    registration = db.Column(db.String(50), nullable=False, unique=True)
    school_year = db.Column(db.String(50), nullable=False)
    classroom = db.Column(db.String(20), nullable=True)  # Sala (ex: 6A, 7B)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    results = db.relationship("Result", backref="student", lazy=True, cascade="all, delete-orphan")
    group = db.relationship("Group", backref="students", lazy=True)

    def __repr__(self):
        return f"<Student {self.full_name} – {self.school_year}>"


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    num_corridas = db.Column(db.Integer, nullable=False, default=1)  # heats per student (legacy)
    competition_group = db.Column(db.String(50), nullable=True)  # ex: "6º e 7º Ano"
    num_series = db.Column(db.Integer, nullable=False, default=1)   # number of heats/bateries
    athletes_per_series = db.Column(db.Integer, nullable=False, default=8)  # lanes per heat
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    results = db.relationship("Result", backref="event", lazy=True, cascade="all, delete-orphan")
    group = db.relationship("Group", backref="events", lazy=True)

    def __repr__(self):
        return f"<Event {self.name} ({self.competition_group})>"


class Result(db.Model):
    __tablename__ = "results"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    corrida_num = db.Column(db.Integer, nullable=False, default=1)  # which heat (1, 2, 3…)

    minutes = db.Column(db.Integer, nullable=False, default=0)
    seconds = db.Column(db.Integer, nullable=False, default=0)
    centesimos = db.Column(db.Integer, nullable=False, default=0)
    total_time = db.Column(db.Float, nullable=True)  # computed: min*60 + sec + cent/100

    placement = db.Column(db.Integer, nullable=True)
    points = db.Column(db.Integer, nullable=False, default=0)
    is_dq = db.Column(db.Boolean, nullable=False, default=False)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Unique per student × event × heat
    __table_args__ = (
        db.UniqueConstraint("student_id", "event_id", "corrida_num", name="uix_student_event_corrida"),
    )

    def time_display(self):
        if self.is_dq:
            return "DQ"
        return f"{self.minutes}:{self.seconds:02d}.{self.centesimos:02d}"

    def __repr__(self):
        return f"<Result s={self.student_id} e={self.event_id} c={self.corrida_num} t={self.total_time}>"
