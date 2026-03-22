import os

FILE_PATH = "templates/cadastros.html"

with open(FILE_PATH, "r") as f:
    content = f.read()

# 1. Add Tab Button
tab_search = """    <button class="tab-btn" onclick="switchTab('provas', this)">
        🏁 Provas <span class="count-pill">{{ events | length }}</span>
    </button>
</div>"""
tab_replace = """    <button class="tab-btn" onclick="switchTab('provas', this)">
        🏁 Provas <span class="count-pill">{{ events | length }}</span>
    </button>
    <button class="tab-btn" onclick="switchTab('grupos', this)">
        👥 Turmas <span class="count-pill">{{ groups | length }}</span>
    </button>
</div>"""
content = content.replace(tab_search, tab_replace)

# 2. Add Group to Add Student Form
add_student_search = """                <div class="form-group">
                    <label for="school_year">Ano Escolar / Equipe</label>
                    <select id="school_year" name="school_year" required>
                        <option value="" disabled selected>Selecione...</option>
                        <option>6º Ano</option>
                        <option>7º Ano</option>
                        <option>8º Ano</option>
                        <option>9º Ano</option>
                        <option>1º Ano Médio</option>
                        <option>2º Ano Médio</option>
                        <option>3º Ano Médio</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary" """
add_student_replace = """                <div class="form-group">
                    <label for="school_year">Ano Escolar / Equipe</label>
                    <select id="school_year" name="school_year" required>
                        <option value="" disabled selected>Selecione...</option>
                        <option>6º Ano</option>
                        <option>7º Ano</option>
                        <option>8º Ano</option>
                        <option>9º Ano</option>
                        <option>1º Ano Médio</option>
                        <option>2º Ano Médio</option>
                        <option>3º Ano Médio</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="group_id">Turma</label>
                    <select id="group_id" name="group_id">
                        <option value="">Sem Turma</option>
                        {% for g in groups %}
                        <option value="{{ g.id }}">{{ g.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <button type="submit" class="btn btn-primary" """
content = content.replace(add_student_search, add_student_replace)

# 3. Add Group Column to Student Table Header
stu_th_search = """                            <th>Sala</th>
                            <th>Equipe</th>
                            <th style="text-align:right; width:80px;"></th>"""
stu_th_replace = """                            <th>Sala</th>
                            <th>Turma</th>
                            <th>Equipe</th>
                            <th style="text-align:right; width:80px;"></th>"""
content = content.replace(stu_th_search, stu_th_replace)

# 4. Add Group Column to Student Table Rows
stu_td_search = """                            <td id="s-class-{{ s.id }}" style="color:var(--text-muted);">{{ s.classroom or '—' }}</td>
                            <td id="s-year-{{ s.id }}"><span class="badge badge-accent">{{ s.school_year }}</span></td>
                            <td style="text-align:right;">
                                <div style="display:inline-flex; gap:4px;">
                                    <button class="btn btn-ghost btn-sm btn-icon" title="Editar aluno"
                                        onclick="openEditStudent({{ s.id }}, '{{ s.full_name | replace("'", "\\'") }}', '{{ s.registration }}', '{{ s.school_year }}', '{{ s.classroom or '' }}')">
                                        ✏️
                                    </button>"""
stu_td_replace = """                            <td id="s-class-{{ s.id }}" style="color:var(--text-muted);">{{ s.classroom or '—' }}</td>
                            <td id="s-group-{{ s.id }}" style="color:var(--text-muted);">{{ s.group.name if s.group else '—' }}</td>
                            <td id="s-year-{{ s.id }}"><span class="badge badge-accent">{{ s.school_year }}</span></td>
                            <td style="text-align:right;">
                                <div style="display:inline-flex; gap:4px;">
                                    <button class="btn btn-ghost btn-sm btn-icon" title="Editar aluno"
                                        onclick="openEditStudent({{ s.id }}, '{{ s.full_name | replace("'", "\\'") }}', '{{ s.registration }}', '{{ s.school_year }}', '{{ s.classroom or '' }}', '{{ s.group_id or '' }}')">
                                        ✏️
                                    </button>"""
content = content.replace(stu_td_search, stu_td_replace)

# 5. Add Group to Add Event Form
add_event_search = """                <div class="form-group">
                    <label>Grupos de Competição</label>
                    <div style="display:flex; flex-direction:column; gap:8px; padding:12px; background:var(--bg-card); border:1px solid var(--border); border-radius:8px;">
                        {% for group in competition_groups %}
                        <label style="display:flex; align-items:center; gap:8px; font-weight:normal; cursor:pointer; margin:0;">
                            <input type="checkbox" name="competition_group" value="{{ group }}" style="width:16px; height:16px;">
                            {{ group }}
                        </label>
                        {% endfor %}
                    </div>
                </div>
                <div class="form-row">"""
add_event_replace = """                <div class="form-group">
                    <label>Grupos de Competição</label>
                    <div style="display:flex; flex-direction:column; gap:8px; padding:12px; background:var(--bg-card); border:1px solid var(--border); border-radius:8px;">
                        {% for group in competition_groups %}
                        <label style="display:flex; align-items:center; gap:8px; font-weight:normal; cursor:pointer; margin:0;">
                            <input type="checkbox" name="competition_group" value="{{ group }}" style="width:16px; height:16px;">
                            {{ group }}
                        </label>
                        {% endfor %}
                    </div>
                </div>
                <div class="form-group">
                    <label for="event_group_id">Restrito à Turma (Opcional)</label>
                    <select id="event_group_id" name="group_id">
                        <option value="">Qualquer Turma (Aberto)</option>
                        {% for g in groups %}
                        <option value="{{ g.id }}">{{ g.name }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div class="form-row">"""
content = content.replace(add_event_search, add_event_replace)

# 6. Add Group to Event Headers
ev_th_search = """                            <th>Grupo</th>
                            <th>Séries</th>
                            <th>Raias</th>"""
ev_th_replace = """                            <th>Grupos Idade</th>
                            <th>Turma Restrita</th>
                            <th>Séries</th>
                            <th>Raias</th>"""
content = content.replace(ev_th_search, ev_th_replace)

# 7. Add Group to Event Rows
ev_td_search = """                            <td id="e-group-{{ e.id }}">
                                <span class="badge badge-accent" style="font-size:11px;">
                                    {{ e.competition_group or '—' }}
                                </span>
                            </td>
                            <td id="e-series-{{ e.id }}" style="color:var(--text-muted);">{{ e.num_series }}×</td>
                            <td id="e-lanes-{{ e.id }}" style="color:var(--text-muted);">{{ e.athletes_per_series }}</td>
                            <td style="text-align:right;">
                                <div style="display:inline-flex; gap:4px;">
                                    <button class="btn btn-ghost btn-sm btn-icon" title="Editar prova"
                                        onclick="openEditEvent({{ e.id }}, '{{ e.name | replace("'", "\\'") }}', '{{ e.competition_group or '' }}', {{ e.num_series }}, {{ e.athletes_per_series }})">
                                        ✏️
                                    </button>"""
ev_td_replace = """                            <td id="e-group-{{ e.id }}">
                                <span class="badge badge-accent" style="font-size:11px;">
                                    {{ e.competition_group or '—' }}
                                </span>
                            </td>
                            <td id="e-restricted-group-{{ e.id }}">
                                <span style="font-size:12px; color:var(--text-muted);">
                                    {{ e.group.name if e.group else 'Aberto' }}
                                </span>
                            </td>
                            <td id="e-series-{{ e.id }}" style="color:var(--text-muted);">{{ e.num_series }}×</td>
                            <td id="e-lanes-{{ e.id }}" style="color:var(--text-muted);">{{ e.athletes_per_series }}</td>
                            <td style="text-align:right;">
                                <div style="display:inline-flex; gap:4px;">
                                    <button class="btn btn-ghost btn-sm btn-icon" title="Editar prova"
                                        onclick="openEditEvent({{ e.id }}, '{{ e.name | replace("'", "\\'") }}', '{{ e.competition_group or '' }}', {{ e.num_series }}, {{ e.athletes_per_series }}, '{{ e.group_id or '' }}')">
                                        ✏️
                                    </button>"""
content = content.replace(ev_td_search, ev_td_replace)

# 8. Add Groups Tab Pane (at the end before edit student modal)
pane_grupos = """
<!-- ══════════════════════════════════════════
     TAB: GRUPOS
══════════════════════════════════════════ -->
<div class="tab-pane" id="pane-grupos">
    <div class="cadastro-layout">
        <div class="card cadastro-form-col">
            <div class="card-header">
                <div class="card-title">➕ Cadastrar Turma</div>
            </div>
            <form method="POST" action="{{ url_for('cadastros.add_group') }}">
                <div class="form-group">
                    <label for="group_name">Nome da Turma</label>
                    <input type="text" id="group_name" name="name"
                           placeholder="ex: Turma da Manhã, SESI" required autocomplete="off" />
                </div>
                <button type="submit" class="btn btn-primary" style="width:100%;">
                    Cadastrar Turma
                </button>
            </form>
        </div>

        <div class="card cadastro-list-col" style="padding:0; overflow:hidden;">
            <div class="card-header" style="padding:16px 20px;">
                <div class="card-title">👥 Turmas Cadastradas</div>
            </div>
            {% if groups %}
            <div class="table-wrapper" style="border:none; border-radius:0;">
                <table id="groups-table">
                    <thead>
                        <tr>
                            <th>Nome da Turma</th>
                            <th>Data de Criação</th>
                            <th style="text-align:right; width:80px;"></th>
                        </tr>
                    </thead>
                    <tbody id="groups-tbody">
                        {% for g in groups %}
                        <tr id="group-row-{{ g.id }}">
                            <td id="g-name-{{ g.id }}"><strong>{{ g.name }}</strong></td>
                            <td style="color:var(--text-muted);">{{ g.created_at.strftime('%d/%m/%Y') if g.created_at else '—' }}</td>
                            <td style="text-align:right;">
                                <div style="display:inline-flex; gap:4px;">
                                    <button class="btn btn-danger btn-sm btn-icon" title="Remover turma"
                                        onclick="confirmDelete('{{ url_for('cadastros.delete_group', group_id=g.id) }}', 'group-row-{{ g.id }}', '{{ g.name | replace("'", "\\'") }}')">
                                        🗑️
                                    </button>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="empty-state" style="padding:48px;">
                <span class="empty-state-icon">👥</span>
                <h3>Nenhuma Turma</h3>
                <p>Cadastre as turmas para organizar seus alunos.</p>
            </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- ══════════════════════════════════════════
     EDIT STUDENT MODAL
══════════════════════════════════════════ -->"""
edit_modals_start = "<!-- ══════════════════════════════════════════\n     EDIT STUDENT MODAL\n══════════════════════════════════════════ -->"
content = content.replace(edit_modals_start, pane_grupos)

with open(FILE_PATH, "w") as f:
    f.write(content)

print("Patch applied to cadastros.html")
