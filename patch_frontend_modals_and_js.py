import os

FILE_PATH = "templates/cadastros.html"

with open(FILE_PATH, "r") as f:
    content = f.read()

# 1. Edit Student Modal: Add group dropdown
modal_student_search = """        <div class="form-group">
            <label for="edit-student-year">Ano Escolar / Equipe</label>
            <select id="edit-student-year">
                <option value="" disabled>Selecione...</option>
                <option>6º Ano</option>
                <option>7º Ano</option>
                <option>8º Ano</option>
                <option>9º Ano</option>
                <option>1º Ano Médio</option>
                <option>2º Ano Médio</option>
                <option>3º Ano Médio</option>
            </select>
        </div>
        <div id="edit-student-error" class="edit-modal-error" style="display:none;"></div>"""
modal_student_replace = """        <div class="form-group">
            <label for="edit-student-year">Ano Escolar / Equipe</label>
            <select id="edit-student-year">
                <option value="" disabled>Selecione...</option>
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
            <label for="edit-student-group">Turma (Opcional)</label>
            <select id="edit-student-group">
                <option value="">Sem Turma</option>
                {% for g in groups %}
                <option value="{{ g.id }}">{{ g.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div id="edit-student-error" class="edit-modal-error" style="display:none;"></div>"""
if modal_student_search in content:
    content = content.replace(modal_student_search, modal_student_replace)

# 2. Edit Event Modal: Add group dropdown
modal_event_search = """                {% endfor %}
            </div>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label for="edit-event-series">Nº de Séries</label>"""
modal_event_replace = """                {% endfor %}
            </div>
        </div>
        <div class="form-group">
            <label for="edit-event-group">Restrito à Turma (Opcional)</label>
            <select id="edit-event-group">
                <option value="">Qualquer Turma (Aberto)</option>
                {% for g in groups %}
                <option value="{{ g.id }}">{{ g.name }}</option>
                {% endfor %}
            </select>
        </div>
        <div class="form-row">
            <div class="form-group">
                <label for="edit-event-series">Nº de Séries</label>"""
if modal_event_search in content:
    content = content.replace(modal_event_search, modal_event_replace)


# 3. JS: openEditStudent
js_open_student_search = """function openEditStudent(id, name, registration, year, classroom) {
    document.getElementById('edit-student-id').value       = id;
    document.getElementById('edit-student-name').value     = name;
    document.getElementById('edit-student-reg').value      = registration;
    document.getElementById('edit-student-year').value     = year;
    document.getElementById('edit-student-class').value    = classroom;"""
js_open_student_replace = """function openEditStudent(id, name, registration, year, classroom, groupId) {
    document.getElementById('edit-student-id').value       = id;
    document.getElementById('edit-student-name').value     = name;
    document.getElementById('edit-student-reg').value      = registration;
    document.getElementById('edit-student-year').value     = year;
    document.getElementById('edit-student-class').value    = classroom;
    document.getElementById('edit-student-group').value    = groupId || '';"""
if js_open_student_search in content:
    content = content.replace(js_open_student_search, js_open_student_replace)

# 4. JS: submitEditStudent payload
js_submit_student_search1 = """    const school_year = document.getElementById('edit-student-year').value;
    const classroom   = document.getElementById('edit-student-class').value.trim();
    const errEl       = document.getElementById('edit-student-error');"""
js_submit_student_replace1 = """    const school_year = document.getElementById('edit-student-year').value;
    const classroom   = document.getElementById('edit-student-class').value.trim();
    const group_id    = document.getElementById('edit-student-group').value;
    const errEl       = document.getElementById('edit-student-error');"""
if js_submit_student_search1 in content:
    content = content.replace(js_submit_student_search1, js_submit_student_replace1)

js_submit_student_search2 = """            body: JSON.stringify({ full_name, registration, school_year, classroom }),"""
js_submit_student_replace2 = """            body: JSON.stringify({ full_name, registration, school_year, classroom, group_id }),"""
if js_submit_student_search2 in content:
    content = content.replace(js_submit_student_search2, js_submit_student_replace2)

# 5. JS: DOM updates after edit student
js_submit_student_search3 = """                document.getElementById(`s-class-${id}`).textContent = s.classroom || '—';
                document.getElementById(`s-year-${id}`).innerHTML  =
                    `<span class="badge badge-accent">${escHtml(s.school_year)}</span>`;
                // Re-wire edit button
                row.querySelector('.btn-ghost').setAttribute('onclick',
                    `openEditStudent(${s.id}, '${s.full_name.replace(/'/g,"\\\\'")}', '${s.registration}', '${s.school_year}', '${s.classroom}')`);"""
js_submit_student_replace3 = """                document.getElementById(`s-class-${id}`).textContent = s.classroom || '—';
                if(document.getElementById(`s-group-${id}`)) document.getElementById(`s-group-${id}`).textContent = s.group_name || '—';
                document.getElementById(`s-year-${id}`).innerHTML  =
                    `<span class="badge badge-accent">${escHtml(s.school_year)}</span>`;
                // Re-wire edit button
                row.querySelector('.btn-ghost').setAttribute('onclick',
                    `openEditStudent(${s.id}, '${s.full_name.replace(/'/g,"\\\\'")}', '${s.registration}', '${s.school_year}', '${s.classroom}', '${s.group_id || ''}')`);"""
if js_submit_student_search3 in content:
    content = content.replace(js_submit_student_search3, js_submit_student_replace3)

# 6. JS: openEditEvent
js_open_event_search = """function openEditEvent(id, name, group, numSeries, lanes) {
    document.getElementById('edit-event-id').value      = id;
    document.getElementById('edit-event-name').value    = name;
    const currentGroups = group ? group.split(',').map(g => g.trim()) : [];
    document.querySelectorAll('.edit-group-cb').forEach(cb => {
        cb.checked = currentGroups.includes(cb.value);
    });
    document.getElementById('edit-event-series').value  = numSeries;"""
js_open_event_replace = """function openEditEvent(id, name, group, numSeries, lanes, groupId) {
    document.getElementById('edit-event-id').value      = id;
    document.getElementById('edit-event-name').value    = name;
    const currentGroups = group ? group.split(',').map(g => g.trim()) : [];
    document.querySelectorAll('.edit-group-cb').forEach(cb => {
        cb.checked = currentGroups.includes(cb.value);
    });
    document.getElementById('edit-event-group').value   = groupId || '';
    document.getElementById('edit-event-series').value  = numSeries;"""
if js_open_event_search in content:
    content = content.replace(js_open_event_search, js_open_event_replace)

# 7. JS: submitEditEvent payload
js_submit_event_search1 = """    const competition_group  = Array.from(document.querySelectorAll('.edit-group-cb:checked')).map(cb => cb.value).join(',');
    const num_series         = parseInt(document.getElementById('edit-event-series').value) || 1;
    const athletes_per_series = parseInt(document.getElementById('edit-event-lanes').value) || 8;
    const errEl              = document.getElementById('edit-event-error');"""
js_submit_event_replace1 = """    const competition_group  = Array.from(document.querySelectorAll('.edit-group-cb:checked')).map(cb => cb.value).join(',');
    const group_id           = document.getElementById('edit-event-group').value;
    const num_series         = parseInt(document.getElementById('edit-event-series').value) || 1;
    const athletes_per_series = parseInt(document.getElementById('edit-event-lanes').value) || 8;
    const errEl              = document.getElementById('edit-event-error');"""
if js_submit_event_search1 in content:
    content = content.replace(js_submit_event_search1, js_submit_event_replace1)

js_submit_event_search2 = """            body: JSON.stringify({ name, competition_group, num_series, athletes_per_series }),"""
js_submit_event_replace2 = """            body: JSON.stringify({ name, competition_group, num_series, athletes_per_series, group_id }),"""
if js_submit_event_search2 in content:
    content = content.replace(js_submit_event_search2, js_submit_event_replace2)

# 8. JS: DOM updates after edit event
js_submit_event_search3 = """                document.getElementById(`e-group-${id}`).innerHTML =
                    `<span class="badge badge-accent" style="font-size:11px;">${escHtml(e.competition_group || '—')}</span>`;
                document.getElementById(`e-series-${id}`).textContent = `${e.num_series}×`;
                document.getElementById(`e-lanes-${id}`).textContent  = e.athletes_per_series;
                // Re-wire edit button
                row.querySelector('.btn-ghost').setAttribute('onclick',
                    `openEditEvent(${e.id}, '${e.name.replace(/'/g,"\\\\'")}', '${e.competition_group}', ${e.num_series}, ${e.athletes_per_series})`);"""
js_submit_event_replace3 = """                document.getElementById(`e-group-${id}`).innerHTML =
                    `<span class="badge badge-accent" style="font-size:11px;">${escHtml(e.competition_group || '—')}</span>`;
                if(document.getElementById(`e-restricted-group-${id}`)) document.getElementById(`e-restricted-group-${id}`).innerHTML = 
                    `<span style="font-size:12px; color:var(--text-muted);">${e.group_name || 'Aberto'}</span>`;
                document.getElementById(`e-series-${id}`).textContent = `${e.num_series}×`;
                document.getElementById(`e-lanes-${id}`).textContent  = e.athletes_per_series;
                // Re-wire edit button
                row.querySelector('.btn-ghost').setAttribute('onclick',
                    `openEditEvent(${e.id}, '${e.name.replace(/'/g,"\\\\'")}', '${e.competition_group}', ${e.num_series}, ${e.athletes_per_series}, '${e.group_id || ''}')`);"""
if js_submit_event_search3 in content:
    content = content.replace(js_submit_event_search3, js_submit_event_replace3)

with open(FILE_PATH, "w") as f:
    f.write(content)

print("Patch applied to JS & modals")
