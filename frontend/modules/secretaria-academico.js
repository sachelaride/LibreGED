(() => {
  const API_BASE = `http://${window.location.hostname || 'localhost'}:8000/secretaria/academico`;
  const API_ROOT = `http://${window.location.hostname || 'localhost'}:8000`;
  const RESOURCE_PATHS = {
    campuses: '/campi',
    departments: '/departamentos',
    sectors: '/setores',
    courses: '/cursos',
    disciplines: '/disciplinas',
    terms: '/periodos',
    curricula: '/matrizes',
    staff: '/profissionais',
    rooms: '/salas',
    offerings: '/ofertas',
    classes: '/turmas',
    schedules: '/horarios',
    coordinator_assignments: '/responsabilidades-coordenacao'
  };
  const state = {};

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    })[character]);
  }

  function parseToken(token) {
    try {
      const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(decodeURIComponent(atob(base64).split('').map(character =>
        `%${(`00${character.charCodeAt(0).toString(16)}`).slice(-2)}`
      ).join('')));
    } catch (error) {
      return null;
    }
  }

  function checkSession() {
    const token = localStorage.getItem('ged_token');
    const payload = token ? parseToken(token) : null;
    if (!payload || payload.exp <= Math.floor(Date.now() / 1000) || payload.module !== 'secretaria') {
      window.location.replace('../login.html?module=secretaria');
      return null;
    }
    return token;
  }

  async function apiRequest(path, options = {}) {
    const token = checkSession();
    if (!token) throw new Error('Sessão inválida. Entre novamente no módulo Secretaria.');
    const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
    const response = await fetch(url, {
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

  function renderStats(summary = {}) {
    const labels = {
      campi: 'Campi / unidades',
      departamentos: 'Departamentos',
      setores: 'Setores',
      cursos: 'Cursos',
      disciplinas: 'Disciplinas',
      matrizes: 'Matrizes curriculares',
      periodos: 'Períodos letivos',
      ofertas: 'Ofertas',
      turmas: 'Turmas',
      professores: 'Professores',
      coordenadores: 'Coordenadores',
      salas: 'Salas e ambientes'
    };
    document.getElementById('catalog-stats').innerHTML = Object.entries(labels).map(([key, label]) => `
      <article class="glass-panel" style="padding:16px; border-left:3px solid var(--primary);">
        <div class="text-muted" style="font-size:11px; text-transform:uppercase; letter-spacing:.06em;">${label}</div>
        <strong style="display:block; font-size:1.55rem; margin-top:8px;">${escapeHtml(summary[key] ?? 0)}</strong>
      </article>
    `).join('');
  }

  function displayValue(value) {
    if (value === null || value === undefined || value === '') return '—';
    if (typeof value === 'boolean') return value ? 'Sim' : 'Não';
    if (Array.isArray(value)) return value.map(displayValue).join(', ');
    if (typeof value === 'object') return JSON.stringify(value);
    if (typeof value === 'string' && /^\d{4}-\d\d-\d\dT/.test(value)) return value.slice(0, 10);
    return String(value);
  }

  function renderLists() {
    const visibleFields = {
      campuses: ['name'],
      departments: ['code', 'name', 'campus_id', 'status'],
      sectors: ['code', 'name', 'department_name', 'status'],
      courses: ['code', 'name', 'degree', 'modality', 'duration_periods', 'status'],
      disciplines: ['code', 'name', 'workload_hours', 'credits', 'status'],
      terms: ['code', 'name', 'starts_on', 'ends_on', 'status'],
      curricula: ['course_id', 'version', 'effective_from', 'status', 'disciplines'],
      staff: ['staff_code', 'full_name', 'email', 'staff_type', 'status'],
      rooms: ['code', 'name', 'capacity', 'room_type', 'is_active'],
      offerings: ['course_name', 'discipline_name', 'term_name', 'capacity', 'status'],
      classes: ['code', 'course_name', 'discipline_name', 'term_name', 'teacher_name', 'coordinator_name', 'capacity', 'status'],
      schedules: ['class_code', 'discipline_name', 'weekday', 'starts_at', 'ends_at', 'room_name'],
      coordinator_assignments: ['coordinator_name', 'course_name', 'campus_name', 'starts_on', 'ends_on']
    };
    const historyEntityTypes = {
      offerings: 'oferta',
      classes: 'turma',
      schedules: 'horario',
      staff: 'profissional',
      coordinator_assignments: 'responsabilidade-coordenacao'
    };
    const labels = {
      code: 'Código',
      name: 'Nome',
      degree: 'Grau',
      modality: 'Modalidade',
      duration_periods: 'Períodos',
      status: 'Situação',
      workload_hours: 'Carga horária',
      credits: 'Créditos',
      starts_on: 'Início',
      ends_on: 'Término',
      coordinator_name: 'Coordenador',
      campus_name: 'Campus',
      course_id: 'Curso (ID)',
      campus_id: 'Campus (ID)',
      department_name: 'Departamento',
      course_name: 'Curso',
      discipline_name: 'Disciplina',
      term_name: 'Período',
      effective_from: 'Vigente desde',
      disciplines: 'Disciplinas vinculadas',
      staff_code: 'Código funcional',
      full_name: 'Nome completo',
      email: 'E-mail',
      user_id: 'Conta vinculada',
      staff_type: 'Função',
      capacity: 'Vagas/capacidade',
      room_type: 'Tipo',
      is_active: 'Ativa',
      teacher_name: 'Professor',
      coordinator_name: 'Coordenador',
      class_code: 'Turma',
      weekday: 'Dia',
      starts_at: 'Início',
      ends_at: 'Término',
      room_name: 'Ambiente'
    };
    Object.entries(visibleFields).forEach(([resource, fields]) => {
      const container = document.querySelector(`[data-list="${resource}"]`);
      if (!container) return;
      const records = state[resource] || [];
      if (!records.length) {
        container.innerHTML = '<p class="text-muted">Nenhum registro cadastrado.</p>';
        return;
      }
      const headers = fields.map(field => `<th>${escapeHtml(labels[field] || field)}</th>`).join('');
      const historyEntityType = historyEntityTypes[resource];
      const rows = records.map(record => `
        <tr>${fields.map(field => {
          let value = record[field];
          if (field === 'disciplines' && Array.isArray(value)) {
            value = value.map(item => {
              const prerequisites = (item.prerequisites || []).map(prerequisite => prerequisite.discipline_name).join(', ');
              const prerequisiteLabel = prerequisites ? `; pré-requisitos: ${prerequisites}` : '';
              const equivalences = (item.equivalences || []).map(equivalence => equivalence.discipline_name).join(', ');
              const equivalenceLabel = equivalences ? `; equivalentes: ${equivalences}` : '';
              const electiveLabel = item.elective_group
                ? `; optativa em ${item.elective_group.name} (${item.elective_group.minimum_credits} créditos mínimos)`
                : item.is_required ? '; obrigatória' : '; optativa sem grupo';
              return `${item.discipline_id.slice(0, 8)}… (período ${item.term_number}${prerequisiteLabel}${equivalenceLabel}${electiveLabel})`;
            }).join('; ');
          }
          if (field === 'weekday' && Number.isInteger(value)) {
            value = ['','Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo'][value];
          }
          return `<td>${escapeHtml(displayValue(value))}</td>`;
        }).join('')}${historyEntityType ? `
          <td><button class="btn-secondary" type="button" data-history-entity="${historyEntityType}" data-history-id="${escapeHtml(record.id)}" aria-label="Consultar histórico de alterações">Histórico</button></td>
        ` : ''}</tr>
      `).join('');
      container.innerHTML = `<table><thead><tr>${headers}${historyEntityType ? '<th>Alterações</th>' : ''}</tr></thead><tbody>${rows}</tbody></table>`;
    });
  }

  function renderAcademicChangeHistory(items) {
    const container = document.getElementById('academic-change-history');
    if (!items.length) {
      container.textContent = 'Nenhuma alteração registrada para este item.';
      return;
    }

    const actionLabels = {
      academic_offering_created: 'Oferta criada',
      academic_offering_updated: 'Oferta atualizada',
      academic_class_created: 'Turma criada',
      academic_class_updated: 'Turma atualizada',
      faculty_allocation_updated: 'Alocação docente atualizada',
      academic_schedule_created: 'Horário criado',
      academic_schedule_updated: 'Horário atualizado',
      academic_staff_created: 'Profissional cadastrado',
      academic_staff_updated: 'Profissional atualizado',
      academic_coordinator_assignment_created: 'Responsabilidade de coordenação criada',
      academic_coordinator_assignment_updated: 'Responsabilidade de coordenação atualizada'
    };
    const rows = items.map(item => {
      let details = item.details;
      try {
        details = typeof details === 'string' ? JSON.parse(details) : details;
      } catch {
        details = item.details;
      }
      const timestamp = item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '—';
      return `<tr>
        <td>${escapeHtml(timestamp)}</td>
        <td>${escapeHtml(actionLabels[item.action] || item.action)}</td>
        <td><pre style="white-space:pre-wrap; margin:0;">${escapeHtml(JSON.stringify(details, null, 2) || '—')}</pre></td>
      </tr>`;
    }).join('');
    container.innerHTML = `<table><thead><tr><th>Data</th><th>Evento</th><th>Alterações</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function updateSelects() {
    const optionConfig = {
      campuses: { label: item => item.name },
      students: { label: item => `${item.full_name} (${item.id.slice(0, 8)})` },
      departments: { label: item => `${item.code} — ${item.name}` },
      sectors: { label: item => `${item.code} — ${item.name}` },
      staff: { label: item => `${item.staff_code} — ${item.full_name} (${item.status})` },
      linkable_users: { label: item => item.username },
      courses: { label: item => `${item.code} — ${item.name}` },
      disciplines: { label: item => `${item.code} — ${item.name}` },
      'curriculum-prerequisites': { label: item => item.name },
      'curriculum-electives': { label: item => item.name },
      'curriculum-required-disciplines': { label: item => item.name },
      'recognition-curricula': { label: item => `${item.version} — ${item.effective_from}` },
      'recognition-disciplines': { label: item => item.name },
      terms: { label: item => `${item.code} — ${item.name}` },
      curricula: { label: item => `${item.version} — ${item.course_id}` },
      teachers: { label: item => `${item.staff_code} — ${item.full_name}` },
      coordinators: { label: item => `${item.staff_code} — ${item.full_name}` },
      rooms: { label: item => `${item.code} — ${item.name}` },
      offerings: { label: item => `${item.discipline_name} — ${item.term_name} (${item.course_name})` },
      classes: { label: item => `${item.code} — ${item.discipline_name}` },
      coordinator_assignments: {
        label: item => `${item.coordinator_name} — ${item.course_name} (${item.starts_on} a ${item.ends_on})`
      }
    };
    document.querySelectorAll('select[data-options]').forEach(select => {
      const key = select.dataset.options;
      const config = optionConfig[key];
      const items = (state[key] || []).filter(item =>
        !['teachers', 'coordinators'].includes(key) || item.status === 'ativo'
      );
      const allowEmpty = select.dataset.allowEmpty === 'true';
      const placeholder = allowEmpty ? '<option value="">Não atribuído</option>' : '<option value="">Selecione</option>';
      select.innerHTML = placeholder + items.map(item =>
        `<option value="${escapeHtml(item.id)}">${escapeHtml(config.label(item))}</option>`
      ).join('');
      select.disabled = !allowEmpty && items.length === 0;
    });
    updateCurriculumOptions();
    updateRecognitionOptions();
  }

  function setMatrixDisciplineOptions(select, curriculum, predicate) {
    const disciplineNames = new Map((state.disciplines || []).map(item => [item.id, `${item.code} — ${item.name}`]));
    const options = (curriculum?.disciplines || []).filter(predicate)
      .map(item => ({ id: item.discipline_id, label: disciplineNames.get(item.discipline_id) || item.discipline_id }));
    const selected = new Set([...select.selectedOptions].map(option => option.value));
    select.innerHTML = options.map(item =>
      `<option value="${escapeHtml(item.id)}"${selected.has(item.id) ? ' selected' : ''}>${escapeHtml(item.label)}</option>`
    ).join('');
    select.disabled = options.length === 0;
  }

  function updateCurriculumOptions() {
    const prerequisiteForm = document.querySelector('[data-result="curriculum-discipline"]');
    if (prerequisiteForm) {
      const curriculum = (state.curricula || []).find(
        item => item.id === prerequisiteForm.elements.namedItem('curriculum_id').value
      );
      const termNumber = Number(prerequisiteForm.elements.namedItem('term_number').value);
      setMatrixDisciplineOptions(
        prerequisiteForm.elements.namedItem('prerequisite_discipline_ids'),
        curriculum,
        item => item.term_number < termNumber
      );
    }

    document.querySelectorAll('[data-result="elective-group"], [data-result="curriculum-equivalence"]').forEach(form => {
      const curriculum = (state.curricula || []).find(
        item => item.id === form.elements.namedItem('curriculum_id').value
      );
      if (form.dataset.result === 'elective-group') {
        setMatrixDisciplineOptions(
          form.elements.namedItem('discipline_ids'),
          curriculum,
          item => !item.is_required && !item.elective_group
        );
      } else {
        setMatrixDisciplineOptions(
          form.elements.namedItem('discipline_id'),
          curriculum,
          item => item.is_required
        );
      }
    });
  }

  function updateRecognitionOptions() {
    const form = document.getElementById('credit-recognition-form');
    if (!form) return;
    const courseId = form.elements.namedItem('course_id').value;
    const curriculumSelect = form.elements.namedItem('curriculum_id');
    const selectedCurriculumId = curriculumSelect.value;
    const curricula = (state.curricula || []).filter(item => item.course_id === courseId);
    curriculumSelect.innerHTML = '<option value="">Selecione</option>' + curricula.map(item => `
      <option value="${escapeHtml(item.id)}"${item.id === selectedCurriculumId ? ' selected' : ''}>
        ${escapeHtml(item.version)} — ${escapeHtml(item.effective_from)}
      </option>
    `).join('');
    if (!curricula.some(item => item.id === curriculumSelect.value)) {
      curriculumSelect.value = curricula[0]?.id || '';
    }
    const curriculum = curricula.find(item => item.id === curriculumSelect.value);
    const disciplineSelect = form.elements.namedItem('discipline_id');
    const selectedDisciplineId = disciplineSelect.value;
    const disciplineNames = new Map((state.disciplines || []).map(item => [item.id, item.name]));
    const disciplines = curriculum?.disciplines || [];
    disciplineSelect.innerHTML = '<option value="">Selecione</option>' + disciplines.map(item => `
      <option value="${escapeHtml(item.discipline_id)}"${item.discipline_id === selectedDisciplineId ? ' selected' : ''}>
        ${escapeHtml(disciplineNames.get(item.discipline_id) || item.discipline_id)}
      </option>
    `).join('');
    if (!disciplines.some(item => item.discipline_id === disciplineSelect.value)) {
      disciplineSelect.value = '';
    }
    curriculumSelect.disabled = curricula.length === 0;
    disciplineSelect.disabled = disciplines.length === 0;
  }

  function renderCreditRecognitions() {
    const container = document.getElementById('credit-recognition-list');
    if (!container) return;
    const items = state.creditRecognitions || [];
    if (!items.length) {
      container.innerHTML = '<p class="text-muted">Nenhuma solicitação de aproveitamento registrada.</p>';
      return;
    }
    const statusLabels = { pending: 'Pendente', approved: 'Aprovada', rejected: 'Rejeitada' };
    container.innerHTML = `
      <h3>Solicitações registradas</h3>
      <table>
        <thead><tr><th>Aluno / destino</th><th>Estudos de origem</th><th>Carga / créditos</th><th>Status / decisão</th><th>Análise</th></tr></thead>
        <tbody>${items.map(item => `
          <tr>
            <td>${escapeHtml(item.student_name)}<br>${escapeHtml(item.course_name)} — ${escapeHtml(item.target_discipline)}</td>
            <td>${escapeHtml(item.source_discipline)}<br>${escapeHtml(item.source_course)}, ${escapeHtml(item.source_institution)}</td>
            <td>${escapeHtml(item.workload_hours)} h / ${escapeHtml(item.credits)} créditos</td>
            <td>${escapeHtml(statusLabels[item.status] || item.status)}${item.decision_note ? `<br>${escapeHtml(item.decision_note)}` : ''}</td>
            <td>${item.status === 'pending' ? `
              <textarea data-recognition-note="${escapeHtml(item.id)}" maxlength="2000" rows="2" aria-label="Observação da decisão"></textarea>
              <button class="btn-primary" type="button" data-recognition-id="${escapeHtml(item.id)}" data-recognition-status="approved">Aprovar</button>
              <button class="btn-secondary" type="button" data-recognition-id="${escapeHtml(item.id)}" data-recognition-status="rejected">Rejeitar</button>
            ` : `${escapeHtml(displayValue(item.decided_at))}<br>Responsável: ${escapeHtml(item.reviewer_id || '—')}`}</td>
          </tr>
        `).join('')}</tbody>
      </table>
    `;
  }

  function nestedValue(source, path) {
    return path.split('.').reduce((value, key) => value?.[key], source);
  }

  function populateProfileForm(form, data) {
    for (const field of form.elements) {
      if (!field.name) continue;
      if (field.name === 'habilitacoes') {
        field.value = (data?.habilitacao || [])
          .map(item => `${item.nome_habilitacao}|${item.data_habilitacao}`)
          .join('\n');
      } else {
        field.value = nestedValue(data, field.name) ?? '';
      }
    }
  }

  function transcriptProfilePayload(form) {
    const payload = {};
    for (const field of form.elements) {
      if (!field.name || field.name === 'course_id') continue;
      if (field.name === 'habilitacoes') {
        payload.habilitacao = field.value.split(/\r?\n/).map(line => line.trim()).filter(Boolean).map(line => {
          const [name, completionDate, ...extra] = line.split('|').map(value => value.trim());
          if (!name || !completionDate || extra.length) {
            throw new Error('Cada habilitação deve estar no formato nome|AAAA-MM-DD.');
          }
          return { nome_habilitacao: name, data_habilitacao: completionDate };
        });
        continue;
      }
      const path = field.name.split('.');
      let target = payload;
      for (const key of path.slice(0, -1)) {
        target[key] ||= {};
        target = target[key];
      }
      target[path[path.length - 1]] = field.value.trim();
    }
    return payload;
  }

  async function loadInstitutionTranscriptProfile() {
    const form = document.getElementById('institution-transcript-profile-form');
    const response = await apiRequest('/historico/perfil-institucional');
    populateProfileForm(form, response.profile || {});
  }

  async function loadCourseTranscriptProfile() {
    const form = document.getElementById('course-transcript-profile-form');
    const courseId = form.elements.namedItem('course_id').value;
    if (!courseId) {
      populateProfileForm(form, {});
      return;
    }
    const response = await apiRequest(
      `/cursos/${encodeURIComponent(courseId)}/perfil-historico`
    );
    populateProfileForm(form, response.profile || {});
  }

  async function loadStudentTranscriptEntry(form) {
    const studentId = form.elements.namedItem('student_id').value;
    const courseId = form.elements.namedItem('course_id').value;
    const entryDate = form.elements.namedItem('entry_date');
    const accessForm = form.elements.namedItem('access_form');
    if (!studentId || !courseId) {
      entryDate.value = '';
      accessForm.value = '';
      return;
    }

    const feedback = form.querySelector('.catalog-feedback');
    feedback.textContent = 'Consultando dados de ingresso...';
    feedback.style.color = 'var(--text-muted)';
    try {
      const response = await apiRequest(
        `/alunos/${encodeURIComponent(studentId)}/cursos/${encodeURIComponent(courseId)}/dados-ingresso-historico`
      );
      if (
        form.elements.namedItem('student_id').value !== studentId
        || form.elements.namedItem('course_id').value !== courseId
      ) return;
      entryDate.value = response.entry_date || '';
      accessForm.value = response.access_form || '';
      showFeedback(
        form,
        response.configured ? 'Dados de ingresso carregados.' : 'Ainda não há dados de ingresso cadastrados.'
      );
    } catch (error) {
      showFeedback(form, error.message, true);
    }
  }

  async function loadTeacherTranscriptProfile(form) {
    const staffId = form.elements.namedItem('staff_id').value;
    const title = form.elements.namedItem('titulacao');
    const cpf = form.elements.namedItem('cpf');
    const lattes = form.elements.namedItem('lattes');
    if (!staffId) {
      title.value = '';
      cpf.value = '';
      lattes.value = '';
      return;
    }

    const feedback = form.querySelector('.catalog-feedback');
    feedback.textContent = 'Consultando dados do docente...';
    feedback.style.color = 'var(--text-muted)';
    try {
      const response = await apiRequest(
        `/profissionais/${encodeURIComponent(staffId)}/dados-historico`
      );
      if (form.elements.namedItem('staff_id').value !== staffId) return;
      title.value = response.titulacao || '';
      cpf.value = '';
      cpf.placeholder = response.cpf_configured ? 'Já cadastrado; deixe vazio para manter' : '11 dígitos';
      lattes.value = '';
      lattes.placeholder = response.lattes_configured
        ? 'Já cadastrado; deixe vazio para manter'
        : 'https://lattes.cnpq.br/1234567890123456';
      showFeedback(
        form,
        response.configured ? 'Dados do docente carregados.' : 'Titulação ainda não cadastrada.'
      );
    } catch (error) {
      showFeedback(form, error.message, true);
    }
  }

  async function loadCatalog() {
    const requests = Object.entries(RESOURCE_PATHS).map(async ([key, path]) => {
      const result = await apiRequest(path);
      state[key] = result.items || [];
    });
    requests.push(apiRequest(`${API_ROOT}/api/students`).then(result => {
      state.students = result;
    }));
    requests.push(apiRequest('/aproveitamentos').then(result => {
      state.creditRecognitions = result.items || [];
    }));
    requests.push(apiRequest('/usuarios-vinculaveis').then(result => {
      state.linkable_users = result.items || [];
    }));
    requests.push(apiRequest('/resumo').then(result => renderStats(result.summary || {})));
    requests.push(loadInstitutionTranscriptProfile());
    await Promise.all(requests);
    state.teachers = (state.staff || []).filter(item => item.staff_type === 'professor');
    state.coordinators = (state.staff || []).filter(item => item.staff_type === 'coordenador');
    updateSelects();
    renderLists();
    renderCreditRecognitions();
  }

  function formPayload(form) {
    const payload = {};
    for (const field of form.elements) {
      if (!field.name) continue;
      const { name, value } = field;
      if (field.type === 'checkbox') {
        payload[name] = field.checked;
      } else if (field instanceof HTMLSelectElement && field.multiple) {
        payload[name] = [...field.selectedOptions].map(option => option.value);
      } else if (field.type === 'number') {
        payload[name] = Number(value);
      } else {
        payload[name] = value.trim();
      }
    }
    form.querySelectorAll('input[type="checkbox"]').forEach(field => {
      payload[field.name] = field.checked;
    });
    return payload;
  }

  function buildEndpoint(form, payload) {
    if (form.dataset.endpoint) return form.dataset.endpoint;
    return form.dataset.endpointTemplate.replace(/\{([^}]+)\}/g, (_match, field) =>
      encodeURIComponent(payload[field])
    );
  }

  function preparePayload(form, payload) {
    const result = form.dataset.result;
    if (result === 'credit-recognition') {
      const { student_id, ...body } = payload;
      return body;
    }
    if (result === 'staff-update') {
      const { staff_id, ...body } = payload;
      body.user_id = body.user_id || null;
      return body;
    }
    if (result === 'coordinator-assignment-update') {
      const { assignment_id, ...body } = payload;
      return body;
    }
    if (result === 'department-update' || result === 'sector-update') {
      const { department_id, sector_id, ...body } = payload;
      return body;
    }
    if (result === 'curriculum-equivalence') {
      return { equivalent_discipline_id: payload.equivalent_discipline_id };
    }
    if (result === 'elective-group') {
      const { curriculum_id, ...body } = payload;
      return body;
    }
    if (result === 'curriculum') {
      return {
        course_id: payload.course_id,
        version: payload.version,
        effective_from: payload.effective_from,
        disciplines: [{
          discipline_id: payload.discipline_id,
          term_number: payload.term_number,
          is_required: true
        }]
      };
    }
    if (result === 'curriculum-discipline' || result === 'schedule') {
      const { curriculum_id, class_id, ...body } = payload;
      return body;
    }
    return payload;
  }

  function showFeedback(form, message, isError = false) {
    const feedback = form.querySelector('.catalog-feedback');
    feedback.textContent = message;
    feedback.style.color = isError ? '#fca5a5' : '#6ee7b7';
  }

  document.querySelectorAll('.catalog-form').forEach(form => {
    if (form.dataset.result === 'staff-update') {
      const staffSelect = form.elements.namedItem('staff_id');
      const userSelect = form.elements.namedItem('user_id');
      staffSelect.addEventListener('change', async () => {
        const staffId = staffSelect.value;
        const staff = (state.staff || []).find(item => item.id === staffId);
        for (const field of ['staff_code', 'full_name', 'email', 'staff_type', 'status', 'campus_id']) {
          form.elements.namedItem(field).value = staff?.[field] || '';
        }
        try {
          const query = staffId ? `?staff_id=${encodeURIComponent(staffId)}` : '';
          const result = await apiRequest(`/usuarios-vinculaveis${query}`);
          const accounts = result.items || [];
          userSelect.innerHTML = '<option value="">Não vinculado</option>' + accounts.map(account =>
            `<option value="${escapeHtml(account.id)}">${escapeHtml(account.username)}</option>`
          ).join('');
          userSelect.value = staff?.user_id || '';
        } catch (error) {
          showFeedback(form, error.message, true);
        }
      });
    }
    if (
      form.id === 'institution-transcript-profile-form'
      || form.id === 'course-transcript-profile-form'
    ) {
      if (form.id === 'course-transcript-profile-form') {
        form.elements.namedItem('course_id').addEventListener('change', () => {
          loadCourseTranscriptProfile().catch(error => showFeedback(form, error.message, true));
        });
      }
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        try {
          const payload = transcriptProfilePayload(form);
          const path = form.id === 'institution-transcript-profile-form'
            ? '/historico/perfil-institucional'
            : `/cursos/${encodeURIComponent(form.elements.namedItem('course_id').value)}/perfil-historico`;
          await apiRequest(path, { method: 'PUT', body: JSON.stringify(payload) });
          showFeedback(form, 'Perfil regulatório salvo.');
        } catch (error) {
          showFeedback(form, error.message, true);
        } finally {
          submit.disabled = false;
        }
      });
      return;
    }
    if (form.id === 'curriculum-progress-form') {
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const studentId = form.elements.namedItem('student_id').value;
        const courseId = form.elements.namedItem('course_id').value;
        const feedback = form.querySelector('.catalog-feedback');
        const result = document.getElementById('curriculum-progress-result');
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        feedback.textContent = 'Consultando histórico acadêmico...';
        feedback.style.color = 'var(--text-muted)';
        result.replaceChildren();
        try {
          const progress = await apiRequest(
            `${API_BASE}/alunos/${encodeURIComponent(studentId)}/progresso?course_id=${encodeURIComponent(courseId)}`
          );
          const requiredRows = progress.required_disciplines.map(item => `
            <tr>
              <td>${escapeHtml(item.discipline_name)}</td>
              <td>${escapeHtml(item.credits)}</td>
              <td>${item.status === 'completed' ? 'Concluída' : 'Pendente'}</td>
            </tr>
          `).join('');
          const electiveRows = progress.elective_groups.map(group => `
            <tr>
              <td>${escapeHtml(group.name)}</td>
              <td>${escapeHtml(group.earned_credits)} / ${escapeHtml(group.minimum_credits)}</td>
              <td>${group.status === 'completed' ? 'Concluída' : 'Pendente'}</td>
            </tr>
          `).join('');
          result.innerHTML = `
            <h3>${escapeHtml(progress.student.full_name)} — ${escapeHtml(progress.course.name)}</h3>
            <p>Matriz ${escapeHtml(progress.curriculum.version)} ·
              ${escapeHtml(progress.credits.completed_total)} de ${escapeHtml(progress.credits.required_total)} créditos mínimos</p>
            <p><strong>${progress.eligible_to_complete ? 'Requisitos curriculares cumpridos' : 'Requisitos curriculares pendentes'}</strong></p>
            <h4>Disciplinas obrigatórias</h4>
            <table><thead><tr><th>Disciplina</th><th>Créditos</th><th>Situação</th></tr></thead><tbody>${requiredRows}</tbody></table>
            <h4>Grupos optativos</h4>
            ${electiveRows
              ? `<table><thead><tr><th>Grupo</th><th>Créditos cumpridos / exigidos</th><th>Situação</th></tr></thead><tbody>${electiveRows}</tbody></table>`
              : '<p>Nenhum grupo optativo cadastrado na matriz.</p>'}
          `;
          feedback.textContent = 'Progresso curricular atualizado.';
          feedback.style.color = '#6ee7b7';
        } catch (error) {
          feedback.textContent = error.message;
          feedback.style.color = '#fca5a5';
        } finally {
          submit.disabled = false;
        }
      });
      return;
    }
    if (form.id === 'academic-history-form') {
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const studentId = form.elements.namedItem('student_id').value;
        const courseId = form.elements.namedItem('course_id').value;
        const feedback = form.querySelector('.catalog-feedback');
        const result = document.getElementById('academic-history-result');
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        feedback.textContent = 'Consultando extrato acadêmico...';
        feedback.style.color = 'var(--text-muted)';
        result.replaceChildren();
        try {
          const history = await apiRequest(
            `${API_BASE}/alunos/${encodeURIComponent(studentId)}/historico?course_id=${encodeURIComponent(courseId)}`
          );
          const recordRows = history.records.map(item => `
            <tr>
              <td>${item.type === 'credit_recognition' ? 'Aproveitamento deferido' : 'Matrícula em turma'}</td>
              <td>${escapeHtml(item.discipline_name)}</td>
              <td>${escapeHtml(item.period || '—')}</td>
              <td>${escapeHtml(item.workload_hours)} h / ${escapeHtml(item.credits)} créditos</td>
              <td>${escapeHtml(item.result)} · ${escapeHtml(item.enrollment_status)}</td>
              <td>${escapeHtml(item.source)}${item.decision_note ? `<br>Decisão: ${escapeHtml(item.decision_note)}` : ''}${item.reviewer_id ? `<br>Responsável: ${escapeHtml(item.reviewer_id)}` : ''}</td>
            </tr>
          `).join('');
          const pendingRows = history.pending_recognitions.map(item => `
            <li>${escapeHtml(item.discipline_name)} — aguardando análise (origem: ${escapeHtml(item.source_discipline)})</li>
          `).join('');
          const blockerRows = history.official_history_blockers.map(item => `<li>${escapeHtml(item)}</li>`).join('');
          result.innerHTML = `
            <h3>${escapeHtml(history.student.full_name)} — ${escapeHtml(history.course.name)}</h3>
            <p>Matriz ${escapeHtml(history.curriculum.version)}</p>
            <p><strong>Extrato acadêmico informativo; não é documento oficial emitido segundo o padrão MEC.</strong></p>
            ${history.records.length
              ? `<table><thead><tr><th>Tipo</th><th>Disciplina</th><th>Período</th><th>Carga / créditos</th><th>Resultado</th><th>Origem / decisão</th></tr></thead><tbody>${recordRows}</tbody></table>`
              : '<p>Nenhum registro acadêmico vinculado a este curso.</p>'}
            ${pendingRows ? `<h4>Solicitações pendentes (não integralizadas)</h4><ul>${pendingRows}</ul>` : ''}
            <h4>Pendências para histórico oficial</h4><ul>${blockerRows}</ul>
          `;
          feedback.textContent = 'Extrato acadêmico atualizado.';
          feedback.style.color = '#6ee7b7';
        } catch (error) {
          feedback.textContent = error.message;
          feedback.style.color = '#fca5a5';
        } finally {
          submit.disabled = false;
        }
      });
      return;
    }
    if (form.id === 'transcript-identity-form') {
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const studentId = form.elements.namedItem('student_id').value;
        const feedback = form.querySelector('.catalog-feedback');
        const submit = form.querySelector('[type="submit"]');
        const identity = {};
        for (const field of form.elements) {
          if (field.name && field.name !== 'student_id') {
            identity[field.name] = field.value.trim() || null;
          }
        }
        submit.disabled = true;
        try {
          await apiRequest(
            `${API_BASE}/alunos/${encodeURIComponent(studentId)}/dados-historico`,
            { method: 'PATCH', body: JSON.stringify(identity) }
          );
          showFeedback(form, 'Dados de identificação salvos.');
        } catch (error) {
          showFeedback(form, error.message, true);
        } finally {
          submit.disabled = false;
        }
      });
      return;
    }
    if (form.id === 'transcript-entry-form') {
      const loadEntry = () => loadStudentTranscriptEntry(form);
      form.elements.namedItem('student_id').addEventListener('change', loadEntry);
      form.elements.namedItem('course_id').addEventListener('change', loadEntry);
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const studentId = form.elements.namedItem('student_id').value;
        const courseId = form.elements.namedItem('course_id').value;
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        try {
          await apiRequest(
            `/alunos/${encodeURIComponent(studentId)}/cursos/${encodeURIComponent(courseId)}/dados-ingresso-historico`,
            {
              method: 'PUT',
              body: JSON.stringify({
                entry_date: form.elements.namedItem('entry_date').value,
                access_form: form.elements.namedItem('access_form').value
              })
            }
          );
          showFeedback(form, 'Dados de ingresso salvos.');
        } catch (error) {
          showFeedback(form, error.message, true);
        } finally {
          submit.disabled = false;
        }
      });
      return;
    }
    if (form.id === 'teacher-transcript-profile-form') {
      const loadProfile = () => loadTeacherTranscriptProfile(form);
      form.elements.namedItem('staff_id').addEventListener('change', loadProfile);
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const staffId = form.elements.namedItem('staff_id').value;
        const submit = form.querySelector('[type="submit"]');
        submit.disabled = true;
        try {
          const profile = {
            titulacao: form.elements.namedItem('titulacao').value
          };
          const cpf = form.elements.namedItem('cpf').value.trim();
          const lattes = form.elements.namedItem('lattes').value.trim();
          if (cpf) profile.cpf = cpf;
          if (lattes) profile.lattes = lattes;
          await apiRequest(
            `/profissionais/${encodeURIComponent(staffId)}/dados-historico`,
            {
              method: 'PUT',
              body: JSON.stringify(profile)
            }
          );
          showFeedback(form, 'Dados do docente salvos.');
        } catch (error) {
          showFeedback(form, error.message, true);
        } finally {
          submit.disabled = false;
        }
      });
      return;
    }
    if (form.id === 'credit-recognition-form') {
      form.elements.namedItem('course_id').addEventListener('change', updateRecognitionOptions);
      form.elements.namedItem('curriculum_id').addEventListener('change', updateRecognitionOptions);
      form.dataset.result = 'credit-recognition';
    }
    if (form.dataset.result === 'curriculum-discipline') {
      form.elements.namedItem('curriculum_id').addEventListener('change', updateCurriculumOptions);
      form.elements.namedItem('term_number').addEventListener('input', updateCurriculumOptions);
    }
    if (form.dataset.result === 'elective-group' || form.dataset.result === 'curriculum-equivalence') {
      form.elements.namedItem('curriculum_id').addEventListener('change', updateCurriculumOptions);
    }
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const submit = form.querySelector('[type="submit"]');
      const payload = formPayload(form);
      const path = buildEndpoint(form, payload);
      const body = preparePayload(form, payload);
      submit.disabled = true;
      try {
        await apiRequest(path, { method: form.dataset.method || 'POST', body: JSON.stringify(body) });
        showFeedback(form, 'Cadastro salvo.');
        form.reset();
        form.querySelectorAll('input[type="checkbox"]').forEach(field => {
          field.checked = field.defaultChecked;
        });

        const coordinatorAssignmentForm = document.querySelector(
          '[data-result="coordinator-assignment-update"]'
        );
        coordinatorAssignmentForm?.elements.namedItem('assignment_id').addEventListener('change', event => {
          const assignment = (state.coordinator_assignments || []).find(
            item => item.id === event.currentTarget.value
          );
          if (!assignment) return;
          for (const field of ['coordinator_id', 'course_id', 'campus_id', 'starts_on', 'ends_on']) {
            coordinatorAssignmentForm.elements.namedItem(field).value = assignment[field] || '';
          }
        });

        document.getElementById('credit-recognition-list')?.addEventListener('click', async event => {
          const button = event.target.closest('[data-recognition-id]');
          if (!button) return;
          const feedback = document.querySelector('#credit-recognition-form .catalog-feedback');
          const note = document.querySelector(`[data-recognition-note="${CSS.escape(button.dataset.recognitionId)}"]`);
          button.disabled = true;
          try {
            await apiRequest(
              `/aproveitamentos/${encodeURIComponent(button.dataset.recognitionId)}/decisao`,
              {
                method: 'PATCH',
                body: JSON.stringify({
                  status: button.dataset.recognitionStatus,
                  decision_note: note?.value || null
                })
              }
            );
            showFeedback(document.getElementById('credit-recognition-form'), 'Decisão registrada.');
            await loadCatalog();
          } catch (error) {
            showFeedback(document.getElementById('credit-recognition-form'), error.message, true);
          } finally {
            button.disabled = false;
          }
        });
        await loadCatalog();
      } catch (error) {
        showFeedback(form, error.message, true);
      } finally {
        submit.disabled = false;
      }
    });
  });

  document.querySelector('.content-area').addEventListener('click', async event => {
    const button = event.target.closest('[data-history-entity]');
    if (!button) return;

    const output = document.getElementById('academic-change-history');
    button.disabled = true;
    output.textContent = 'Consultando histórico de alterações...';
    try {
      const entityType = encodeURIComponent(button.dataset.historyEntity);
      const entityId = encodeURIComponent(button.dataset.historyId);
      const response = await apiRequest(
        `/historico-alteracoes/${entityType}/${entityId}`
      );
      renderAcademicChangeHistory(response.items || []);
    } catch (error) {
      output.textContent = `Não foi possível consultar o histórico: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  });

  const token = checkSession();
  if (token) {
    loadCatalog().catch(error => {
      const alert = document.getElementById('catalog-error');
      alert.hidden = false;
      alert.textContent = `Não foi possível carregar os cadastros acadêmicos: ${error.message}`;
    });
  }
})();
