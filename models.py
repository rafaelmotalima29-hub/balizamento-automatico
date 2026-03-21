from datetime import datetime
from extensions import db


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    results = db.relationship("Result", backref="student", lazy=True, cascade="all, delete-orphan")

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    results = db.relationship("Result", backref="event", lazy=True, cascade="all, delete-orphan")

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
    is_dq = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
