(() => {
  const API_BASE = `http://${window.location.hostname || 'localhost'}:8000/coordenacao`;
  const container = document.getElementById('coordination-requests');
  const enrollmentContainer = document.getElementById('coordination-enrollments');
  const studentContainer = document.getElementById('coordination-students');
  const actionContainer = document.getElementById('coordination-actions');
  const errorBox = document.getElementById('coordination-request-error');

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[character]);
  }

  async function apiRequest(path, options = {}) {
    const token = localStorage.getItem('ged_token');
    if (!token) throw new Error('Sessão inválida. Entre novamente no módulo Coordenação.');
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers
      }
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(body.detail)
        ? body.detail.map(item => item.msg).join('; ')
        : body.detail;
      throw new Error(detail || `Erro HTTP ${response.status}`);
    }
    return body;
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function renderRequests(items) {
    if (!items.length) {
      container.innerHTML = '<p class="text-muted">Não há solicitações de aproveitamento neste escopo.</p>';
      return;
    }
    container.innerHTML = `
      <table style="width:100%; min-width:900px; border-collapse:collapse;">
        <thead><tr>
          <th style="text-align:left; padding:10px;">Aluno / curso</th>
          <th style="text-align:left; padding:10px;">Estudo de origem</th>
          <th style="text-align:left; padding:10px;">Disciplina destino</th>
          <th style="text-align:left; padding:10px;">Carga / situação</th>
          <th style="text-align:left; padding:10px;">Parecer / decisão</th>
        </tr></thead>
        <tbody>${items.map(item => `
          <tr>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.student_name)}<br>
              <span class="text-muted">${escapeHtml(item.course_name)}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.source_discipline)}<br>
              <span class="text-muted">${escapeHtml(item.source_course)} — ${escapeHtml(item.source_institution)}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">${escapeHtml(item.target_discipline || '—')}</td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.workload_hours)} h / ${escapeHtml(item.credits)} créditos<br>
              <span class="text-muted">${escapeHtml(item.status)}</span>
            </td>
            <td style="padding:10px; vertical-align:top; min-width:240px;">
              ${item.status === 'pending' ? `
                <textarea data-decision-note="${escapeHtml(item.id)}" maxlength="2000" rows="2" style="width:100%;" aria-label="Parecer"></textarea>
                <div style="display:flex; gap:8px; margin-top:8px;">
                  <button class="btn-primary" type="button" data-decision-id="${escapeHtml(item.id)}" data-decision-status="approved">Aprovar</button>
                  <button class="btn-secondary" type="button" data-decision-id="${escapeHtml(item.id)}" data-decision-status="rejected">Rejeitar</button>
                </div>
              ` : `
                ${escapeHtml(item.decision_note || 'Sem parecer informado')}<br>
                <span class="text-muted">Responsável: ${escapeHtml(item.reviewer_id || '—')}</span>
              `}
            </td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  function renderPendingEnrollments(items) {
    if (!items.length) {
      enrollmentContainer.innerHTML = '<p class="text-muted">Não há matrículas pendentes neste escopo.</p>';
      return;
    }
    enrollmentContainer.innerHTML = `
      <table style="width:100%; min-width:760px; border-collapse:collapse;">
        <thead><tr>
          <th style="text-align:left; padding:10px;">Aluno</th>
          <th style="text-align:left; padding:10px;">Curso / disciplina</th>
          <th style="text-align:left; padding:10px;">Turma / período</th>
          <th style="text-align:left; padding:10px;">Situação / decisão</th>
        </tr></thead>
        <tbody>${items.map(item => `
          <tr>
            <td style="padding:10px; vertical-align:top;">${escapeHtml(item.student_name)}</td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.course_name)}<br>
              <span class="text-muted">${escapeHtml(item.discipline_name)}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.class_code)}<br>
              <span class="text-muted">${escapeHtml(item.term_name)}</span>
            </td>
            <td style="padding:10px; vertical-align:top; min-width:240px;">
              <span class="text-muted">${escapeHtml(item.status)}</span>
              <button class="btn-primary" type="button" data-enrollment-approval="${escapeHtml(item.id)}" style="margin-top:8px;">Aprovar matrícula</button>
            </td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  function renderStudents(items) {
    if (!items.length) {
      studentContainer.innerHTML = '<p class="text-muted">Não há vínculos acadêmicos neste escopo.</p>';
      return;
    }
    studentContainer.innerHTML = `
      <table style="width:100%; min-width:900px; border-collapse:collapse;">
        <thead><tr>
          <th style="text-align:left; padding:10px;">Aluno</th>
          <th style="text-align:left; padding:10px;">Curso</th>
          <th style="text-align:left; padding:10px;">Disciplina</th>
          <th style="text-align:left; padding:10px;">Turma / período</th>
          <th style="text-align:left; padding:10px;">Campus / situação</th>
        </tr></thead>
        <tbody>${items.map(item => `
          <tr>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.full_name)}<br>
              <span class="text-muted">${escapeHtml(item.student_id)}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">${escapeHtml(item.course)}</td>
            <td style="padding:10px; vertical-align:top;">${escapeHtml(item.discipline)}</td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.class)}<br>
              <span class="text-muted">${escapeHtml(item.term)}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.campus)}<br>
              <span class="text-muted">${escapeHtml(item.status)}</span>
            </td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  function renderActions(items) {
    if (!items.length) {
      actionContainer.innerHTML = '<p class="text-muted">Não há pendências neste escopo.</p>';
      return;
    }
    actionContainer.innerHTML = `
      <table style="width:100%; min-width:900px; border-collapse:collapse;">
        <thead><tr>
          <th style="text-align:left; padding:10px;">Aluno / curso</th>
          <th style="text-align:left; padding:10px;">Pendência</th>
          <th style="text-align:left; padding:10px;">Prioridade / prazo</th>
          <th style="text-align:left; padding:10px;">Situação / responsável</th>
        </tr></thead>
        <tbody>${items.map(item => `
          <tr>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.student_name)}<br>
              <span class="text-muted">${escapeHtml(item.course_name)} · ${escapeHtml(item.campus_name)}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.issue)}<br>
              <span class="text-muted">${escapeHtml(item.category)}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.priority)}<br>
              <span class="text-muted">${escapeHtml(item.deadline || 'Sem prazo')}</span>
            </td>
            <td style="padding:10px; vertical-align:top;">
              ${escapeHtml(item.status)}<br>
              <span class="text-muted">${escapeHtml(item.responsible)}</span>
              ${item.status !== 'concluída' ? `
                <div><button class="btn-secondary" type="button" data-action-resolve="${escapeHtml(item.id)}" data-action-student="${escapeHtml(item.student_id)}" data-action-course="${escapeHtml(item.course_id)}" style="margin-top:8px;">Concluir</button></div>
              ` : ''}
            </td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  async function loadRequests() {
    const result = await apiRequest('/solicitacoes-aproveitamento');
    renderRequests(result.items || []);
  }

  async function loadPendingEnrollments() {
    const result = await apiRequest('/matriculas-pendentes');
    renderPendingEnrollments(result.items || []);
  }

  async function loadStudents() {
    const result = await apiRequest('/alunos');
    renderStudents(result.items || []);
  }

  async function loadActions() {
    const result = await apiRequest('/pendencias');
    renderActions(result.items || []);
  }

  container.addEventListener('click', async event => {
    const button = event.target.closest('[data-decision-id]');
    if (!button) return;
    button.disabled = true;
    errorBox.hidden = true;
    try {
      const note = container.querySelector(`[data-decision-note="${CSS.escape(button.dataset.decisionId)}"]`);
      await apiRequest(
        `/solicitacoes-aproveitamento/${encodeURIComponent(button.dataset.decisionId)}/decisao`,
        {
          method: 'PATCH',
          body: JSON.stringify({
            status: button.dataset.decisionStatus,
            decision_note: note?.value.trim() || null
          })
        }
      );
      await loadRequests();
    } catch (error) {
      showError(error.message);
    } finally {
      button.disabled = false;
    }
  });

  enrollmentContainer.addEventListener('click', async event => {
    const button = event.target.closest('[data-enrollment-approval]');
    if (!button) return;
    button.disabled = true;
    errorBox.hidden = true;
    try {
      const enrollmentId = button.dataset.enrollmentApproval;
      await apiRequest(`/matriculas/${encodeURIComponent(enrollmentId)}/aprovar`, {
        method: 'POST'
      });
      await loadPendingEnrollments();
    } catch (error) {
      showError(error.message);
    } finally {
      button.disabled = false;
    }
  });

  actionContainer.addEventListener('click', async event => {
    const button = event.target.closest('[data-action-resolve]');
    if (!button) return;
    button.disabled = true;
    errorBox.hidden = true;
    try {
      const params = new URLSearchParams({
        course_id: button.dataset.actionCourse,
        action_id: button.dataset.actionResolve
      });
      await apiRequest(
        `/pendencias/${encodeURIComponent(button.dataset.actionStudent)}/resolver?${params}`,
        { method: 'POST' }
      );
      await loadActions();
    } catch (error) {
      showError(error.message);
    } finally {
      button.disabled = false;
    }
  });

  document.getElementById('coordination-request-reload').addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    try {
      await Promise.all([loadRequests(), loadPendingEnrollments()]);
    } catch (error) {
      showError(error.message);
    } finally {
      event.currentTarget.disabled = false;
    }
  });

  document.getElementById('coordination-enrollment-reload').addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    errorBox.hidden = true;
    try {
      await loadPendingEnrollments();
    } catch (error) {
      showError(error.message);
    } finally {
      event.currentTarget.disabled = false;
    }
  });

  document.getElementById('coordination-students-reload').addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    errorBox.hidden = true;
    try {
      await loadStudents();
    } catch (error) {
      showError(error.message);
    } finally {
      event.currentTarget.disabled = false;
    }
  });

  document.getElementById('coordination-actions-reload').addEventListener('click', async event => {
    event.currentTarget.disabled = true;
    errorBox.hidden = true;
    try {
      await loadActions();
    } catch (error) {
      showError(error.message);
    } finally {
      event.currentTarget.disabled = false;
    }
  });

  document.addEventListener('DOMContentLoaded', () => {
    loadRequests().catch(error => showError(error.message));
    loadPendingEnrollments().catch(error => showError(error.message));
    loadStudents().catch(error => showError(error.message));
    loadActions().catch(error => showError(error.message));
  });

  window.addEventListener('module-action-saved', event => {
    if (event.detail?.module === 'coordenacao') {
      loadActions().catch(error => showError(error.message));
    }
  });
})();
