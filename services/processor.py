"""
Core business logic: wide-format CSV/Excel processing, time conversion,
ranking per (event, corrida_num, school_year), and points distribution.

Expected spreadsheet columns (wide format — one row per student):
  Nome | Matrícula | Ano Escolar | {Event} - Corrida 1 - Minutos | … Segundos | … Centésimos | …
"""

import re
import unicodedata
import pandas as pd
from collections import defaultdict

from extensions import db
from models import Student, Event, Result

# Points table: placement → points
POINTS_TABLE = {1: 10, 2: 8, 3: 7, 4: 6, 5: 5, 6: 4, 7: 3, 8: 2, 9: 1}

DQ_MINUTES = 9  # value in "Minutos" that signals DQ/absent


# ── Helpers ─────────────────────────────────────────────────────────

def _normalize(s: str) -> str:
    """Strip accents and lowercase for fuzzy column matching."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _is_dq(minutes: int) -> bool:
    return int(minutes) == DQ_MINUTES


def _convert_time(minutes: int, seconds: int, centesimos: int) -> float:
    return int(minutes) * 60 + int(seconds) + int(centesimos) / 100


def _assign_points(rank: int) -> int:
    return POINTS_TABLE.get(rank, 0)


# Column-name pattern: "{event_name} - Corrida {n} - {Minutos|Segundos|Centésimos}"
_COL_PATTERN = re.compile(
    r"^(.+)\s*-\s*corrida\s+(\d+)\s*-\s*(minuto|segundo|centesimo|cent)",
    re.IGNORECASE,
)

FIELD_MAP = {
    "minuto": "min",
    "segundo": "seg",
    "centesimo": "cent",
    "cent": "cent",
}


def _parse_time_columns(columns, events):
    """
    Return a dict:
      normalized_col_name → (event, corrida_num, field)
    where field ∈ {'min', 'seg', 'cent'}
    """
    event_by_norm = {_normalize(e.name): e for e in events}
    col_map = {}

    for col in columns:
        norm_col = _normalize(col)
        m = _COL_PATTERN.match(norm_col)
        if not m:
            continue
        event_norm = _normalize(m.group(1))
        corrida_num = int(m.group(2))
        field_prefix = m.group(3).lower().rstrip("s")  # "minuto", "segundo", "centesimo"

        if event_norm not in event_by_norm:
            continue

        field = FIELD_MAP.get(field_prefix, None)
        if field is None:
            continue

        col_map[col] = (event_by_norm[event_norm], corrida_num, field)

    return col_map


# ── Main entry point ─────────────────────────────────────────────────

def process_upload(filepath: str) -> dict:
    """
    Parse uploaded wide-format CSV or Excel, compute rankings and points,
    persist Results to DB, return summary dict.
    """
    # ── 1. Load file ─────────────────────────────────────────────────
    try:
        if filepath.lower().endswith(".csv"):
            df = pd.read_csv(filepath, dtype=str, encoding="utf-8-sig")
        else:
            df = pd.read_excel(filepath, dtype=str)
    except Exception as exc:
        return {"processed": 0, "errors": [f"Erro ao ler arquivo: {exc}"], "skipped": 0}

    # Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # ── 2. Verify base columns ────────────────────────────────────────
    base_required = {"Nome", "Matrícula", "Ano Escolar"}
    missing_base = base_required - set(df.columns)
    if missing_base:
        return {
            "processed": 0,
            "errors": [f"Colunas fixas não encontradas: {', '.join(sorted(missing_base))}"],
            "skipped": 0,
        }

    # ── 3. Identify time columns ─────────────────────────────────────
    events = Event.query.all()
    col_map = _parse_time_columns(df.columns.tolist(), events)

    if not col_map:
        return {
            "processed": 0,
            "errors": [
                "Nenhuma coluna de tempo reconhecida. "
                "Verifique se o arquivo foi gerado pelo sistema de Balizamento."
            ],
            "skipped": 0,
        }

    # ── 4. Parse rows ─────────────────────────────────────────────────
    errors = []
    # key: (student, event, corrida_num) → {min, seg, cent}
    time_data = defaultdict(lambda: {"min": None, "seg": None, "cent": None})

    for row_idx, df_row in df.iterrows():
        line = row_idx + 2

        registration = str(df_row.get("Matrícula", "")).strip()
        if not registration:
            errors.append(f"Linha {line}: Matrícula vazia — linha ignorada.")
            continue

        student = Student.query.filter_by(registration=registration).first()
        if not student:
            errors.append(f"Linha {line}: Matrícula '{registration}' não encontrada no sistema.")
            continue

        for col, (event, corrida_num, field) in col_map.items():
            raw = str(df_row.get(col, "")).strip()
            if not raw or raw.lower() in ("", "nan", "none", "-"):
                continue  # blank → skip this cell
            try:
                time_data[(student, event, corrida_num)][field] = int(float(raw))
            except ValueError:
                errors.append(f"Linha {line}, coluna '{col}': valor inválido '{raw}'.")

    # ── 5. Build result list (only complete min+seg+cent entries) ─────
    rows_to_process = []
    for (student, event, corrida_num), fields in time_data.items():
        if any(v is None for v in fields.values()):
            continue  # incomplete time — skip silently
        minutes, seconds, centesimos = fields["min"], fields["seg"], fields["cent"]
        dq = _is_dq(minutes)
        rows_to_process.append({
            "student": student,
            "event": event,
            "corrida_num": corrida_num,
            "minutes": minutes,
            "seconds": seconds,
            "centesimos": centesimos,
            "dq": dq,
            "total_time": _convert_time(minutes, seconds, centesimos) if not dq else None,
        })

    if not rows_to_process:
        return {"processed": 0, "errors": errors + ["Nenhum tempo válido encontrado no arquivo."], "skipped": 0}

    # ── 6. Clear previous results and persist ────────────────────────
    Result.query.delete()
    db.session.flush()

    result_objs = []
    for r in rows_to_process:
        res = Result(
            student_id=r["student"].id,
            event_id=r["event"].id,
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

    # ── 7. Rank within each (event, corrida_num, school_year) ─────────
    groups = defaultdict(list)
    for row_data, res_obj in result_objs:
        key = (row_data["event"].id, row_data["corrida_num"], row_data["student"].school_year)
        groups[key].append((row_data, res_obj))

    for key, group in groups.items():
        valid = [(r, o) for r, o in group if not r["dq"]]
        disqualified = [(r, o) for r, o in group if r["dq"]]

        valid.sort(key=lambda x: x[0]["total_time"])

        rank = 1
        for i, (row_data, res_obj) in enumerate(valid):
            if i > 0 and row_data["total_time"] == valid[i - 1][0]["total_time"]:
                pass  # tie — keep same rank
            else:
                rank = i + 1
            res_obj.placement = rank
            res_obj.points = _assign_points(rank)

        for _, res_obj in disqualified:
            res_obj.placement = None
            res_obj.points = 0

    db.session.commit()
    return {"processed": len(rows_to_process), "errors": errors, "skipped": 0}
