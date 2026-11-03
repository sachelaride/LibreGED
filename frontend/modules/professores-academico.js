(() => {
  const API_BASE = `http://${window.location.hostname || 'localhost'}:8000/professores`;
  const state = { classes: [], assessments: [] };
  const classSelect = document.getElementById('professor-class');
  const assessmentSelect = document.getElementById('professor-grade-assessment');
  const errorBox = document.getElementById('professor-academic-error');
  const statusLabels = {
    present: 'Presente',
    absent: 'Ausente',
    justified: 'Falta justificada',
    remote: 'Participação remota'
  };

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[character]);
  }

  function displayError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  async function apiRequest(path, options = {}) {
    const token = localStorage.getItem('ged_token');
    if (!token) throw new Error('Sessão inválida. Entre novamente no módulo Professores.');
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers
      }
    });
    const body = response.status === 204 ? {} : await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(body.detail)
        ? body.detail.map(item => item.msg).join('; ')
        : body.detail;
      throw new Error(detail || `Erro HTTP ${response.status}`);
    }
    return body;
  }

  function selectedClassId() {
    return classSelect.value;
  }

  function localDate() {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 10);
  }

  async function loadClasses() {
    const result = await apiRequest('/turmas');
    state.classes = result.items || [];
    const previous = selectedClassId();
    classSelect.innerHTML = '<option value="">Selecione uma turma atribuída</option>' + state.classes.map(item => `
      <option value="${escapeHtml(item.id)}">
        ${escapeHtml(item.code)} — ${escapeHtml(item.discipline_name)} (${escapeHtml(item.term_name)})
      </option>
    `).join('');
    classSelect.value = state.classes.some(item => item.id === previous)
      ? previous
      : (state.classes[0]?.id || '');
    classSelect.disabled = state.classes.length === 0;
    document.querySelectorAll('#professor-assessment-form input, #professor-assessment-form textarea, #professor-assessment-form button')
      .forEach(field => { field.disabled = state.classes.length === 0; });
    if (!state.classes.length) {
      document.getElementById('professor-assessments').innerHTML =
        '<p class="text-muted">Nenhuma turma atribuída a esta conta. Solicite à Secretaria o vínculo do usuário ao cadastro docente e à turma.</p>';
      document.getElementById('professor-grades').textContent = '';
      document.getElementById('professor-attendance').textContent = '';
      return;
    }
    await loadClassData();
  }

  async function loadAssessments() {
    const classId = selectedClassId();
    const result = await apiRequest(`/avaliacoes?class_id=${encodeURIComponent(classId)}`);
    state.assessments = result.items || [];
    const selectedAssessment = assessmentSelect.value;
    assessmentSelect.innerHTML = '<option value="">Selecione uma avaliação</option>' + state.assessments.map(item => `
      <option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} (máx. ${escapeHtml(item.max_score)})</option>
    `).join('');
    assessmentSelect.value = state.assessments.some(item => item.id === selectedAssessment)
      ? selectedAssessment
      : (state.assessments[0]?.id || '');
    assessmentSelect.disabled = state.assessments.length === 0;
    renderAssessments();
    await loadGrades();
  }

  function renderAssessments() {
    const container = document.getElementById('professor-assessments');
    if (!state.assessments.length) {
      container.innerHTML = '<p class="text-muted">Nenhuma avaliação cadastrada para esta turma.</p>';
      return;
    }
    container.innerHTML = `
      <table>
        <thead><tr><th>Avaliação</th><th>Máximo</th><th>Data</th><th>Ações</th></tr></thead>
        <tbody>${state.assessments.map(item => `
          <tr data-assessment-row="${escapeHtml(item.id)}">
            <td>
              <input data-field="name" aria-label="Nome da avaliação" value="${escapeHtml(item.name)}" maxlength="160">
              <textarea data-field="description" aria-label="Descrição" maxlength="2000" rows="2">${escapeHtml(item.description || '')}</textarea>
            </td>
            <td><input data-field="max_score" aria-label="Pontuação máxima" type="number" min="0.01" max="1000" step="0.01" value="${escapeHtml(item.max_score)}"></td>
            <td><input data-field="due_date" aria-label="Data prevista" type="date" value="${escapeHtml(item.due_date || '')}"></td>
            <td>
              <button class="btn-secondary" type="button" data-assessment-save="${escapeHtml(item.id)}">Salvar</button>
              <button class="btn-secondary" type="button" data-assessment-delete="${escapeHtml(item.id)}">Excluir</button>
            </td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  async function loadGrades() {
    const container = document.getElementById('professor-grades');
    const assessmentId = assessmentSelect.value;
    if (!assessmentId) {
      container.innerHTML = '<p class="text-muted">Cadastre ou selecione uma avaliação.</p>';
      return;
    }
    const result = await apiRequest(`/avaliacoes/${encodeURIComponent(assessmentId)}/notas`);
    const assessment = state.assessments.find(item => item.id === assessmentId);
    container.innerHTML = `
      <table>
        <thead><tr><th>Aluno</th><th>Nota / máximo ${escapeHtml(assessment?.max_score)}</th><th>Observação</th><th>Ações</th></tr></thead>
        <tbody>${(result.items || []).map(item => `
          <tr data-grade-row="${escapeHtml(item.enrollment_id)}">
            <td>${escapeHtml(item.full_name)}</td>
            <td><input data-field="score" aria-label="Nota de ${escapeHtml(item.full_name)}" type="number" min="0" max="${escapeHtml(assessment?.max_score)}" step="0.01" value="${item.score ?? ''}"></td>
            <td><input data-field="comment" aria-label="Observação da nota" maxlength="2000" value="${escapeHtml(item.comment || '')}"></td>
            <td>
              <button class="btn-secondary" type="button" data-grade-save="${escapeHtml(item.enrollment_id)}">Salvar</button>
              ${item.grade_id ? `<button class="btn-secondary" type="button" data-grade-delete="${escapeHtml(item.enrollment_id)}">Remover</button>` : ''}
            </td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  async function loadAttendance() {
    const classId = selectedClassId();
    const attendanceDate = document.getElementById('professor-attendance-date').value;
    if (!classId || !attendanceDate) return;
    const result = await apiRequest(
      `/turmas/${encodeURIComponent(classId)}/frequencia?attendance_date=${encodeURIComponent(attendanceDate)}`
    );
    const container = document.getElementById('professor-attendance');
    if (!(result.items || []).length) {
      container.innerHTML = '<p class="text-muted">Não há matrículas ativas nesta turma.</p>';
      return;
    }
    container.innerHTML = `
      <table>
        <thead><tr><th>Aluno</th><th>Situação</th><th>Observação</th><th>Ações</th></tr></thead>
        <tbody>${result.items.map(item => `
          <tr data-attendance-row="${escapeHtml(item.enrollment_id)}" data-recorded="${item.attendance_id ? 'true' : 'false'}">
            <td>${escapeHtml(item.full_name)}</td>
            <td><select data-field="status" aria-label="Frequência de ${escapeHtml(item.full_name)}">
              <option value="">Não registrado</option>
              ${Object.entries(statusLabels).map(([value, label]) => `
                <option value="${value}"${item.status === value ? ' selected' : ''}>${label}</option>
              `).join('')}
            </select></td>
            <td><input data-field="note" aria-label="Observação da frequência" maxlength="1000" value="${escapeHtml(item.note || '')}"></td>
            <td>
              <button class="btn-secondary" type="button" data-attendance-save="${escapeHtml(item.enrollment_id)}">Salvar</button>
              ${item.attendance_id ? `<button class="btn-secondary" type="button" data-attendance-delete="${escapeHtml(item.enrollment_id)}">Remover</button>` : ''}
            </td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  async function loadClassData() {
    if (!selectedClassId()) return;
    await loadAssessments();
    await loadAttendance();
  }

  async function runAction(button, action) {
    button.disabled = true;
    errorBox.hidden = true;
    try {
      await action();
    } catch (error) {
      displayError(error.message);
    } finally {
      button.disabled = false;
    }
  }

  document.getElementById('professor-assessment-form').addEventListener('submit', event => {
    event.preventDefault();
    const form = event.currentTarget;
    const submit = form.querySelector('[type="submit"]');
    runAction(submit, async () => {
      await apiRequest(`/turmas/${encodeURIComponent(selectedClassId())}/avaliacoes`, {
        method: 'POST',
        body: JSON.stringify({
          name: form.elements.namedItem('name').value.trim(),
          description: form.elements.namedItem('description').value.trim() || null,
          max_score: Number(form.elements.namedItem('max_score').value),
          due_date: form.elements.namedItem('due_date').value || null
        })
      });
      form.reset();
      await loadAssessments();
    });
  });

  document.getElementById('professor-assessments').addEventListener('click', event => {
    const saveButton = event.target.closest('[data-assessment-save]');
    const deleteButton = event.target.closest('[data-assessment-delete]');
    if (saveButton) {
      const row = saveButton.closest('[data-assessment-row]');
      runAction(saveButton, async () => {
        const value = field => row.querySelector(`[data-field="${field}"]`).value;
        await apiRequest(`/avaliacoes/${encodeURIComponent(saveButton.dataset.assessmentSave)}`, {
          method: 'PATCH',
          body: JSON.stringify({
            name: value('name').trim(),
            description: value('description').trim() || null,
            max_score: Number(value('max_score')),
            due_date: value('due_date') || null
          })
        });
        await loadAssessments();
      });
    } else if (deleteButton) {
      if (!window.confirm('Excluir esta avaliação? Lançamentos de nota precisam ser removidos antes.')) return;
      runAction(deleteButton, async () => {
        await apiRequest(`/avaliacoes/${encodeURIComponent(deleteButton.dataset.assessmentDelete)}`, {
          method: 'DELETE'
        });
        await loadAssessments();
      });
    }
  });

  assessmentSelect.addEventListener('change', () => {
    loadGrades().catch(error => displayError(error.message));
  });

  document.getElementById('professor-grades').addEventListener('click', event => {
    const saveButton = event.target.closest('[data-grade-save]');
    const deleteButton = event.target.closest('[data-grade-delete]');
    if (saveButton) {
      const row = saveButton.closest('[data-grade-row]');
      runAction(saveButton, async () => {
        const score = row.querySelector('[data-field="score"]').value;
        if (score === '') throw new Error('Informe uma nota antes de salvar.');
        await apiRequest(
          `/avaliacoes/${encodeURIComponent(assessmentSelect.value)}/notas/${encodeURIComponent(saveButton.dataset.gradeSave)}`,
          {
            method: 'PUT',
            body: JSON.stringify({
              score: Number(score),
              comment: row.querySelector('[data-field="comment"]').value.trim() || null
            })
          }
        );
        await loadGrades();
      });
    } else if (deleteButton) {
      runAction(deleteButton, async () => {
        await apiRequest(
          `/avaliacoes/${encodeURIComponent(assessmentSelect.value)}/notas/${encodeURIComponent(deleteButton.dataset.gradeDelete)}`,
          { method: 'DELETE' }
        );
        await loadGrades();
      });
    }
  });

  document.getElementById('professor-load-attendance').addEventListener('click', event => {
    runAction(event.currentTarget, loadAttendance);
  });

  document.getElementById('professor-attendance-date').addEventListener('change', () => {
    loadAttendance().catch(error => displayError(error.message));
  });

  document.getElementById('professor-attendance').addEventListener('click', event => {
    const saveButton = event.target.closest('[data-attendance-save]');
    const deleteButton = event.target.closest('[data-attendance-delete]');
    if (saveButton) {
      const row = saveButton.closest('[data-attendance-row]');
      runAction(saveButton, async () => {
        const attendanceStatus = row.querySelector('[data-field="status"]').value;
        if (!attendanceStatus) throw new Error('Selecione uma situação de frequência.');
        const attendanceDate = document.getElementById('professor-attendance-date').value;
        await apiRequest(
          `/turmas/${encodeURIComponent(selectedClassId())}/frequencia/${encodeURIComponent(saveButton.dataset.attendanceSave)}?attendance_date=${encodeURIComponent(attendanceDate)}`,
          {
            method: 'PUT',
            body: JSON.stringify({
              status: attendanceStatus,
              note: row.querySelector('[data-field="note"]').value.trim() || null
            })
          }
        );
        await loadAttendance();
      });
    } else if (deleteButton) {
      runAction(deleteButton, async () => {
        const attendanceDate = document.getElementById('professor-attendance-date').value;
        await apiRequest(
          `/turmas/${encodeURIComponent(selectedClassId())}/frequencia/${encodeURIComponent(deleteButton.dataset.attendanceDelete)}?attendance_date=${encodeURIComponent(attendanceDate)}`,
          { method: 'DELETE' }
        );
        await loadAttendance();
      });
    }
  });

  classSelect.addEventListener('change', () => {
    loadClassData().catch(error => displayError(error.message));
  });

  document.getElementById('professor-reload').addEventListener('click', event => {
    runAction(event.currentTarget, loadClasses);
  });

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('professor-attendance-date').value = localDate();
    loadClasses().catch(error => displayError(error.message));
  });
})();
