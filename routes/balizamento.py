"""
Export a wide-format Excel/CSV balizamento template.

New column layout (one row per student):
  Nome | Matrícula | Ano Escolar | {Event} - Corrida 1 - Min | … Seg | … Cent | {Event} - Corrida 2 - Min | … | …

This format is importable by Google Sheets, Excel, LibreOffice, etc.
"""

import io
import csv
import unicodedata

from flask import Blueprint, render_template, send_file
from models import Student, Event

balizamento_bp = Blueprint("balizamento", __name__)

SCHOOL_YEAR_ORDER = [
    "6º Ano", "7º Ano", "8º Ano", "9º Ano",
    "1º Ano Médio", "2º Ano Médio", "3º Ano Médio",
]
BASE_COLS = ["Nome", "Matrícula", "Ano Escolar"]
TIME_FIELDS = ["Minutos", "Segundos", "Centésimos"]


def _year_sort_key(sy: str) -> int:
    try:
        return SCHOOL_YEAR_ORDER.index(sy)
    except ValueError:
        return 99


def _col_name(event_name: str, corrida: int, field: str) -> str:
    """e.g.  '50m Livre - Corrida 1 - Minutos'"""
    return f"{event_name} - Corrida {corrida} - {field}"


def _build_header_and_rows(students, events):
    """
    Build (header_row, data_rows) in wide format.
    One data_row per student, sorted by school_year then name.
    """
    students_sorted = sorted(
        students,
        key=lambda s: (_year_sort_key(s.school_year), s.full_name),
    )
    events_sorted = sorted(events, key=lambda e: e.name)

    # Build header
    header = list(BASE_COLS)
    for event in events_sorted:
        for corrida in range(1, event.num_corridas + 1):
            for field in TIME_FIELDS:
                header.append(_col_name(event.name, corrida, field))

    # Build data rows
    rows = []
    for student in students_sorted:
        row = [student.full_name, student.registration, student.school_year]
        for event in events_sorted:
            for corrida in range(1, event.num_corridas + 1):
                row.extend(["", "", ""])  # Minutos, Segundos, Centésimos (blank)
        rows.append(row)

    return header, rows


# ── Routes ──────────────────────────────────────────────────────────

@balizamento_bp.route("/balizamento")
def balizamento():
    students = Student.query.order_by(Student.school_year, Student.full_name).all()
    events = Event.query.order_by(Event.name).all()
    header, _ = _build_header_and_rows(students, events) if (students and events) else ([], [])
    return render_template("balizamento.html", students=students, events=events, header=header)


@balizamento_bp.route("/balizamento/export")
def export_csv():
    """
    Stream a plain CSV file (UTF-8 with BOM) compatible with
    Excel, Google Sheets, LibreOffice Calc, etc.
    """
    students = Student.query.order_by(Student.school_year, Student.full_name).all()
    events = Event.query.order_by(Event.name).all()
    header, rows = _build_header_and_rows(students, events)

    # Build into a plain str first, then encode — avoids TextIOWrapper detach issues
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    csv_str = output.getvalue()
    output.close()

    # Add UTF-8 BOM so Excel auto-detects the encoding on Windows/Mac
    buf = io.BytesIO(b"\xef\xbb\xbf" + csv_str.encode("utf-8"))
    buf.seek(0)

    return send_file(
        buf,
        mimetype="text/csv",
        as_attachment=True,
        download_name="balizamento_template.csv",
    )


@balizamento_bp.route("/balizamento/export/xlsx")
def export_xlsx():
    """
    Stream a proper .xlsx file with styled headers and auto-column widths.
    This is the most compatible format for Google Sheets and Excel.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    students = Student.query.order_by(Student.school_year, Student.full_name).all()
    events = Event.query.order_by(Event.name).all()
    header, rows = _build_header_and_rows(students, events)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Balizamento"

    # ── Styles ──────────────────────────────────────────────────────
    base_fill   = PatternFill("solid", fgColor="1C2230")
    event_fills = [
        PatternFill("solid", fgColor="163340"),
        PatternFill("solid", fgColor="163322"),
    ]
    header_font = Font(bold=True, color="FFFFFF", size=10)
    accent_font = Font(bold=True, color="00C9B1", size=10)
    center      = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        bottom=Side(border_style="thin", color="2D3748"),
        right=Side(border_style="thin", color="2D3748"),
    )

    # ── Header row ──────────────────────────────────────────────────
    for col_idx, col_name in enumerate(header, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.alignment = center
        cell.border = thin_border

        if col_idx <= len(BASE_COLS):
            cell.fill = base_fill
            cell.font = accent_font
        else:
            # Alternate fill per event block so it's visually grouped
            # Find which event this column belongs to
            time_col_idx = col_idx - len(BASE_COLS) - 1  # 0-based among time cols
            events_sorted = sorted(events, key=lambda e: e.name)
            col_count = 0
            event_idx = 0
            for ev_i, ev in enumerate(events_sorted):
                block = ev.num_corridas * len(TIME_FIELDS)
                if time_col_idx < col_count + block:
                    event_idx = ev_i
                    break
                col_count += block
            cell.fill = event_fills[event_idx % len(event_fills)]
            cell.font = header_font

    ws.row_dimensions[1].height = 40

    # ── Freeze panes ────────────────────────────────────────────────
    ws.freeze_panes = "D2"

    # ── Data rows ───────────────────────────────────────────────────
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = thin_border
            if col_idx <= len(BASE_COLS):
                cell.alignment = Alignment(vertical="center")
            else:
                cell.alignment = center

    # ── Auto-width ──────────────────────────────────────────────────
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=0)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 30)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="balizamento_template.xlsx",
    )
