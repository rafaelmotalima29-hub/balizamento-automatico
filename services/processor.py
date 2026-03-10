"""
Upload processor — reads the seeded XLSX format produced by balizamento.py.

Expected sheet columns (one row per lane):
  Série | Raia | Nome | Matrícula | Ano Escolar | Sala | Minutos | Segundos | Centésimos

Multiple sheets (one per competition group) are all processed.

DQ convention: Minutos == 9 → disqualified/absent.
"""

import re
import unicodedata
import pandas as pd
from collections import defaultdict

from extensions import db
from models import Student, Event, Result

POINTS_TABLE = {1: 10, 2: 8, 3: 7, 4: 6, 5: 5, 6: 4, 7: 3, 8: 2, 9: 1}
DQ_MINUTES = 9


# ── Tiny helpers ──────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _is_dq(minutes: int) -> bool:
    return int(minutes) == DQ_MINUTES


def _convert_time(minutes: int, seconds: int, centesimos: int) -> float:
    return int(minutes) * 60 + int(seconds) + int(centesimos) / 100


def _assign_points(rank: int) -> int:
    return POINTS_TABLE.get(rank, 0)


def _safe_int(val, default=0) -> int:
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


# ── Main entry point ──────────────────────────────────────────────────

def process_upload(filepath: str) -> dict:
    """
    Parse uploaded XLSX (seeded format, multi-sheet), compute rankings,
    persist Results, return summary dict.
    """
    # ── 1. Load all sheets ───────────────────────────────────────────
    try:
        if filepath.lower().endswith(".csv"):
            sheets = {"Sheet1": pd.read_csv(filepath, dtype=str, encoding="utf-8-sig")}
        else:
            xl = pd.ExcelFile(filepath)
            sheets = {name: xl.parse(name, dtype=str) for name in xl.sheet_names}
    except Exception as exc:
        return {"processed": 0, "errors": [f"Erro ao ler arquivo: {exc}"], "skipped": 0}

    errors = []
    # key: (student, corrida_num=1) → {min, seg, cent, serie, event}
    # We use the event implied by the sheet + student matching
    # Actually: one result per student per event (aluno só nada uma série por prova)
    time_data: dict = {}  # (student_id, event_id) → {min, seg, cent}
    events_all = Event.query.all()
    events_by_name = {_normalize(e.name): e for e in events_all}

    # ── 2. Process each sheet ────────────────────────────────────────
    for sheet_name, df in sheets.items():
        df.columns = [str(c).strip() for c in df.columns]

        # Detect format: seeded (has "Série") vs legacy (has event-corrida cols)
        norm_cols = {_normalize(c): c for c in df.columns}

        if "serie" in norm_cols or "série" in norm_cols:
            _process_seeded_sheet(df, norm_cols, time_data, errors, events_by_name)
        else:
            _process_legacy_sheet(df, time_data, errors, events_all)

    if not time_data:
        return {
            "processed": 0,
            "errors": errors + ["Nenhum tempo válido encontrado no arquivo."],
            "skipped": 0,
        }

    # ── 3. Build result list ─────────────────────────────────────────
    rows_to_process = []
    for (student_id, event_id), fields in time_data.items():
        if any(v is None for v in [fields.get("min"), fields.get("seg"), fields.get("cent")]):
            continue
        minutes    = fields["min"]
        seconds    = fields["seg"]
        centesimos = fields["cent"]
        dq         = _is_dq(minutes)
        rows_to_process.append({
            "student_id": student_id,
            "event_id":   event_id,
            "corrida_num": 1,
            "minutes":    minutes,
            "seconds":    seconds,
            "centesimos": centesimos,
            "dq":         dq,
            "total_time": _convert_time(minutes, seconds, centesimos) if not dq else None,
        })

    if not rows_to_process:
        return {"processed": 0, "errors": errors + ["Nenhum tempo válido encontrado."], "skipped": 0}

    # ── 4. Persist ───────────────────────────────────────────────────
    Result.query.delete()
    db.session.flush()

    result_objs = []
    for r in rows_to_process:
        res = Result(
            student_id=r["student_id"],
            event_id=r["event_id"],
            corrida_num=r["corrida_num"],
            minutes=r["minutes"],
            seconds=r["seconds"],
            centesimos=r["centesimos"],
            total_time=r["total_time"],
            is_dq=r["dq"],
            points=0,
            placement=None,
        )
        db.session.add(res)
        result_objs.append((r, res))

    db.session.flush()

    # ── 5. Rank within (event, school_year) ─────────────────────────
    # Pull student for ranking
    student_map = {s.id: s for s in Student.query.all()}
    event_map   = {e.id: e for e in events_all}

    groups = defaultdict(list)
    for row_data, res_obj in result_objs:
        student = student_map.get(row_data["student_id"])
        if student:
            key = (row_data["event_id"], student.school_year)
            groups[key].append((row_data, res_obj))

    for key, group in groups.items():
        valid = [(r, o) for r, o in group if not r["dq"]]
        disq  = [(r, o) for r, o in group if r["dq"]]
        valid.sort(key=lambda x: x[0]["total_time"])

        rank = 1
        for i, (row_data, res_obj) in enumerate(valid):
            if i > 0 and row_data["total_time"] == valid[i - 1][0]["total_time"]:
                pass  # tie
            else:
                rank = i + 1
            res_obj.placement = rank
            res_obj.points    = _assign_points(rank)

        for _, res_obj in disq:
            res_obj.placement = None
            res_obj.points    = 0

    db.session.commit()
    return {"processed": len(rows_to_process), "errors": errors, "skipped": 0}


# ── Format parsers ────────────────────────────────────────────────────

def _process_seeded_sheet(df, norm_cols, time_data, errors, events_by_name):
    """Parse the seeded multi-series format (Série|Raia|Nome|Matrícula|…|Min|Seg|Cent)."""
    matricula_col = norm_cols.get("matricula") or norm_cols.get("matrícula")
    min_col  = norm_cols.get("minutos")
    seg_col  = norm_cols.get("segundos")
    cent_col = norm_cols.get("centesimos") or norm_cols.get("centésimos")

    if not all([matricula_col, min_col, seg_col, cent_col]):
        # Skip rows that are event-title separators (merged cells become NaN)
        return

    for row_idx, df_row in df.iterrows():
        line = row_idx + 2
        registration = str(df_row.get(matricula_col, "")).strip()
        if not registration or registration.lower() in ("nan", "", "none"):
            continue

        min_raw  = str(df_row.get(min_col, "")).strip()
        seg_raw  = str(df_row.get(seg_col, "")).strip()
        cent_raw = str(df_row.get(cent_col, "")).strip()

        # All three must be present
        if any(v.lower() in ("", "nan", "none", "-") for v in [min_raw, seg_raw, cent_raw]):
            continue

        student = Student.query.filter_by(registration=registration).first()
        if not student:
            errors.append(f"Linha {line}: Matrícula '{registration}' não encontrada.")
            continue

        # Find which event this student belongs to based on their school_year
        event = _event_for_student(student, events_by_name)
        if not event:
            errors.append(f"Linha {line}: Nenhuma prova encontrada para o aluno '{student.full_name}'.")
            continue

        key = (student.id, event.id)
        if key not in time_data:
            time_data[key] = {
                "min":  _safe_int(min_raw),
                "seg":  _safe_int(seg_raw),
                "cent": _safe_int(cent_raw),
            }


def _event_for_student(student, events_by_name):
    """Find the first event whose competition_group matches the student's school_year."""
    from services.seeding import YEAR_TO_GROUP
    student_group = YEAR_TO_GROUP.get(student.school_year)
    from models import Event
    for event in Event.query.all():
        if event.competition_group == student_group:
            return event
    return None


# Legacy wide-format parser (kept for backwards compatibility)
_COL_PATTERN = re.compile(
    r"^(.+)\s*-\s*corrida\s+(\d+)\s*-\s*(minuto|segundo|centesimo|cent)",
    re.IGNORECASE,
)
FIELD_MAP = {"minuto": "min", "segundo": "seg", "centesimo": "cent", "cent": "cent"}


def _process_legacy_sheet(df, time_data, errors, events_all):
    event_by_norm = {_normalize(e.name): e for e in events_all}
    col_map = {}
    for col in df.columns:
        m = _COL_PATTERN.match(_normalize(col))
        if not m:
            continue
        ev_norm = _normalize(m.group(1))
        if ev_norm not in event_by_norm:
            continue
        field = FIELD_MAP.get(m.group(3).lower().rstrip("s"))
        if field:
            col_map[col] = (event_by_norm[ev_norm], int(m.group(2)), field)

    for row_idx, df_row in df.iterrows():
        line = row_idx + 2
        registration = str(df_row.get("Matrícula", "")).strip()
        if not registration:
            continue
        student = Student.query.filter_by(registration=registration).first()
        if not student:
            errors.append(f"Linha {line}: Matrícula '{registration}' não encontrada.")
            continue
        for col, (event, corrida_num, field) in col_map.items():
            raw = str(df_row.get(col, "")).strip()
            if raw.lower() in ("", "nan", "none", "-"):
                continue
            key = (student.id, event.id)
            time_data.setdefault(key, {"min": None, "seg": None, "cent": None})
            try:
                time_data[key][field] = int(float(raw))
            except ValueError:
                errors.append(f"Linha {line}, '{col}': valor inválido '{raw}'.")
