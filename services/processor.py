"""
Upload processor — reads the seeded XLSX format produced by balizamento.py.

Expected XLSX structure (one sheet per competition group):
  • Row 1 per event block: merged title cell  e.g. "🏁 50m Livre"
  • Row 2: column headers  Série | Raia | Nome | Matrícula | Ano Escolar | Sala | Minutos | Segundos | Centésimos
  • Rows 3+: one row per lane

Multiple events may appear in the same sheet (each preceded by its title row).
Multiple sheets are all processed.

DQ convention: Minutos == 9 → disqualified/absent.
"""

import re
import unicodedata
import pandas as pd
from collections import defaultdict

from extensions import db
from models import Student, Event, Result

DQ_MINUTES = 9


def _load_points_table() -> dict:
    """Carrega a tabela de pontuação configurada no banco de dados."""
    from models import ScoreConfig
    rows = ScoreConfig.query.all()
    return {row.placement: row.points for row in rows}


# ── Tiny helpers ──────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _is_dq(minutes: int) -> bool:
    return int(minutes) == DQ_MINUTES


def _convert_time(minutes: int, seconds: int, centesimos: int) -> float:
    return int(minutes) * 60 + int(seconds) + int(centesimos) / 100


def _assign_points(rank: int, points_table: dict) -> int:
    return points_table.get(rank, 0)


def _safe_int(val, default=0) -> int:
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


# ── Main entry point ──────────────────────────────────────────────────

def process_upload(filepath: str) -> dict:
    """
    Parse uploaded file (CSV or XLSX/XLS seeded format), compute rankings,
    persist Results, return summary dict.
    """
    # ── 1. Load all sheets ───────────────────────────────────────────
    try:
        if filepath.lower().endswith(".csv"):
            # CSV: read with explicit headers
            df = pd.read_csv(filepath, dtype=str, encoding="utf-8-sig")
            df.columns = [str(c).strip() for c in df.columns]
            sheets_plain = {"Sheet1": df}
            sheets_raw = {}
        else:
            xl = pd.ExcelFile(filepath)
            sheets_plain = {}
            # Read without header=0 so we can detect our custom structure
            # (the app exports a merged title row before the column-header row)
            sheets_raw = {
                name: xl.parse(name, dtype=str, header=None)
                for name in xl.sheet_names
            }
    except Exception as exc:
        return {"processed": 0, "errors": [f"Erro ao ler arquivo: {exc}"], "skipped": 0}

    errors = []
    # (student_id, event_id) → {min, seg, cent}
    time_data: dict = {}
    events_all = Event.query.all()
    events_by_name = {_normalize(e.name): e for e in events_all}

    # ── 2. Process each sheet ────────────────────────────────────────
    # CSV: standard column-header format
    for sheet_name, df in sheets_plain.items():
        norm_cols = {_normalize(c): c for c in df.columns}
        if "serie" in norm_cols or "série" in norm_cols:
            _process_seeded_sheet(df, norm_cols, time_data, errors, events_by_name)
        else:
            _process_legacy_sheet(df, time_data, errors, events_all)

    # XLSX/XLS: handle custom multi-event format with title rows
    for sheet_name, df_raw in sheets_raw.items():
        _process_xlsx_sheet(df_raw, time_data, errors, events_by_name)

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
    points_table = _load_points_table()
    student_map  = {s.id: s for s in Student.query.all()}

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
                pass  # tie — same rank
            else:
                rank = i + 1
            res_obj.placement = rank
            res_obj.points    = _assign_points(rank, points_table)

        for _, res_obj in disq:
            res_obj.placement = None
            res_obj.points    = 0

    db.session.commit()
    return {"processed": len(rows_to_process), "errors": errors, "skipped": 0}


# ── XLSX multi-event parser (primary format) ──────────────────────────

# Keywords that identify a column-header row
_HEADER_MARKERS = {"serie", "série"}


def _process_xlsx_sheet(df_raw, time_data, errors, events_by_name):
    """
    Parse a raw (header=None) DataFrame from one XLSX sheet.

    Handles the app-generated seeded format:
      - Event title row: merged cell; only column 0 has a value (non-numeric text)
      - Column header row: contains "Série" / "série" in one of the cells
      - Data rows: one per lane
      - Empty spacer rows: between event blocks

    Also handles plain XLSX (no title row) where row 0 is the header row.
    In that case current_event stays None and _event_for_student() is used as fallback.
    """
    current_event = None
    col_map = None   # field_name → column index

    for row_idx in range(len(df_raw)):
        row = df_raw.iloc[row_idx]
        # Stringify all values; treat NaN / "nan" as empty
        row_strs = [str(v).strip() for v in row]
        non_empty = [
            (i, v) for i, v in enumerate(row_strs)
            if v and v.lower() not in ("nan", "none")
        ]

        # Empty row → skip (spacer between events)
        if not non_empty:
            continue

        norm_strs = [_normalize(v) for v in row_strs]

        # ── Header row detection ──────────────────────────────────
        # A header row contains "série" or "serie" as one of the cell values.
        if any(nv in _HEADER_MARKERS for nv in norm_strs):
            col_map = {}
            for ci, nv in enumerate(norm_strs):
                if nv in ("serie", "série"):
                    col_map["serie"] = ci
                elif nv == "raia":
                    col_map["raia"] = ci
                elif nv in ("matricula", "matrícula"):
                    col_map["matricula"] = ci
                elif nv in ("nome", "nome completo"):
                    col_map["nome"] = ci
                elif nv == "minutos":
                    col_map["min"] = ci
                elif nv == "segundos":
                    col_map["seg"] = ci
                elif nv in ("centesimos", "centésimos"):
                    col_map["cent"] = ci
            continue

        # ── Event title row detection ─────────────────────────────
        # The merged title cell produces exactly one non-empty value in column 0.
        # Guard: make sure it's non-numeric text (not a lone série number like "1").
        if len(non_empty) == 1 and non_empty[0][0] == 0:
            raw_title = non_empty[0][1]
            if not raw_title.replace(".", "", 1).isdigit():
                if "serie" in _normalize(raw_title) or "série" in raw_title.lower():
                    pass # It's a "Série 1 de 2" separator row, do not reset col_map
                else:
                    # Non-numeric single-cell row → event title
                    import re
                    clean_title = re.sub(r'\s*\(.*?\)\s*$', '', raw_title)
                    norm_name = _normalize(clean_title)   # strips emoji, lowercases
                    current_event = events_by_name.get(norm_name)
                    col_map = None   # reset — next header row will set it
            continue

        # ── Data row ─────────────────────────────────────────────
        if col_map is None or "matricula" not in col_map:
            continue

        registration = row_strs[col_map["matricula"]]
        if not registration or registration.lower() in ("nan", "", "none"):
            continue

        min_raw  = row_strs[col_map["min"]]  if "min"  in col_map else ""
        seg_raw  = row_strs[col_map["seg"]]  if "seg"  in col_map else ""
        cent_raw = row_strs[col_map["cent"]] if "cent" in col_map else ""

        if any(v.lower() in ("", "nan", "none", "-") for v in [min_raw, seg_raw, cent_raw]):
            continue

        line = row_idx + 1
        student = Student.query.filter_by(registration=registration).first()
        if not student:
            errors.append(f"Linha {line}: Matrícula '{registration}' não encontrada.")
            continue

        # Use event detected from title row; fall back to group-based lookup
        event = current_event or _event_for_student(student)
        if not event:
            errors.append(
                f"Linha {line}: Nenhuma prova encontrada para '{student.full_name}' "
                f"({student.school_year})."
            )
            continue

        key = (student.id, event.id)
        if key not in time_data:
            time_data[key] = {
                "min":  _safe_int(min_raw),
                "seg":  _safe_int(seg_raw),
                "cent": _safe_int(cent_raw),
            }


# ── CSV seeded-format parser ───────────────────────────────────────────

def _process_seeded_sheet(df, norm_cols, time_data, errors, events_by_name):
    """Parse the seeded CSV format (Série|Raia|Nome|Matrícula|…|Min|Seg|Cent)."""
    matricula_col = norm_cols.get("matricula") or norm_cols.get("matrícula")
    min_col  = norm_cols.get("minutos")
    seg_col  = norm_cols.get("segundos")
    cent_col = norm_cols.get("centesimos") or norm_cols.get("centésimos")

    if not all([matricula_col, min_col, seg_col, cent_col]):
        return

    for row_idx, df_row in df.iterrows():
        line = row_idx + 2
        registration = str(df_row.get(matricula_col, "")).strip()
        if not registration or registration.lower() in ("nan", "", "none"):
            continue

        min_raw  = str(df_row.get(min_col, "")).strip()
        seg_raw  = str(df_row.get(seg_col, "")).strip()
        cent_raw = str(df_row.get(cent_col, "")).strip()

        if any(v.lower() in ("", "nan", "none", "-") for v in [min_raw, seg_raw, cent_raw]):
            continue

        student = Student.query.filter_by(registration=registration).first()
        if not student:
            errors.append(f"Linha {line}: Matrícula '{registration}' não encontrada.")
            continue

        event = _event_for_student(student)
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


def _event_for_student(student):
    """Fallback: find the first event whose competition_group matches the student's school_year."""
    from services.seeding import YEAR_TO_GROUP
    student_group = YEAR_TO_GROUP.get(student.school_year)
    for event in Event.query.all():
        if event.competition_group and student_group in [g.strip() for g in event.competition_group.split(",")]:
            return event
    return None


# ── Legacy wide-format parser (backwards compatibility) ───────────────

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
