const moduleMeta = {
  admin: {
    title: 'Administração Geral',
    accent: '#8b5cf6',
    description: 'Governança do sistema, instituições, usuários e fluxos cruciais.',
    items: 'administração',
    endpoints: {
      dashboard: '/admin/dashboard',
      list: '/admin/usuarios',
    }
  },
  sead: {
    title: 'SEAD — Secretaria Acadêmica Digital',
    accent: '#5B7AFF',
    description: 'Atendimento acadêmico, matrículas, protocolos, histórico e documentos da vida do aluno.',
    items: 'alunos',
    endpoints: {
      dashboard: '/sead/dashboard',
      list: '/sead/alunos',
    }
  },
  ead: {
    title: 'EAD — Educação a Distância',
    accent: '#14b8a6',
    description: 'Polos, tutores, aulas virtuais, disciplinas e acompanhamento dos estudantes a distância.',
    items: 'polos',
    endpoints: {
      dashboard: '/ead/dashboard',
      list: '/ead/polos',
    }
  },
  secretaria: {
    title: 'Secretaria Acadêmica',
    accent: '#5B7AFF',
    description: 'Atendimento acadêmico, matrículas, estudantes e documentação.',
    items: 'alunos',
    endpoints: {
      dashboard: '/secretaria/dashboard',
      list: '/secretaria/alunos',
    }
  },
  professores: {
    title: 'Professores',
    accent: '#22c55e',
    description: 'Turmas, frequências, notas e acompanhamento didático.',
    items: 'turmas',
    endpoints: {
      dashboard: '/professores/dashboard',
      list: '/professores/turmas',
    }
  },
  ged: {
    title: 'GED e Documentos',
    accent: '#f59e0b',
    description: 'Documentos, versões, validação e gestão documental.',
    items: 'documentos',
    endpoints: {
      dashboard: '/ged/dashboard',
      list: '/ged/documentos',
    }
  },
  financeiro: {
    title: 'Financeiro',
    accent: '#10b981',
    description: 'Cobrança, boletos, pagamentos e fluxo financeiro.',
    items: 'boletos',
    endpoints: {
      dashboard: '/financeiro/dashboard',
      list: '/financeiro/boletos',
    }
  },
  coordenacao: {
    title: 'Coordenação',
    accent: '#a855f7',
    description: 'Acompanhamento acadêmico e pendências institucionais.',
    items: 'pendências',
    endpoints: {
      dashboard: '/coordenacao/dashboard',
      list: '/coordenacao/pendencias',
    }
  },
  aluno: {
    title: 'Portal do Aluno',
    accent: '#fb7185',
    description: 'Boletim, documentos, matrícula e acompanhamento do estudante.',
    items: 'boletim',
    endpoints: {
      dashboard: '/aluno/dashboard',
      list: '/aluno/boletim',
    }
  }
};

const API_URL = `http://${window.location.hostname || 'localhost'}:8000/api`;
const API_BASE_URL = API_URL.replace(/\/api$/, '');

function buildApiUrl(path) {
  if (!path) return API_BASE_URL;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch (error) {
    return null;
  }
}

function getAuthHeaders() {
  const token = localStorage.getItem('ged_token');
  return token ? { Authorization: 'Bearer ' + token } : {};
}

function statusBadgeClass(value) {
  if (!value) return 'status-badge neutral';
  const text = String(value).toLowerCase();
  if (text.includes('pendente') || text.includes('aguardando') || text.includes('pendência')) return 'status-badge warning';
  if (text.includes('ativo') || text.includes('validado') || text.includes('matriculado') || text.includes('quitado')) return 'status-badge success';
  if (text.includes('alto') || text.includes('crítico') || text.includes('revisão')) return 'status-badge danger';
  return 'status-badge neutral';
}

function resolveListItems(listData) {
  if (!listData) return [];
  if (Array.isArray(listData)) return listData;
  if (Array.isArray(listData.items)) return listData.items;
  if (listData.grades && typeof listData.grades === 'object') {
    return Object.entries(listData.grades).map(([label, value]) => ({ disciplina: label, nota: value }));
  }
  if (listData.items && typeof listData.items === 'object') {
    return toArray(listData.items);
  }
  if (typeof listData === 'object') {
    return toArray(listData).filter((entry) => typeof entry === 'object' && entry !== null);
  }
  return [];
}

function toArray(value) {
  if (Array.isArray(value)) return value;
  if (value && typeof value === 'object') return Object.values(value);
  return [];
}

function renderStats(stats) {
  const grid = document.getElementById('stats-grid');
  if (!grid) return;
  const entries = Object.entries(stats || {});
  grid.innerHTML = entries.map(([key, value]) => `
    <div class="glass-panel" style="padding: 18px; border-left: 4px solid ${moduleMeta[currentModule].accent};">
      <div style="font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: var(--text-muted);">${key.replace(/_/g, ' ')}</div>
      <div style="font-size: 2rem; font-weight: 800; margin-top: 8px;">${value}</div>
    </div>
  `).join('');
}

function renderPrimaryList(items) {
  const listEl = document.getElementById('primary-list');
  if (!listEl) return;
  const entries = toArray(items).slice(0, 7);
  if (!entries.length) {
    listEl.innerHTML = '<p class="text-muted">Nenhum registro disponível neste módulo.</p>';
    return;
  }

  const keys = Object.keys(entries[0] || {});
  const visibleKeys = keys.slice(0, 5);
  const headers = visibleKeys.map((key) => `<th>${key.replace(/_/g, ' ')}</th>`).join('');
  const rows = entries.map((row) => {
    const values = visibleKeys.map((key) => {
      const value = row[key];
      const isStatus = typeof value === 'string' && (value.toLowerCase().includes('pendente') || value.toLowerCase().includes('matriculado') || value.toLowerCase().includes('validado') || value.toLowerCase().includes('ativo'));
      return `<td>${isStatus ? `<span class="${statusBadgeClass(value)}">${value}</span>` : value ?? '-'}</td>`;
    }).join('');
    const rowId = row.student_id || row.document_id || row.invoice_id || row.class_id || row.name || row.id || JSON.stringify(row);
    return `<tr class="detail-row" data-row-key="${String(rowId).replace(/"/g, '&quot;')}" style="cursor:pointer;">${values}</tr>`;
  }).join('');

  listEl.innerHTML = `
    <div style="overflow:auto;">
      <table class="data-table" style="width:100%; min-width: 500px;">
        <thead><tr>${headers}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;

  listEl.querySelectorAll('.detail-row').forEach((row) => {
    row.addEventListener('click', () => {
      const rowKey = row.getAttribute('data-row-key');
      const item = entries.find((entry) => {
        const candidate = entry.student_id || entry.document_id || entry.invoice_id || entry.class_id || entry.name || entry.id || JSON.stringify(entry);
        return String(candidate) === rowKey;
      });
      if (item) renderDetailModal(item);
    });
  });
}

function renderDetailModal(item) {
  const overlay = document.createElement('div');
  overlay.style.position = 'fixed';
  overlay.style.inset = '0';
  overlay.style.background = 'rgba(15, 23, 42, 0.66)';
  overlay.style.display = 'flex';
  overlay.style.alignItems = 'center';
  overlay.style.justifyContent = 'center';
  overlay.style.zIndex = '1000';

  const modal = document.createElement('div');
  modal.style.width = 'min(720px, 92vw)';
  modal.style.maxHeight = '80vh';
  modal.style.overflowY = 'auto';
  modal.style.background = 'var(--panel-bg, #0f172a)';
  modal.style.border = '1px solid rgba(148, 163, 184, 0.2)';
  modal.style.borderRadius = '18px';
  modal.style.padding = '20px';
  modal.style.boxShadow = '0 25px 50px rgba(15, 23, 42, 0.5)';

  const title = item.full_name || item.title || item.name || item.student_id || item.document_id || 'Detalhes do registro';
  const entries = Object.entries(item || {}).filter(([key, value]) => value !== undefined && value !== null && value !== '');

  modal.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom: 16px;">
      <div>
        <div class="text-muted" style="font-size:12px; text-transform:uppercase; letter-spacing:.08em;">Detalhes</div>
        <h3 style="margin:8px 0 0;">${title}</h3>
      </div>
      <button type="button" class="btn-secondary btn-small" data-close-detail="true">Fechar</button>
    </div>
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px;">
      ${entries.map(([key, value]) => `
        <div style="padding:12px; border-radius:12px; background: rgba(148, 163, 184, 0.08); border: 1px solid rgba(148, 163, 184, 0.12);">
          <div class="text-muted" style="font-size: 11px; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 6px;">${key.replace(/_/g, ' ')}</div>
          <div style="font-weight:600; word-break: break-word;">${typeof value === 'string' && (value.toLowerCase().includes('pendente') || value.toLowerCase().includes('matriculado') || value.toLowerCase().includes('validado') || value.toLowerCase().includes('ativo')) ? `<span class="${statusBadgeClass(value)}">${value}</span>` : value}</div>
        </div>
      `).join('')}
    </div>
  `;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  const closeButton = overlay.querySelector('[data-close-detail]');
  closeButton.addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', (event) => {
    if (event.target === overlay) overlay.remove();
  });
}

const moduleActions = {
  admin: [
    { key: 'instituicao', label: 'Nova instituição', kind: 'form' },
    { key: 'usuario-admin', label: 'Usuário admin', kind: 'form' },
    { key: 'workflow', label: 'Workflow', kind: 'form' },
    { key: 'relatorio', label: 'Relatório', kind: 'refresh' }
  ],
  secretaria: [
    { key: 'novo-aluno', label: 'Novo aluno', kind: 'form' },
    { key: 'nova-matricula', label: 'Matrícula', kind: 'form' },
    { key: 'novo-documento', label: 'Documento', kind: 'form' },
    { key: 'relatorio', label: 'Relatório', kind: 'refresh' }
  ],
  professores: [
    { key: 'lancar-notas', label: 'Lançar notas', kind: 'form' },
    { key: 'frequencia', label: 'Frequência', kind: 'form' },
    { key: 'nova-turma', label: 'Turma', kind: 'form' },
    { key: 'relatorio', label: 'Relatório', kind: 'refresh' }
  ],
  ged: [
    { key: 'upload-doc', label: 'Upload', kind: 'form' },
    { key: 'validar-doc', label: 'Validar', kind: 'form' },
    { key: 'auditoria', label: 'Auditoria', kind: 'form' },
    { key: 'buscar-doc', label: 'Buscar', kind: 'refresh' }
  ],
  financeiro: [
    { key: 'gerar-boleto', label: 'Gerar boleto', kind: 'form' },
    { key: 'cobranca', label: 'Cobrança', kind: 'form' },
    { key: 'pagamento', label: 'Pagamento', kind: 'form' },
    { key: 'revisoes', label: 'Revisões acadêmicas', kind: 'refresh' },
    { key: 'extrato', label: 'Extrato', kind: 'refresh' }
  ],
  coordenacao: [
    { key: 'nova-pendencia', label: 'Pendência', kind: 'form' },
    { key: 'acompanhamento', label: 'Acompanhamento', kind: 'form' },
    { key: 'relatorio', label: 'Relatório', kind: 'refresh' },
    { key: 'validacao', label: 'Validação', kind: 'form' }
  ],
  aluno: [
    { key: 'consultar-boletim', label: 'Boletim', kind: 'form' },
    { key: 'documentos', label: 'Documentos', kind: 'refresh' },
    { key: 'matricula', label: 'Matrícula', kind: 'form' },
    { key: 'ajuda', label: 'Ajuda', kind: 'refresh' }
  ]
};

function ensureFormPanel() {
  const statsGrid = document.getElementById('stats-grid');
  if (!statsGrid || document.getElementById('module-form-panel')) return;

  const panel = document.createElement('div');
  panel.id = 'module-form-panel';
  panel.className = 'glass-panel';
  panel.style.padding = '20px';
  panel.style.marginBottom = '20px';
  panel.style.display = 'none';
  statsGrid.insertAdjacentElement('afterend', panel);
}

function showStatusMessage(message, type = 'info') {
  const panel = document.getElementById('module-form-panel');
  if (!panel) return;

  const statusNode = panel.querySelector('.module-form-status') || document.createElement('div');
  statusNode.className = 'module-form-status';
  statusNode.style.marginTop = '12px';
  statusNode.style.padding = '10px 12px';
  statusNode.style.borderRadius = '8px';
  statusNode.style.fontSize = '13px';
  statusNode.style.fontWeight = '600';
  statusNode.style.background = type === 'error' ? 'rgba(239,68,68,0.12)' : 'rgba(91,122,255,0.12)';
  statusNode.style.color = type === 'error' ? '#fca5a5' : '#dbeafe';
  statusNode.textContent = message;
  panel.appendChild(statusNode);
}

function openActionForm(actionKey, initialValues = {}) {
  ensureFormPanel();
  const panel = document.getElementById('module-form-panel');
  const actionMap = {
    'instituicao': {
      title: 'Nova instituição',
      endpoint: '/institutions',
      method: 'POST',
      fields: [
        { name: 'name', label: 'Nome da instituição', type: 'text', value: 'Instituto de Ensino Superior LibreGED' },
        { name: 'cnpj', label: 'CNPJ', type: 'text', value: '12.345.678/0001-90' },
        { name: 'legal_name', label: 'Razão social', type: 'text', value: 'IES LibreGED Ltda.' }
      ],
      transform: (formData) => ({
        name: formData.name,
        cnpj: formData.cnpj.replace(/[^0-9]/g, ''),
        legal_name: formData.legal_name
      })
    },
    'usuario-admin': {
      title: 'Criar usuário administrativo',
      endpoint: '/users',
      method: 'POST',
      fields: [
        { name: 'username', label: 'Usuário', type: 'text', value: 'coordgeral' },
        { name: 'email', label: 'E-mail', type: 'email', value: 'coordgeral@universidade.edu.br' },
        { name: 'role', label: 'Perfil', type: 'select', options: ['admin_global', 'admin_instituicao', 'operador'], value: 'admin_instituicao' },
        { name: 'password', label: 'Senha', type: 'password', value: 'novaSenha123' }
      ],
      transform: (formData) => ({
        username: formData.username,
        email: formData.email,
        role: formData.role,
        password: formData.password
      })
    },
    'workflow': {
      title: 'Novo workflow',
      endpoint: '/workflows',
      method: 'POST',
      fields: [
        { name: 'name', label: 'Nome do workflow', type: 'text', value: 'Cadastro Acadêmico' },
        { name: 'description', label: 'Descrição', type: 'text', value: 'Fluxo de matrícula e validação documental' },
        { name: 'status', label: 'Status', type: 'select', options: ['draft', 'active', 'archived'], value: 'draft' }
      ],
      transform: (formData) => ({
        name: formData.name,
        description: formData.description,
        status: formData.status
      })
    },
    'novo-aluno': {
      title: 'Novo aluno',
      endpoint: '/secretaria/alunos',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'Código do aluno', type: 'text', value: 'ALU-1003' },
        { name: 'full_name', label: 'Nome completo', type: 'text', value: 'Maria Oliveira' },
        { name: 'cpf', label: 'CPF', type: 'text', value: '111.222.333-44' },
        { name: 'email', label: 'E-mail', type: 'email', value: 'maria@universidade.edu.br' },
        { name: 'course', label: 'Curso', type: 'text', value: 'Engenharia de Software' },
        { name: 'campus', label: 'Campus', type: 'text', value: 'Campus Central' },
        { name: 'enrollment_status', label: 'Status da matrícula', type: 'select', options: ['matriculado', 'pendente', 'em análise'], value: 'matriculado' },
        { name: 'start_date', label: 'Data de ingresso', type: 'date', value: '2026-08-01' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        full_name: formData.full_name,
        cpf: formData.cpf,
        email: formData.email,
        course: formData.course,
        campus: formData.campus,
        enrollment_status: formData.enrollment_status,
        start_date: formData.start_date
      })
    },
    'nova-matricula': {
      title: 'Registrar matrícula',
      endpoint: '/secretaria/alunos',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'Código do aluno', type: 'text', value: 'ALU-1004' },
        { name: 'full_name', label: 'Nome completo', type: 'text', value: 'João Pereira' },
        { name: 'cpf', label: 'CPF', type: 'text', value: '555.666.777-88' },
        { name: 'email', label: 'E-mail', type: 'email', value: 'joao@universidade.edu.br' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        full_name: formData.full_name,
        cpf: formData.cpf,
        email: formData.email
      })
    },
    'novo-documento': {
      title: 'Registrar documento',
      endpoint: '/ged/documentos/upload',
      method: 'POST',
      fields: [
        { name: 'title', label: 'Título', type: 'text', value: 'Histórico escolar' },
        { name: 'file_name', label: 'Nome do arquivo', type: 'text', value: 'historico.pdf' },
        { name: 'document_type', label: 'Tipo documental', type: 'text', value: 'Acadêmico' }
      ],
      transform: (formData) => ({
        title: formData.title,
        file_name: formData.file_name,
        document_type: formData.document_type
      })
    },
    'lancar-notas': {
      title: 'Lançar nota',
      endpoint: '/professores/notas',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'Aluno', type: 'text', value: 'ALU-1001' },
        { name: 'disciplina', label: 'Disciplina', type: 'text', value: 'Algoritmos' },
        { name: 'nota', label: 'Nota', type: 'number', value: '9.5', step: '0.1' },
        { name: 'frequencia', label: 'Frequência (%)', type: 'number', value: '96', step: '1' },
        { name: 'bimestre', label: 'Bimestre', type: 'select', options: ['1º Bimestre', '2º Bimestre', '3º Bimestre', '4º Bimestre'], value: '1º Bimestre' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        disciplina: formData.disciplina,
        nota: Number(formData.nota),
        frequencia: Number(formData.frequencia),
        bimestre: formData.bimestre
      })
    },
    'frequencia': {
      title: 'Registrar frequência',
      endpoint: '/professores/notas',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'Aluno', type: 'text', value: 'ALU-1001' },
        { name: 'disciplina', label: 'Disciplina', type: 'text', value: 'Matemática' },
        { name: 'frequencia', label: 'Presença (%)', type: 'number', value: '96', step: '1' },
        { name: 'bimestre', label: 'Bimestre', type: 'select', options: ['1º Bimestre', '2º Bimestre', '3º Bimestre', '4º Bimestre'], value: '1º Bimestre' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        disciplina: formData.disciplina,
        nota: 0,
        frequencia: Number(formData.frequencia),
        bimestre: formData.bimestre
      })
    },
    'nova-turma': {
      title: 'Nova turma',
      endpoint: '/professores/turmas',
      method: 'POST',
      fields: [
        { name: 'class_id', label: 'Código da turma', type: 'text', value: 'TUR-203' },
        { name: 'name', label: 'Nome da turma', type: 'text', value: 'Física Aplicada' },
        { name: 'period', label: 'Período', type: 'text', value: '2026/2' },
        { name: 'professor', label: 'Professor responsável', type: 'text', value: 'Prof. Helena Costa' },
        { name: 'room', label: 'Sala', type: 'text', value: 'LAB-02' },
        { name: 'students_count', label: 'Quantidade de alunos', type: 'number', value: '28', step: '1' },
        { name: 'schedule', label: 'Horário', type: 'text', value: 'Terça e Quinta, 10:00-12:00' }
      ],
      transform: (formData) => ({
        class_id: formData.class_id,
        name: formData.name,
        period: formData.period,
        professor: formData.professor,
        room: formData.room,
        students_count: Number(formData.students_count),
        schedule: formData.schedule
      })
    },
    'upload-doc': {
      title: 'Upload documental',
      endpoint: '/ged/documentos/upload',
      method: 'POST',
      fields: [
        { name: 'title', label: 'Título', type: 'text', value: 'Diploma digital' },
        { name: 'file_name', label: 'Arquivo', type: 'text', value: 'diploma.pdf' },
        { name: 'document_type', label: 'Tipo', type: 'text', value: 'Diploma' },
        { name: 'owner', label: 'Responsável', type: 'text', value: 'Secretaria Acadêmica' },
        { name: 'status', label: 'Status', type: 'select', options: ['recebido', 'em validação', 'validado', 'recusado'], value: 'recebido' },
        { name: 'version', label: 'Versão', type: 'select', options: ['v1', 'v2', 'v3'], value: 'v1' },
        { name: 'category', label: 'Categoria', type: 'text', value: 'Acadêmico' },
        { name: 'retention', label: 'Retenção', type: 'text', value: '5 anos' }
      ],
      transform: (formData) => ({
        title: formData.title,
        file_name: formData.file_name,
        document_type: formData.document_type,
        owner: formData.owner,
        status: formData.status,
        version: formData.version,
        category: formData.category,
        retention: formData.retention
      })
    },
    'validar-doc': {
      title: 'Validar documento',
      endpoint: '/ged/documentos/upload',
      method: 'POST',
      fields: [
        { name: 'title', label: 'Documento', type: 'text', value: 'RG do aluno' },
        { name: 'file_name', label: 'Arquivo', type: 'text', value: 'rg_ana.pdf' },
        { name: 'document_type', label: 'Tipo', type: 'text', value: 'Identidade' },
        { name: 'owner', label: 'Responsável', type: 'text', value: 'Coordenação' },
        { name: 'status', label: 'Status', type: 'select', options: ['recebido', 'em validação', 'validado', 'recusado'], value: 'validado' },
        { name: 'version', label: 'Versão', type: 'select', options: ['v1', 'v2', 'v3'], value: 'v2' }
      ],
      transform: (formData) => ({
        title: formData.title,
        file_name: formData.file_name,
        document_type: formData.document_type,
        owner: formData.owner,
        status: formData.status,
        version: formData.version
      })
    },
    'gerar-boleto': {
      title: 'Gerar boleto',
      endpoint: '/financeiro/boletos',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'Aluno', type: 'text', value: 'ALU-1001' },
        { name: 'responsible_financial_id', label: 'Responsável financeiro cadastrado', type: 'select', options: [{ value: '', label: 'Informe o aluno para carregar responsáveis' }], value: '', loadGuardians: true },
        { name: 'amount', label: 'Valor total', type: 'number', value: '1500', step: '0.01' },
        { name: 'discount', label: 'Desconto', type: 'number', value: '0', min: '0', step: '0.01' },
        { name: 'plan', label: 'Plano', type: 'select', options: ['mensalidade', 'anuidade_semestre', 'taxa_matricula', 'personalizado'], value: 'anuidade_semestre' },
        { name: 'installments_count', label: 'Número de parcelas', type: 'number', value: '1', min: '1', max: '36', step: '1' },
        { name: 'due_date', label: 'Vencimento da primeira parcela', type: 'date', value: '2026-12-10' },
        { name: 'issuer', label: 'Emissor', type: 'text', value: 'Secretaria' },
        { name: 'payment_method', label: 'Forma de pagamento', type: 'select', options: ['boleto', 'pix', 'cartão', 'transferência'], value: 'boleto' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        responsible_financial_id: formData.responsible_financial_id || null,
        amount: Number(formData.amount),
        discount: Number(formData.discount),
        plan: formData.plan,
        installments_count: Number(formData.installments_count),
        due_date: formData.due_date,
        issuer: formData.issuer,
        payment_method: formData.payment_method
      })
    },
    'cobranca': {
      title: 'Registrar cobrança',
      endpoint: '/financeiro/boletos',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'Aluno', type: 'text', value: 'ALU-1002' },
        { name: 'responsible_financial_id', label: 'Responsável financeiro cadastrado', type: 'select', options: [{ value: '', label: 'Informe o aluno para carregar responsáveis' }], value: '', loadGuardians: true },
        { name: 'amount', label: 'Valor total', type: 'number', value: '1320', step: '0.01' },
        { name: 'discount', label: 'Desconto', type: 'number', value: '0', min: '0', step: '0.01' },
        { name: 'plan', label: 'Plano', type: 'select', options: ['mensalidade', 'anuidade_semestre', 'taxa_matricula', 'personalizado'], value: 'anuidade_semestre' },
        { name: 'installments_count', label: 'Número de parcelas', type: 'number', value: '4', min: '1', max: '36', step: '1' },
        { name: 'due_date', label: 'Vencimento da primeira parcela', type: 'date', value: '2026-11-30' },
        { name: 'issuer', label: 'Emissor', type: 'text', value: 'Financeiro' },
        { name: 'payment_method', label: 'Forma de pagamento', type: 'select', options: ['boleto', 'pix', 'cartão', 'transferência'], value: 'pix' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        responsible_financial_id: formData.responsible_financial_id || null,
        amount: Number(formData.amount),
        discount: Number(formData.discount),
        plan: formData.plan,
        installments_count: Number(formData.installments_count),
        due_date: formData.due_date,
        issuer: formData.issuer,
        payment_method: formData.payment_method
      })
    },
    'nova-pendencia': {
      title: 'Nova pendência',
      endpoint: '/coordenacao/pendencias',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'ID do aluno', type: 'text', value: '', placeholder: 'ID exibido na lista acadêmica' },
        { name: 'course_id', label: 'ID do curso (opcional se houver um único curso)', type: 'text', value: '' },
        { name: 'issue', label: 'Pendência', type: 'text', value: 'Documentação complementar' },
        { name: 'priority', label: 'Prioridade', type: 'select', options: ['alta', 'média', 'baixa'], value: 'alta' },
        { name: 'status', label: 'Status', type: 'select', options: ['em andamento', 'aguardando'], value: 'em andamento' },
        { name: 'responsible', label: 'Responsável', type: 'text', value: '' },
        { name: 'deadline', label: 'Prazo', type: 'date', value: '' },
        { name: 'category', label: 'Categoria', type: 'text', value: 'Documentação' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        course_id: formData.course_id || null,
        issue: formData.issue,
        priority: formData.priority,
        status: formData.status,
        responsible: formData.responsible || null,
        deadline: formData.deadline || null,
        category: formData.category
      })
    },
    'acompanhamento': {
      title: 'Acompanhamento',
      endpoint: '/coordenacao/pendencias',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'ID do aluno', type: 'text', value: '', placeholder: 'ID exibido na lista acadêmica' },
        { name: 'course_id', label: 'ID do curso (opcional se houver um único curso)', type: 'text', value: '' },
        { name: 'issue', label: 'Observação', type: 'text', value: 'Plano curricular em revisão' },
        { name: 'priority', label: 'Prioridade', type: 'select', options: ['alta', 'média', 'baixa'], value: 'média' },
        { name: 'status', label: 'Status', type: 'select', options: ['em andamento', 'aguardando'], value: 'aguardando' },
        { name: 'responsible', label: 'Responsável', type: 'text', value: '' },
        { name: 'deadline', label: 'Prazo', type: 'date', value: '' },
        { name: 'category', label: 'Categoria', type: 'text', value: 'Curricular' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        course_id: formData.course_id || null,
        issue: formData.issue,
        priority: formData.priority,
        status: formData.status,
        responsible: formData.responsible || null,
        deadline: formData.deadline || null,
        category: formData.category
      })
    },
    'consultar-boletim': {
      title: 'Consultar boletim',
      endpoint: '/aluno/boletim',
      method: 'GET',
      fields: [
        { name: 'student_id', label: 'Código do aluno', type: 'text', value: 'ALU-1001' }
      ],
      transform: (formData) => ({ student_id: formData.student_id })
    },
    'matricula': {
      title: 'Solicitar matrícula',
      endpoint: '/aluno/matricula',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'Código do aluno', type: 'text', value: 'ALU-1001' },
        { name: 'course', label: 'Curso', type: 'text', value: 'Engenharia de Software' },
        { name: 'semester', label: 'Semestre', type: 'text', value: '2026/2' },
        { name: 'status', label: 'Status', type: 'select', options: ['pendente', 'aprovada', 'em análise'], value: 'pendente' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        course: formData.course,
        semester: formData.semester,
        status: formData.status
      })
    },
    'relatorio': {
      title: 'Atualizar painel',
      endpoint: null,
      method: 'REFRESH',
      fields: []
    },
    'validacao': {
      title: 'Validação',
      endpoint: '/coordenacao/pendencias',
      method: 'POST',
      fields: [
        { name: 'student_id', label: 'ID do aluno', type: 'text', value: '', placeholder: 'ID exibido na lista acadêmica' },
        { name: 'course_id', label: 'ID do curso (opcional se houver um único curso)', type: 'text', value: '' },
        { name: 'issue', label: 'Item validado', type: 'text', value: 'Histórico escolar' },
        { name: 'priority', label: 'Prioridade', type: 'select', options: ['alta', 'média', 'baixa'], value: 'alta' }
      ],
      transform: (formData) => ({
        student_id: formData.student_id,
        course_id: formData.course_id || null,
        issue: formData.issue,
        priority: formData.priority
      })
    },
    'documentos': {
      title: 'Listar documentos',
      endpoint: null,
      method: 'REFRESH',
      fields: []
    },
    'ajuda': {
      title: 'Ajuda',
      endpoint: null,
      method: 'REFRESH',
      fields: []
    },
    'extrato': {
      title: 'Extrato',
      endpoint: null,
      method: 'REFRESH',
      fields: []
    },
    'pagamento': {
      title: 'Pagamento',
      endpointTemplate: '/financeiro/boletos/{invoice_id}/status',
      method: 'PATCH',
      fields: [
        { name: 'invoice_id', label: 'ID da cobrança', type: 'text', value: '' },
        { name: 'status', label: 'Novo status', type: 'select', options: ['quitado', 'cancelado'], value: 'quitado' }
      ],
      transform: (formData) => ({
        status: formData.status
      })
    },
    'resolver-revisao': {
      title: 'Concluir revisão financeira',
      endpointTemplate: '/financeiro/revisoes-academicas/{review_id}/resolver',
      method: 'PATCH',
      fields: [
        { name: 'review_id', label: 'ID da revisão', type: 'text', value: '', readOnly: true },
        { name: 'resolution_note', label: 'Observação da análise', type: 'text', value: '', placeholder: 'Descreva a análise realizada' }
      ],
      transform: (formData) => ({
        resolution_note: formData.resolution_note
      })
    }
  };

  const config = actionMap[actionKey];
  if (!config) return;

  const existingStatus = panel.querySelector('.module-form-status');
  if (existingStatus) existingStatus.remove();

  panel.style.display = 'block';
  panel.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom: 16px;">
      <div>
        <div class="text-muted" style="font-size:12px; text-transform:uppercase; letter-spacing:.08em;">Ação do módulo</div>
        <h3 style="margin:8px 0 0;">${config.title}</h3>
      </div>
      <button type="button" class="btn-secondary btn-small" data-close-form="true">Fechar</button>
    </div>
  `;

  if (!config.fields.length) {
    panel.innerHTML += `<div class="text-muted">Painel atualizado com sucesso.</div>`;
    panel.querySelector('[data-close-form]').addEventListener('click', () => { panel.style.display = 'none'; panel.innerHTML = ''; });
    return;
  }

  const form = document.createElement('form');
  form.innerHTML = config.fields.map((field) => {
    const value = initialValues[field.name] ?? field.value ?? '';
    const readOnly = field.readOnly ? 'readonly' : '';
    const inputMarkup = field.type === 'select'
      ? `<select name="${field.name}" ${field.loadGuardians ? 'data-financial-guardian="true" disabled' : ''} style="width:100%; padding:10px; border-radius:8px;">${field.options.map((option) => {
        const optionValue = typeof option === 'object' ? option.value : option;
        const optionLabel = typeof option === 'object' ? option.label : option;
        return `<option value="${optionValue}" ${String(optionValue) === String(field.value) ? 'selected' : ''}>${optionLabel}</option>`;
      }).join('')}</select>`
      : `<input type="${field.type}" name="${field.name}" value="${value}" placeholder="${field.placeholder || ''}" min="${field.min || ''}" max="${field.max || ''}" step="${field.step || 'any'}" ${readOnly} style="width:100%; padding:10px; border-radius:8px;">`;
    return `
      <div style="margin-bottom: 12px;">
        <label style="display:block; margin-bottom:6px; font-weight:600;">${field.label}</label>
        ${inputMarkup}
      </div>
    `;
  }).join('');

  const submitButton = document.createElement('button');
  submitButton.type = 'submit';
  submitButton.className = 'btn-primary';
  submitButton.textContent = 'Salvar';
  form.appendChild(submitButton);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const formData = Object.fromEntries(new FormData(form).entries());
    const payload = config.transform(formData);
    const endpoint = config.endpointTemplate
      ? config.endpointTemplate.replace(/\{([^}]+)\}/g, (_match, fieldName) => encodeURIComponent(formData[fieldName] || ''))
      : config.endpoint;

    if (config.method === 'GET') {
      const query = new URLSearchParams(payload).toString();
      try {
        const url = buildApiUrl(`${config.endpoint}?${query}`);
        const response = await fetch(url, { headers: getAuthHeaders() });
        const json = response.ok ? await response.json() : null;
        showStatusMessage(response.ok ? `Consulta realizada com sucesso para ${payload.student_id}.` : 'Falha ao consultar o módulo.', response.ok ? 'info' : 'error');
        if (json) { showStatusMessage(JSON.stringify(json).slice(0, 140), 'info'); }
      } catch (error) {
        showStatusMessage('Falha ao consultar o módulo.', 'error');
      }
      return;
    }

    try {
      const response = await fetch(buildApiUrl(endpoint), {
        method: config.method,
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify(payload)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        showStatusMessage(result.detail || 'Não foi possível salvar o registro.', 'error');
        return;
      }
      showStatusMessage(`${config.title} registrado com sucesso.`, 'info');
      if (actionKey === 'resolver-revisao') {
        await loadFinancialReviews();
      } else {
        await loadModulePageData();
      }
      window.dispatchEvent(new CustomEvent('module-action-saved', {
        detail: { module: currentModule }
      }));
    } catch (error) {
      showStatusMessage('Falha ao enviar a ação do módulo.', 'error');
    }
  });

  panel.appendChild(form);
  const guardianSelect = form.querySelector('[data-financial-guardian]');
  const studentInput = form.querySelector('[name="student_id"]');
  if (guardianSelect && studentInput) {
    studentInput.addEventListener('change', async () => {
      const studentId = studentInput.value.trim();
      guardianSelect.replaceChildren();
      guardianSelect.disabled = true;
      if (!studentId) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Informe o aluno para carregar responsáveis';
        guardianSelect.appendChild(option);
        return;
      }
      try {
        const response = await fetch(
          buildApiUrl(`/financeiro/alunos/${encodeURIComponent(studentId)}/responsaveis-financeiros`),
          { headers: getAuthHeaders() }
        );
        const data = await response.json();
        if (!response.ok) {
          showStatusMessage(data.detail || 'Não foi possível carregar os responsáveis do aluno.', 'error');
          return;
        }
        const noResponsibleOption = document.createElement('option');
        noResponsibleOption.value = '';
        noResponsibleOption.textContent = 'Sem responsável financeiro vinculado';
        guardianSelect.appendChild(noResponsibleOption);
        data.items.forEach((guardian) => {
          const option = document.createElement('option');
          option.value = guardian.id;
          option.textContent = `${guardian.full_name} (${guardian.relationship_type})`;
          guardianSelect.appendChild(option);
        });
        guardianSelect.disabled = false;
      } catch (error) {
        showStatusMessage('Falha ao carregar os responsáveis do aluno.', 'error');
      }
    });
  }
  panel.querySelector('[data-close-form]').addEventListener('click', () => { panel.style.display = 'none'; panel.innerHTML = ''; });
}

function renderQuickActions() {
  ensureFormPanel();
  const container = document.getElementById('quick-actions');
  if (!container) return;

  const actions = moduleActions[currentModule] || [];
  container.innerHTML = actions.map((action) => `
    <button type="button" class="btn-secondary" data-module-action="${action.key}" style="width:100%; justify-content: center;">${action.label}</button>
  `).join('');

  container.querySelectorAll('[data-module-action]').forEach((button) => {
    button.addEventListener('click', () => {
      const actionKey = button.getAttribute('data-module-action');
      if (actionKey === 'revisoes') {
        loadFinancialReviews();
        return;
      }
      if (actionKey === 'relatorio' || actionKey === 'documentos' || actionKey === 'extrato' || actionKey === 'ajuda' || actionKey === 'buscar-doc') {
        showStatusMessage('Painel atualizado com sucesso.', 'info');
        loadModulePageData();
        return;
      }
      openActionForm(actionKey);
    });
  });
}

async function loadFinancialReviews() {
  try {
    const response = await fetch(
      buildApiUrl('/financeiro/revisoes-academicas?status_filter=pendente'),
      { headers: getAuthHeaders() }
    );
    const data = await response.json();
    if (!response.ok) {
      showStatusMessage(data.detail || 'Não foi possível carregar as revisões financeiras.', 'error');
      return;
    }
    renderFinancialReviews(resolveListItems(data));
    showStatusMessage('Revisões financeiras pendentes carregadas.', 'info');
  } catch (error) {
    showStatusMessage('Falha ao carregar as revisões financeiras.', 'error');
  }
}

function renderFinancialReviews(items) {
  const listEl = document.getElementById('primary-list');
  if (!listEl) return;
  listEl.replaceChildren();

  if (!items.length) {
    const emptyMessage = document.createElement('p');
    emptyMessage.className = 'text-muted';
    emptyMessage.textContent = 'Nenhuma revisão financeira pendente.';
    listEl.appendChild(emptyMessage);
    return;
  }

  const table = document.createElement('table');
  table.className = 'data-table';
  table.style.width = '100%';
  table.style.minWidth = '640px';
  const headers = ['Aluno', 'Tipo', 'Detalhes', 'Criada em', 'Ação'];
  const headerRow = document.createElement('tr');
  headers.forEach((label) => {
    const header = document.createElement('th');
    header.textContent = label;
    headerRow.appendChild(header);
  });
  const thead = document.createElement('thead');
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  items.forEach((item) => {
    const row = document.createElement('tr');
    [
      item.student_name,
      item.review_type,
      item.details,
      item.created_at ? new Date(item.created_at).toLocaleString('pt-BR') : '-'
    ].forEach((value) => {
      const cell = document.createElement('td');
      cell.textContent = value || '-';
      row.appendChild(cell);
    });

    const actionCell = document.createElement('td');
    const resolveButton = document.createElement('button');
    resolveButton.type = 'button';
    resolveButton.className = 'btn-secondary btn-small';
    resolveButton.textContent = 'Analisar e concluir';
    resolveButton.addEventListener('click', () => {
      openActionForm('resolver-revisao', { review_id: item.id });
    });
    actionCell.appendChild(resolveButton);
    row.appendChild(actionCell);
    tbody.appendChild(row);
  });
  table.appendChild(tbody);

  const wrapper = document.createElement('div');
  wrapper.style.overflow = 'auto';
  wrapper.appendChild(table);
  listEl.appendChild(wrapper);
}

async function loadModulePageData() {
  const config = moduleMeta[currentModule];
  if (!config) return;

  const title = document.getElementById('page-title');
  const subtitle = document.getElementById('page-subtitle');
  const bannerTitle = document.getElementById('module-banner-title');
  const bannerText = document.getElementById('module-banner-text');

  if (title) title.textContent = config.title;
  if (subtitle) subtitle.textContent = config.description;
  if (bannerTitle) bannerTitle.textContent = config.title;
  if (bannerText) bannerText.textContent = config.description;

  const endpointDashboard = buildApiUrl(config.endpoints.dashboard);
  const endpointList = buildApiUrl(config.endpoints.list);

  try {
    const dashboardResponse = await fetch(endpointDashboard, { headers: getAuthHeaders() });
    const dashboardData = dashboardResponse.ok ? await dashboardResponse.json() : null;
    if (dashboardData && dashboardData.stats) {
      renderStats(dashboardData.stats);
    } else {
      renderStats({ status: 'Ativo', resumo: 'Operando', acesso: 'Liberado' });
    }

    const listResponse = await fetch(endpointList, { headers: getAuthHeaders() });
    const listData = listResponse.ok ? await listResponse.json() : null;
    const listItems = resolveListItems(listData);
    renderPrimaryList(listItems);
  } catch (error) {
    renderStats({ status: 'Ativo', resumo: 'Modo local', acesso: 'Visualização' });
    renderPrimaryList([
      { nome: 'Dados locais', status: 'Ativo', detalhe: 'Os dados do módulo devem ser sincronizados pelo backend.' }
    ]);
  }

  renderQuickActions();
}

function initModulePage(moduleKey) {
  currentModule = moduleKey;
  const token = localStorage.getItem('ged_token');
  if (!token) {
    window.location.href = '../login.html';
    return;
  }

  const payload = parseJwt(token);
  if (!payload || payload.exp < Math.floor(Date.now() / 1000)) {
    localStorage.removeItem('ged_token');
    window.location.href = '../login.html';
    return;
  }

  loadModulePageData();
}

let currentModule = 'secretaria';

const moduleBadgeStyles = `
  .status-badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .04em;
    text-transform: uppercase;
  }
  .status-badge.success {
    background: rgba(16, 185, 129, 0.15);
    color: #4ade80;
  }
  .status-badge.warning {
    background: rgba(245, 158, 11, 0.12);
    color: #fbbf24;
  }
  .status-badge.danger {
    background: rgba(239, 68, 68, 0.12);
    color: #f87171;
  }
  .status-badge.neutral {
    background: rgba(148, 163, 184, 0.15);
    color: #cbd5e1;
  }
`;

if (!document.getElementById('module-badge-styles')) {
  const styleTag = document.createElement('style');
  styleTag.id = 'module-badge-styles';
  styleTag.textContent = moduleBadgeStyles;
  document.head.appendChild(styleTag);
}
