"""
Balizamento: seeded XLSX export (one tab per competition group).

Sheet layout (one row per lane):
  Série | Raia | Nome | Matrícula | Ano Escolar | Sala | Minutos | Segundos | Centésimos
"""

import io
from collections import defaultdict
from flask import Blueprint, render_template, send_file, request
from flask_login import login_required
from models import Student, Event
from services.seeding import build_series, COMPETITION_GROUPS, YEAR_TO_GROUP

balizamento_bp = Blueprint("balizamento", __name__)

BASE_COLS = ["Série", "Raia", "Nome", "Matrícula", "Ano Escolar", "Sala"]
TIME_COLS = ["Minutos", "Segundos", "Centésimos"]
HEADER = BASE_COLS + TIME_COLS

# ── Colour palette ────────────────────────────────────────────────────

TAB_COLOURS = {
    "6º e 7º Ano":  "163340",
    "8º e 9º Ano":  "163322",
    "Ensino Médio": "2D1A40",
}
SERIE_HEADER_COLOURS = {
    "6º e 7º Ano":  "0D2530",
    "8º e 9º Ano":  "0D2518",
    "Ensino Médio": "1E1030",
}
HEADER_BG      = "1C2230"
HEADER_FG      = "FFFFFF"
ACCENT_FG      = "00C9B1"
ODD_ROW_BG     = "1A2030"
EVEN_ROW_BG    = "141824"
SERIE_SEP_BG   = "0A1018"


# ── Route: preview page ───────────────────────────────────────────────

@balizamento_bp.route("/balizamento")
@login_required
def balizamento():
    students = Student.query.order_by(Student.school_year, Student.full_name).all()
    events   = Event.query.order_by(Event.name).all()

    preview  = _build_preview(events, students)
    has_data = bool(students and events)

    # Stats per group for the UI
    group_stats = {}
    for group in COMPETITION_GROUPS:
        years = _years_for_group(group)
        group_stats[group] = {
            "students": len([s for s in students if s.school_year in years]),
            "events":   len([e for e in events if e.competition_group and group in [x.strip() for x in e.competition_group.split(",")] ]),
        }

    return render_template(
        "balizamento.html",
        students=students,
        events=events,
        preview=preview,
        has_data=has_data,
        competition_groups=COMPETITION_GROUPS,
        group_stats=group_stats,
    )


# ── Route: XLSX export ────────────────────────────────────────────────

@balizamento_bp.route("/balizamento/export/xlsx")
@login_required
def export_xlsx():
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    selected_groups = request.args.getlist("groups")  # multi-group selection
    selected_group  = request.args.get("group")       # legacy single-group
    selected_events = request.args.get("events")      # optional comma-sep event IDs

    students = Student.query.order_by(Student.school_year, Student.full_name).all()
    events   = Event.query.order_by(Event.name).all()

    # Filter events if requested
    if selected_events:
        try:
            ev_ids = {int(x) for x in selected_events.split(",")}
            events = [e for e in events if e.id in ev_ids]
        except ValueError:
            pass
    elif selected_groups:
        events = [e for e in events if e.competition_group and any(g.strip() in selected_groups for g in e.competition_group.split(","))]
    elif selected_group:
        events = [e for e in events if e.competition_group and selected_group in [g.strip() for g in e.competition_group.split(",")]]

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    grouped = defaultdict(list)
    for ev in events:
        if ev.competition_group:
            for g in ev.competition_group.split(","):
                g = g.strip()
                if selected_groups and g not in selected_groups: continue
                if selected_group and g != selected_group: continue
                grouped[g].append(ev)
        else:
            if not selected_groups and not selected_group:
                grouped["Sem Grupo"].append(ev)

    sheet_order = [g for g in COMPETITION_GROUPS if g in grouped]
    if "Sem Grupo" in grouped:
        sheet_order.append("Sem Grupo")

    for group_name in sheet_order:
        group_events = grouped[group_name]

        group_years    = _years_for_group(group_name)
        group_students = [s for s in students if s.school_year in group_years] if group_years else students

        ws = wb.create_sheet(title=_safe_sheet_name(group_name))
        tab_colour = TAB_COLOURS.get(group_name, "1C2230")
        ws.sheet_properties.tabColor = tab_colour

        # ── Styles ──────────────────────────────────────────────────
        header_fill   = PatternFill("solid", fgColor=HEADER_BG)
        accent_fill   = PatternFill("solid", fgColor=tab_colour)
        odd_fill      = PatternFill("solid", fgColor=ODD_ROW_BG)
        even_fill     = PatternFill("solid", fgColor=EVEN_ROW_BG)
        serie_hdr_bg  = SERIE_HEADER_COLOURS.get(group_name, "0D1828")
        serie_hdr_fill = PatternFill("solid", fgColor=serie_hdr_bg)
        sep_fill      = PatternFill("solid", fgColor=SERIE_SEP_BG)

        h_font_base  = Font(bold=True, color=ACCENT_FG, size=10)
        h_font_time  = Font(bold=True, color=HEADER_FG, size=10)
        data_font    = Font(color=HEADER_FG, size=10)
        serie_font   = Font(bold=True, color=ACCENT_FG, size=9, italic=True)
        center       = Alignment(horizontal="center", vertical="center", wrap_text=True)
        left_align   = Alignment(horizontal="left",   vertical="center")

        thin = Border(
            bottom=Side(border_style="thin", color="2D3748"),
            right=Side(border_style="thin",  color="2D3748"),
        )
        thick_top = Border(
            top=Side(border_style="medium", color="00C9B1"),
            bottom=Side(border_style="thin", color="2D3748"),
            right=Side(border_style="thin",  color="2D3748"),
        )

        current_row = 1

        for ev in group_events:
            # ── Event title row ──────────────────────────────────────
            title_cell = ws.cell(row=current_row, column=1,
                                 value=f"🏁  {ev.name}   ({ev.num_series} série(s) × {ev.athletes_per_series} raias)")
            title_cell.font      = Font(bold=True, color=ACCENT_FG, size=12)
            title_cell.fill      = PatternFill("solid", fgColor=HEADER_BG)
            title_cell.alignment = left_align
            ws.merge_cells(start_row=current_row, start_column=1,
                           end_row=current_row, end_column=len(HEADER))
            ws.row_dimensions[current_row].height = 30
            current_row += 1

            # ── Column header row ────────────────────────────────────
            for col_idx, col_name in enumerate(HEADER, start=1):
                cell = ws.cell(row=current_row, column=col_idx, value=col_name)
                cell.fill      = accent_fill if col_idx <= len(BASE_COLS) else header_fill
                cell.font      = h_font_base if col_idx <= len(BASE_COLS) else h_font_time
                cell.alignment = center
                cell.border    = thin
            ws.row_dimensions[current_row].height = 36
            ws.freeze_panes = ws.cell(row=current_row + 1, column=3)
            current_row += 1

            # ── Seeded data rows (with serie separators) ─────────────
            ev_students = [s for s in group_students if ev.group_id is None or s.group_id == ev.group_id]
            all_series = build_series(ev, ev_students, event_group=group_name)

            for series_idx, series in enumerate(all_series, start=1):
                # ── Serie header row ─────────────────────────────────
                serie_label = f"  Série {series_idx} de {len(all_series)}"
                serie_cell  = ws.cell(row=current_row, column=1, value=serie_label)
                serie_cell.font      = serie_font
                serie_cell.fill      = serie_hdr_fill
                serie_cell.alignment = left_align
                ws.merge_cells(start_row=current_row, start_column=1,
                               end_row=current_row, end_column=len(HEADER))
                ws.row_dimensions[current_row].height = 16
                current_row += 1

                for lane_idx, student in enumerate(series, start=1):
                    row_fill  = odd_fill if (current_row % 2 == 0) else even_fill
                    row_data  = [
                        series_idx,
                        lane_idx,
                        student.full_name   if student else "",
                        student.registration if student else "",
                        student.school_year  if student else "",
                        student.classroom or "" if student else "",
                        "",  # Minutos
                        "",  # Segundos
                        "",  # Centésimos
                    ]
                    use_thick = lane_idx == 1
                    for col_idx, value in enumerate(row_data, start=1):
                        cell = ws.cell(row=current_row, column=col_idx, value=value)
                        cell.fill      = row_fill
                        cell.font      = data_font
                        cell.border    = thick_top if use_thick else thin
                        cell.alignment = center if col_idx <= 2 else left_align
                    ws.row_dimensions[current_row].height = 22
                    current_row += 1

                # ── Spacer between series (not after the last) ───────
                if series_idx < len(all_series):
                    for col_idx in range(1, len(HEADER) + 1):
                        sep_cell      = ws.cell(row=current_row, column=col_idx)
                        sep_cell.fill = sep_fill
                    ws.row_dimensions[current_row].height = 5
                    current_row += 1

            # ── Blank spacer between events ──────────────────────────
            current_row += 2

        # ── Column widths ────────────────────────────────────────────
        col_widths = [8, 8, 28, 14, 18, 10, 12, 12, 14]
        for i, w in enumerate(col_widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    # Build a descriptive filename
    if selected_groups and len(selected_groups) == 1:
        safe_name = selected_groups[0].replace(" ", "_").replace("º", "").replace("°", "")
        filename  = f"balizamento_{safe_name}.xlsx"
    elif selected_group:
        safe_name = selected_group.replace(" ", "_").replace("º", "").replace("°", "")
        filename  = f"balizamento_{safe_name}.xlsx"
    else:
        filename = "balizamento_completo.xlsx"

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


# ── Helpers ───────────────────────────────────────────────────────────

def _build_preview(events, students):
    """Return {group: [(event, series_list)]} for template preview."""
    grouped = defaultdict(list)
    for ev in events:
        if ev.competition_group:
            for g in ev.competition_group.split(","):
                key = g.strip()
                group_years    = _years_for_group(key)
                group_students = [s for s in students if s.school_year in group_years] if group_years else students
                ev_students    = [s for s in group_students if ev.group_id is None or s.group_id == ev.group_id]
                series_list    = build_series(ev, ev_students, event_group=key)
                grouped[key].append((ev, series_list))
        else:
            key = "Sem Grupo"
            group_years = _years_for_group(key)
            group_students = [s for s in students if s.school_year in group_years] if group_years else students
            ev_students    = [s for s in group_students if ev.group_id is None or s.group_id == ev.group_id]
            series_list = build_series(ev, ev_students, event_group=key)
            grouped[key].append((ev, series_list))
    return dict(grouped)


def _years_for_group(group: str) -> list[str]:
    return [y for y, g in YEAR_TO_GROUP.items() if g == group]


def _safe_sheet_name(name: str) -> str:
    bad   = r'\/*?:[]'
    clean = "".join(c for c in name if c not in bad)
    return clean[:31]
