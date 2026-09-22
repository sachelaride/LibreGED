// app_operations.js - Lida com a busca e upload do app.html

let searchDocumentTypes = [];

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    }[character]));
}

async function loadSearchDocumentTypes() {
    const selector = document.getElementById('search-document-type');
    if (!selector) return;
    try {
        const response = await fetch(`${API_URL}/documents/search/types`, { headers: getAuthHeaders() });
        if (!response.ok) return;
        const items = await response.json();
        searchDocumentTypes = Array.isArray(items) ? items : [];
        loadSearchGroups();
        loadSearchTypeOptions();
    } catch (e) {
        console.warn('Não foi possível carregar tipos para a busca', e);
    }
}

function loadSearchTypeOptions() {
    const selector = document.getElementById('search-document-type');
    if (!selector) return;
    const groupId = document.getElementById('search-group')?.value || '';
    const current = selector.value;
    const types = searchDocumentTypes.filter(item => !groupId || item.group_id === groupId);
    selector.innerHTML = '<option value="">Tipo documental</option>';
    types.forEach(item => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = item.name;
        selector.appendChild(option);
    });
    if (types.some(item => item.id === current)) selector.value = current;
    updateSearchIndexHelp();
}

function groupLabel(groupId) {
    const labels = {
        pessoal: 'Documentos Pessoais',
        documentos_pessoais: 'Documentos Pessoais',
        acad_dossier: 'Documentos Acadêmicos',
        academico: 'Documentos Acadêmicos',
        documentos_academicos: 'Documentos Acadêmicos'
    };
    return labels[(groupId || '').toLowerCase()] || groupId || 'Sem grupo';
}

function loadSearchGroups() {
    const selector = document.getElementById('search-group');
    if (!selector) return;
    const groups = [...new Map(
        searchDocumentTypes
            .filter(item => item.group_id)
            .map(item => [item.group_id, groupLabel(item.group_id)])
    )].sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'));
    const current = selector.value;
    selector.innerHTML = '<option value="">Grupo documental</option>';
    groups.forEach(([id, label]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = label;
        selector.appendChild(option);
    });
    if (current && groups.some(([id]) => id === current)) selector.value = current;
    updateSearchIndexHelp();
}

function updateSearchIndexHelp() {
    const typeId = document.getElementById('search-document-type')?.value;
    const groupId = document.getElementById('search-group')?.value;
    const help = document.getElementById('search-indexes-help');
    const indexSelector = document.getElementById('search-index');
    if (!help) return;
    const types = searchDocumentTypes.filter(item =>
        (!typeId || item.id === typeId) && (!groupId || item.group_id === groupId)
    );
    const indices = [...new Map(
        types.flatMap(item => (item.indices || []).map(link => {
            const index = link.index || link;
            return [index.id, index];
        }))
    ).values()];
    const currentIndex = indexSelector?.value;
    if (indexSelector) {
        indexSelector.innerHTML = '<option value="">Índice cadastrado</option>';
        indices.forEach(index => {
            const option = document.createElement('option');
            option.value = index.id;
            option.textContent = index.name;
            indexSelector.appendChild(option);
        });
        if (indices.some(index => index.id === currentIndex)) indexSelector.value = currentIndex;
    }
    help.textContent = indices.length
        ? `Índices disponíveis: ${indices.map(index => index.name).join(', ')}.`
        : 'Selecione um grupo ou tipo para ver os índices disponíveis.';
}

function updateOcrHelp() {
    const help = document.getElementById('upload-ocr-help');
    const engine = document.getElementById('upload-ocr-engine')?.value || 'auto';
    if (!help) return;
    const descriptions = {
        auto: 'Auto seleciona o melhor motor disponível no ambiente.',
        none: 'O arquivo será armazenado sem extração de texto OCR.',
        tesseract: 'Boa opção para documentos impressos e idiomas configurados.',
        paddleocr: 'Recomendado para imagens com diferentes layouts e qualidade variável.',
        rapidocr: 'Alternativa leve para processamento rápido de imagens.'
    };
    help.textContent = descriptions[engine] || descriptions.auto;
}

function clearSearchFilters() {
    ['search-query', 'search-student', 'search-group', 'search-index', 'search-index-value'].forEach(id => {
        const field = document.getElementById(id);
        if (field) field.value = '';
    });
    const typeField = document.getElementById('search-document-type');
    if (typeField) typeField.value = '';
    loadSearchTypeOptions();
    updateSearchIndexHelp();
    document.getElementById('search-summary').textContent = '';
    document.getElementById('search-results').innerHTML =
        '<p class="text-muted" style="text-align:center;">Digite um termo ou use filtros para começar a busca.</p>';
}

async function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    const studentId = document.getElementById('search-student')?.value || '';
    const groupId = document.getElementById('search-group')?.value || '';
    const docTypeId = document.getElementById('search-document-type')?.value || '';
    const indexValue = document.getElementById('search-index-value')?.value.trim() || '';
    const indexId = document.getElementById('search-index')?.value || '';
    const resultsContainer = document.getElementById('search-results');
    const summary = document.getElementById('search-summary');

    if (!query && !studentId && !groupId && !docTypeId && !indexId && !indexValue) {
        summary.textContent = '';
        resultsContainer.innerHTML = '<p class="text-muted" style="text-align:center;">Digite um termo ou use filtros para começar a busca.</p>';
        return;
    }

    summary.textContent = 'Consultando documentos autorizados...';
    resultsContainer.innerHTML = '<p style="text-align:center;">Buscando...</p>';

    try {
        const params = new URLSearchParams();
        if (query) params.set('q', query);
        if (studentId) params.set('student_id', studentId);
        if (groupId) params.set('group_id', groupId);
        if (docTypeId) params.set('document_type_id', docTypeId);
        if (indexId) params.set('index_id', indexId);
        if (indexValue) params.set('index_value', indexValue);

        const response = await fetch(`${API_URL}/documents/search?${params.toString()}`, {
            headers: getAuthHeaders()
        });

        if (!response.ok) {
            summary.textContent = '';
            resultsContainer.innerHTML = '<p style="color:red; text-align:center;">Erro ao realizar a busca.</p>';
            return;
        }

        const results = await response.json();
        const documentos = results.items || [];
        summary.textContent = `${results.total || 0} documento(s) encontrado(s)`;
        if (documentos.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted" style="text-align:center;">Nenhum documento encontrado.</p>';
            return;
        }

        let html = '<div style="display:grid; gap:15px;">';
        documentos.forEach(doc => {
            const oficial = doc.is_official !== false && doc.document_purpose !== 'conference';
            const selo = oficial
                ? '<span class="document-purpose-badge document-purpose-official">OFICIAL</span>'
                : '<span class="document-purpose-badge document-purpose-conference">CONFERÊNCIA · NÃO OFICIAL</span>';
            const snippet = escapeHtml((doc.snippet || '').replace(/\s+/g, ' ').trim());
            const studentText = doc.student_id
                ? `<div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">Aluno: ${escapeHtml(doc.student_id)}</div>`
                : '';
            const groupText = doc.group_id
                ? `<div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Grupo: ${escapeHtml(groupLabel(doc.group_id))}</div>`
                : '';
            const typeText = doc.document_type?.name
                ? `<div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Tipo: ${escapeHtml(doc.document_type.name)}</div>`
                : '';
            const indicesText = (doc.indices || []).length
                ? `<div class="search-result-indices">${doc.indices.map(index =>
                    `<span><strong>${escapeHtml(index.name)}:</strong> ${escapeHtml(index.value)}</span>`
                ).join('')}</div>`
                : '';
            const ocrIndexed = doc.ocr_status === 'success' || doc.ocr_status === 'indexed';
            const ocrLabel = ocrIndexed
                ? `OCR indexado · ${escapeHtml(doc.ocr_engine || 'auto')}`
                : 'OCR não executado';
            const ocrClass = ocrIndexed ? 'ocr-status-indexed' : 'ocr-status-skipped';
            const documentId = encodeURIComponent(doc.document_id || doc.id || '');
            html += `
                <div class="glass-panel" style="padding: 20px; display:flex; justify-content:space-between; align-items:flex-start; gap:12px;">
                    <div style="flex:1;">
                        <h4 style="margin-bottom:5px; color:var(--primary);">${escapeHtml(doc.title || 'Documento sem nome')}</h4>
                        <p style="font-size:13px; color:var(--text-muted); margin: 4px 0;">
                            ${selo}
                            <strong>Status:</strong> ${escapeHtml(doc.status || 'N/A')}
                            <span class="ocr-status-badge ${ocrClass}" title="Estado da extração de texto">${ocrLabel}</span>
                        </p>
                        ${studentText}
                        ${groupText}
                        ${typeText}
                        ${indicesText}
                        <div class="search-result-snippet">${snippet || 'Sem prévia extraída por OCR.'}</div>
                    </div>
                    <div>
                        <button class="btn-secondary btn-small" onclick="viewDocument(decodeURIComponent('${documentId}'))">Visualizar</button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        resultsContainer.innerHTML = html;

    } catch(e) {
        summary.textContent = '';
        resultsContainer.innerHTML = `<p style="color:red; text-align:center;">Falha de comunicação: ${e.message}</p>`;
    }

}

function viewDocument(docId) {
    const summary = document.getElementById('search-summary');
    if (summary) summary.textContent = `Documento selecionado: ${docId}. A visualização do arquivo será aberta pelo módulo documental.`;
}

let tiposDocumentaisUpload = [];

async function carregarTiposUpload() {
    const resposta = await fetch(`${API_URL}/document-types?page=1&size=100`, {headers: getAuthHeaders()});
    if (!resposta.ok) throw new Error('Não foi possível carregar os tipos documentais.');
    const dados = await resposta.json();
    tiposDocumentaisUpload = dados.items || [];
    const seletor = document.getElementById('upload-document-type');
    seletor.innerHTML = '<option value="">Selecione o tipo documental</option>';
    tiposDocumentaisUpload.filter(tipo => tipo.is_active).forEach(tipo => {
        const opcao = document.createElement('option');
        opcao.value = tipo.id;
        opcao.textContent = tipo.name;
        seletor.append(opcao);
    });
}

function carregarIndicesUpload() {
    const tipo = tiposDocumentaisUpload.find(item => item.id === document.getElementById('upload-document-type').value);
    const painel = document.getElementById('upload-indices');
    painel.replaceChildren();
    if (!tipo) return;
    (tipo.indices || []).forEach(vinculo => {
        const indice = vinculo.index;
        const grupo = document.createElement('div');
        grupo.className = 'form-group';
        const rotulo = document.createElement('label');
        rotulo.textContent = `${indice.name}${vinculo.is_required ? ' *' : ''}`;
        let campo;
        if (indice.auto_increment) {
            campo = document.createElement('input');
            campo.disabled = true;
            campo.placeholder = 'Gerado automaticamente';
        } else if (indice.type.toLocaleLowerCase() === 'lista') {
            campo = document.createElement('select');
            campo.append(new Option('Selecione', ''));
            (indice.options || []).forEach(valor => campo.append(new Option(valor, valor)));
        } else if (indice.type.toLocaleLowerCase() === 'booleano') {
            campo = document.createElement('select');
            campo.append(new Option('Selecione', ''), new Option('Sim', 'true'), new Option('Não', 'false'));
        } else {
            campo = document.createElement('input');
            campo.type = indice.type.toLocaleLowerCase() === 'data' ? 'date' :
                ['número', 'numero'].includes(indice.type.toLocaleLowerCase()) ? 'number' : 'text';
            if (indice.mask) campo.pattern = indice.mask;
        }
        campo.dataset.indexId = indice.id;
        campo.dataset.autoIncrement = indice.auto_increment ? 'true' : 'false';
        campo.required = vinculo.is_required && !indice.auto_increment;
        grupo.append(rotulo, campo);
        painel.append(grupo);
    });
}

function openNewDocumentForIndex() {
    window.location.hash = 'academic';
    const nameField = document.getElementById('student-name');
    if (nameField) nameField.focus();
}

function renderOperationError(container, message) {
    container.innerHTML = `<p style="color:var(--accent);">${escapeHtml(message)}</p>`;
}

async function loadTaskMonitor() {
    const list = document.getElementById('task-monitor-list');
    const summary = document.getElementById('task-monitor-summary');
    if (!list || !summary) return;
    list.innerHTML = '<p class="text-muted">Carregando tarefas...</p>';
    summary.textContent = '';
    try {
        const response = await fetch(`${API_URL}/workflows/tasks/my-tasks`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            renderOperationError(list, `Não foi possível carregar tarefas (HTTP ${response.status}).`);
            return;
        }
        const tasks = await response.json();
        summary.textContent = `${tasks.length} tarefa(s) pendente(s)`;
        if (!tasks.length) {
            list.innerHTML = '<p class="text-muted">Nenhuma tarefa pendente.</p>';
            return;
        }
        list.innerHTML = tasks.map(task => `
            <div class="operation-list-item">
                <div>
                    <strong>${escapeHtml(task.name)}</strong>
                    <div class="text-muted">${escapeHtml(task.description || 'Sem descrição')}</div>
                    <small class="text-muted">Criada em ${escapeHtml(task.created_at || 'data não informada')}</small>
                </div>
                <button class="btn-primary btn-small" type="button" onclick="completeTask('${encodeURIComponent(task.id)}')">
                    Concluir
                </button>
            </div>
        `).join('');
    } catch (error) {
        renderOperationError(list, `Falha de comunicação: ${error.message}`);
    }
}

async function loadFlowMonitor() {
    const list = document.getElementById('flow-monitor-list');
    if (!list) return;
    list.innerHTML = '<p class="text-muted">Carregando fluxos...</p>';
    try {
        const response = await fetch(`${API_URL}/workflows?page=1&size=100`, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            renderOperationError(list, `Monitor de fluxo indisponível para este perfil (HTTP ${response.status}).`);
            document.getElementById('insight-flow-count')?.replaceChildren(document.createTextNode('-'));
            return;
        }
        const payload = await response.json();
        const flows = payload.items || [];
        if (!flows.length) {
            list.innerHTML = '<p class="text-muted">Nenhum fluxo disponível.</p>';
            return;
        }
        list.innerHTML = flows.map(flow => `
            <div class="operation-list-item">
                <div>
                    <strong>${escapeHtml(flow.name)}</strong>
                    <div class="text-muted">${escapeHtml(flow.internal_name)}</div>
                </div>
                <span class="ocr-status-badge ${flow.is_active ? 'ocr-status-indexed' : 'ocr-status-skipped'}">
                    ${flow.is_active ? 'Ativo' : 'Inativo'}
                </span>
            </div>
        `).join('');
        const flowCount = document.getElementById('insight-flow-count');
        if (flowCount) flowCount.textContent = String(flows.length);
    } catch (error) {
        renderOperationError(list, `Falha de comunicação: ${error.message}`);
    }
}

async function startFlowFromForm() {
    const feedback = document.getElementById('new-flow-feedback');
    const payload = {
        document_id: document.getElementById('new-flow-document-id').value.trim(),
        workflow_id: document.getElementById('new-flow-workflow-id').value.trim(),
        current_state_id: document.getElementById('new-flow-state-id').value.trim()
    };
    feedback.textContent = 'Iniciando fluxo...';
    try {
        const response = await fetch(`${API_URL}/workflows/instances`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            feedback.textContent = data.detail || `Não foi possível iniciar o fluxo (HTTP ${response.status}).`;
            return;
        }
        feedback.textContent = `Fluxo iniciado com sucesso: ${data.id || 'instância criada'}.`;
        document.getElementById('new-flow-form').reset();
        window.location.hash = 'tasks';
    } catch (error) {
        feedback.textContent = `Falha de comunicação: ${error.message}`;
    }
}

async function loadInsights() {
    const taskCount = document.getElementById('insight-task-count');
    const flowCount = document.getElementById('insight-flow-count');
    const uploadCount = document.getElementById('insight-upload-count');
    if (uploadCount) uploadCount.textContent = String(uploadQueueState.length);
    try {
        const response = await fetch(`${API_URL}/workflows/tasks/my-tasks`, {
            headers: getAuthHeaders()
        });
        if (response.ok && taskCount) {
            const tasks = await response.json();
            taskCount.textContent = String(tasks.length);
        }
    } catch {
        if (taskCount) taskCount.textContent = '-';
    }
    loadFlowMonitor();
}

let currentStudentId = null;
let currentInstitutionId = null;
let uploadQueueState = [];

function renderUploadStatus(message = '') {
    const container = document.getElementById('upload-status');
    if (!container) return;
    const completed = uploadQueueState.filter(item => item.status === 'success').length;
    const failed = uploadQueueState.filter(item => item.status === 'error').length;
    const pending = uploadQueueState.length - completed - failed;
    const summary = message || `${completed} concluído(s) · ${pending} pendente(s)${failed ? ` · ${failed} com erro` : ''}`;
    container.innerHTML = `
        <div class="upload-status-header">
            <span>${escapeHtml(summary)}</span>
            <span>${uploadQueueState.length} arquivo(s)</span>
        </div>
        ${uploadQueueState.map(item => `
            <div class="upload-file-row">
                <span class="upload-file-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
                <span class="upload-file-status upload-status-${item.status}">${escapeHtml(item.detail)}</span>
            </div>
        `).join('')}
    `;
}

async function createDossier() {
    const name = document.getElementById('student-name').value;
    const cpf = document.getElementById('student-cpf').value;
    
    if(!name || !cpf) {
        alert("Nome e CPF são obrigatórios para iniciar o Dossiê.");
        return;
    }

    try {
        // Obter instituição (pega a primeira disponível para simplificar o MVP)
        const instResp = await fetch(`${API_URL}/institutions`, { headers: getAuthHeaders() });
        const insts = await instResp.json();
        if(insts.length === 0) {
            alert("Nenhuma instituição encontrada no sistema.");
            return;
        }
        currentInstitutionId = insts[0].id;

        // Criar Aluno (Mockando email e data de nascimento se não existirem na UI)
        const studentResp = await fetch(`${API_URL}/students`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                institution_id: currentInstitutionId,
                full_name: name,
                cpf: cpf,
                birth_date: "2000-01-01", // MOCK
                email: `${cpf}@aluno.com` // MOCK
            })
        });
        
        if(!studentResp.ok) {
            const data = await studentResp.json();
            // Se já existe, tenta buscar a lista e achar ele
            if(studentResp.status === 409) {
                const listResp = await fetch(`${API_URL}/students?institution_id=${currentInstitutionId}`, { headers: getAuthHeaders() });
                const students = await listResp.json();
                const existing = students.find(s => s.cpf === cpf);
                if(existing) {
                    currentStudentId = existing.id;
                    alert("Aluno já existia. Dossiê aberto para o aluno existente.");
                }
            } else {
                alert("Erro ao criar aluno: " + (data.detail || ''));
                return;
            }
        } else {
            const newStudent = await studentResp.json();
            currentStudentId = newStudent.id;
            alert("Aluno cadastrado! Você já pode arrastar os documentos do aluno.");
        }

    } catch(e) {
        alert('Erro de rede: ' + e);
        return;
    }

    // Libera a zona de upload
    const uploadZone = document.getElementById('upload-zone');
    const uploadDropzone = document.getElementById('upload-dropzone');
    uploadZone.style.opacity = '1';
    uploadZone.style.pointerEvents = 'auto';
    try {
        await carregarTiposUpload();
    } catch (erro) {
        alert(erro.message);
        return;
    }
    
    // Adiciona listener pro clique na zona
    uploadDropzone.onclick = () => document.getElementById('file-input').click();

    // Configura os eventos de Drag & Drop
    uploadDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadDropzone.style.borderColor = 'var(--primary)';
        uploadDropzone.style.background = 'rgba(0, 210, 255, 0.1)';
    });

    uploadDropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadDropzone.style.borderColor = 'rgba(255,255,255,0.2)';
        uploadDropzone.style.background = 'transparent';
    });

    uploadDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadDropzone.style.borderColor = 'rgba(255,255,255,0.2)';
        uploadDropzone.style.background = 'transparent';
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    // Quando clica no botão "Arraste documentos aqui" ele aciona o input escondido
    document.getElementById('file-input').addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    alert("Dossiê iniciado! Você já pode arrastar ou selecionar os documentos do aluno no painel ao lado.");
}

async function handleFiles(files) {
    if (!files || files.length === 0) return;
    
    if(!currentStudentId) {
        alert("Nenhum aluno ativo no dossiê.");
        return;
    }

    const docTypeId = document.getElementById('upload-document-type').value;
    if (!docTypeId) {
        alert('Selecione o tipo documental antes de enviar.');
        return;
    }

    const formularioValido = [...document.querySelectorAll('#upload-indices [data-index-id]')]
        .every(campo => campo.disabled || campo.reportValidity());
    if (!formularioValido) return;
    const indices = [...document.querySelectorAll('#upload-indices [data-index-id]')]
        .filter(campo => campo.dataset.autoIncrement !== 'true' && campo.value !== '')
        .map(campo => ({index_id: campo.dataset.indexId, value: campo.value}));

    const ocrEngine = document.getElementById('upload-ocr-engine')?.value || 'auto';
    const ocrEnabled = ocrEngine !== 'none';
    const groupId = document.getElementById('upload-group-id')?.value.trim() || '';
    uploadQueueState = Array.from(files).map(file => ({
        name: file.name,
        status: 'pending',
        detail: 'Aguardando'
    }));
    renderUploadStatus(`Preparando ${files.length} arquivo(s)...`);

    for(let i=0; i<files.length; i++) {
        uploadQueueState[i].detail = 'Enviando';
        renderUploadStatus();
        const formData = new FormData();
        formData.append("title", files[i].name);
        formData.append("document_type_id", docTypeId);
        formData.append("document_purpose", document.getElementById('upload-document-purpose').value);
        formData.append("student_id", currentStudentId || '');
        formData.append("group_id", groupId);
        formData.append("ocr_engine", ocrEngine);
        formData.append("ocr_enabled", ocrEnabled ? 'true' : 'false');
        formData.append("indices_json", JSON.stringify(indices));
        formData.append("file", files[i]);
        
        try {
            const response = await fetch(`${API_URL}/documents/upload`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData
            });
            
            if(!response.ok) {
                const erro = await response.json().catch(() => ({}));
                uploadQueueState[i] = {
                    name: files[i].name,
                    status: 'error',
                    detail: erro.detail || 'Upload recusado'
                };
                renderUploadStatus();
                continue;
            }
            uploadQueueState[i].status = 'success';
            uploadQueueState[i].detail = ocrEnabled ? 'Concluído · OCR solicitado' : 'Concluído · sem OCR';
            renderUploadStatus();
        } catch(e) {
            console.error("Erro de rede no upload " + files[i].name, e);
            uploadQueueState[i] = {
                name: files[i].name,
                status: 'error',
                detail: 'Falha de comunicação'
            };
            renderUploadStatus();
        }
    }

    const failed = uploadQueueState.filter(item => item.status === 'error').length;
    renderUploadStatus(failed
        ? `Processamento concluído com ${failed} erro(s). Os demais arquivos foram enviados.`
        : 'Todos os arquivos foram enviados com sucesso.');
    document.getElementById('file-input').value = '';
}

// --- Dashboard & Sites (ECM) ---
async function loadDashboard() {
    // 1. Carregar layout do Dashboard
    // 2. Carregar My Tasks para o dashlet
    
    try {
        const response = await fetch(`${API_URL}/workflows/tasks/my-tasks`, {
            headers: getAuthHeaders()
        });
        const dashlet = document.getElementById('dashlet-tasks');
        if(!response.ok) {
            dashlet.innerHTML = '<p style="color:red; text-align:center;">Erro ao carregar tarefas.</p>';
            return;
        }
        const tasks = await response.json();
        
        if(tasks.length === 0) {
            dashlet.innerHTML = '<p class="text-muted" style="text-align:center; padding-top:20px;">Você não tem tarefas pendentes. 🎉</p>';
            return;
        }
        
        let html = '';
        tasks.forEach(t => {
            html += `
                <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid var(--primary);">
                    <div style="font-weight: 600; font-size:14px; margin-bottom:4px;">${t.name}</div>
                    <div style="font-size: 12px; color: var(--text-muted);">${t.description || ''}</div>
                    <div style="margin-top: 8px; text-align:right;">
                        <button class="btn-primary" style="padding: 4px 10px; font-size:12px;" onclick="completeTask('${t.id}')">Concluir</button>
                    </div>
                </div>
            `;
        });
        dashlet.innerHTML = html;
        
    } catch (e) {
        console.error(e);
    }
}

async function completeTask(taskId) {
    if(!confirm("Deseja realmente marcar esta tarefa como concluída?")) return;
    
    try {
        const response = await fetch(`${API_URL}/workflows/tasks/${taskId}/complete`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: 'COMPLETE' })
        });
        
        if(response.ok) {
            alert('Tarefa concluída!');
            loadDashboard();
        } else {
            alert('Erro ao concluir tarefa');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

async function loadSites() {
    const grid = document.getElementById('sites-grid');
    grid.innerHTML = '<p class="text-muted">Carregando espaços...</p>';
    
    try {
        const response = await fetch(`${API_URL}/ecm/sites`, {
            headers: getAuthHeaders()
        });
        
        if(!response.ok) {
            grid.innerHTML = '<p style="color:red;">Erro ao buscar espaços colaborativos.</p>';
            return;
        }
        
        const sites = await response.json();
        if(sites.length === 0) {
            grid.innerHTML = '<p class="text-muted" style="grid-column: 1 / -1; text-align:center;">Nenhum Espaço Colaborativo encontrado.</p>';
            return;
        }
        
        let html = '';
        sites.forEach(site => {
            html += `
                <div class="glass-panel" style="padding: 20px; transition: transform 0.2s;">
                    <div style="font-size: 24px; color:var(--primary); margin-bottom:10px;"><i class="fa-solid fa-users-rectangle"></i></div>
                    <h3 style="margin-bottom: 5px;">${site.title}</h3>
                    <p style="font-size: 12px; color:var(--text-muted); margin-bottom:15px;">${site.name} • ${site.visibility}</p>
                    <p style="font-size: 14px; margin-bottom:20px; height: 40px; overflow:hidden;">${site.description || 'Sem descrição.'}</p>
                    <button class="btn-secondary w-100" onclick="alert('Entrando no site: ${site.id}')">Acessar Espaço</button>
                </div>
            `;
        });
        grid.innerHTML = html;
        
    } catch(e) {
        grid.innerHTML = '<p style="color:red;">Erro de comunicação.</p>';
    }
}

function openCreateSiteModal() {
    document.getElementById('create-site-form').style.display = 'block';
}

async function submitCreateSite() {
    const title = document.getElementById('site-title').value;
    const name = document.getElementById('site-name').value;
    const desc = document.getElementById('site-desc').value;
    
    if(!title || !name) {
        alert('Título e URL são obrigatórios');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/ecm/sites`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                name: name,
                description: desc,
                visibility: 'PUBLIC'
            })
        });
        
        if(response.ok) {
            document.getElementById('create-site-form').style.display = 'none';
            document.getElementById('site-title').value = '';
            document.getElementById('site-name').value = '';
            document.getElementById('site-desc').value = '';
            loadSites();
        } else {
            const data = await response.json();
            alert('Erro ao criar site: ' + (data.detail || ''));
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

// --- Biblioteca de Documentos ---
let currentFolderId = null;
let currentFolderPath = []; // Array de {id, name}
let loadedNodes = {}; // Cache de nós para o modal

function renderLibraryTree(nodes) {
    const tree = document.getElementById('library-tree');
    if(!tree) return;

    const folders = nodes.filter(node => node.node_type === 'cm:folder' || node.node_type === 'ies:pasta');
    const items = [{ id: null, name: 'Raiz', level: 0, active: currentFolderPath.length === 0 }];

    currentFolderPath.forEach((folder, index) => {
        items.push({
            id: folder.id,
            name: folder.name,
            level: Math.min(index + 1, 2),
            active: index === currentFolderPath.length - 1
        });
    });

    folders.forEach(folder => {
        items.push({ id: folder.id, name: folder.name, level: currentFolderPath.length ? 2 : 1, active: false });
    });

    tree.innerHTML = items.map(item => `
        <button class="tree-item level-${item.level} ${item.active ? 'active' : ''}" type="button" data-folder-id="${item.id || ''}">
            <i class="fa-solid ${item.active && item.id === null ? 'fa-house' : 'fa-folder'}" aria-hidden="true"></i>
            <span>${item.name}</span>
        </button>
    `).join('');

    tree.querySelectorAll('.tree-item').forEach(button => {
        button.addEventListener('click', () => {
            const folderId = button.dataset.folderId || null;
            if(!folderId) {
                currentFolderPath = [];
                loadLibrary(null);
                return;
            }

            const pathIndex = currentFolderPath.findIndex(folder => folder.id === folderId);
            if(pathIndex >= 0) {
                currentFolderPath = currentFolderPath.slice(0, pathIndex + 1);
            } else {
                const folder = folders.find(item => item.id === folderId);
                if(folder) currentFolderPath.push({ id: folder.id, name: folder.name });
            }
            loadLibrary(folderId);
        });
    });
}

async function loadLibrary(parentId = null) {
    currentFolderId = parentId;
    const grid = document.getElementById('library-grid');
    grid.innerHTML = '<p class="text-muted">Carregando arquivos...</p>';
    
    // Atualizar Breadcrumb
    const btnNavUp = document.getElementById('btn-nav-up');
    const breadcrumb = document.getElementById('breadcrumb');
    
    if(!parentId) {
        btnNavUp.style.display = 'none';
        breadcrumb.innerText = '/ Raiz';
        currentFolderPath = [];
    } else {
        btnNavUp.style.display = 'inline-block';
        let pathStr = '/ Raiz';
        currentFolderPath.forEach(f => {
            pathStr += ` / ${f.name}`;
        });
        breadcrumb.innerText = pathStr;
    }
    
    try {
        let url = `${API_URL}/ecm/nodes`;
        const params = new URLSearchParams();
        if(parentId) params.set('parent_id', parentId);
        const tag = document.getElementById('library-tag-filter')?.value.trim();
        if(tag) params.set('tag', tag);
        if(params.toString()) url += `?${params.toString()}`;
        
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        if(!response.ok) throw new Error("Erro ao carregar");
        const nodes = await response.json();
        
        loadedNodes = {};
        renderLibraryTree(nodes);
        
        if(nodes.length === 0) {
            grid.innerHTML = '<p class="text-muted" style="grid-column: 1 / -1; text-align:center; margin-top:20px;">Pasta vazia.</p>';
            return;
        }
        
        let html = '';
        nodes.forEach(node => {
            loadedNodes[node.id] = node;
            const isFolder = node.node_type === 'cm:folder' || node.node_type === 'ies:pasta';
            const icon = isFolder ? '<i class="fa-solid fa-folder" style="color:#FFD166;"></i>' : '<i class="fa-solid fa-file-lines" style="color:var(--primary);"></i>';
            const onClick = isFolder ? `onclick="navigateDown('${node.id}', '${node.name}')"` : `onclick="openDocumentDetails('${node.id}')"`;
            
            html += `
                <div class="glass-panel" style="padding: 15px; text-align:center; cursor:pointer; transition: transform 0.2s; min-height: 120px; display:flex; flex-direction:column; justify-content:center;" ${onClick} title="${node.name}">
                    <div style="font-size: 32px; margin-bottom:10px;">${icon}</div>
                    <div style="font-size: 13px; font-weight: 500; word-wrap: break-word; overflow:hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                        ${node.name}
                    </div>
                </div>
            `;
        });
        grid.innerHTML = html;
        
    } catch(e) {
        grid.innerHTML = `<p style="color:red;">Falha: ${e.message}</p>`;
    }

    function applyLibraryTagFilter() {
        loadLibrary(currentFolderId);
    }
}

function navigateDown(folderId, folderName) {
    currentFolderPath.push({id: folderId, name: folderName});
    loadLibrary(folderId);
}

function navigateUp() {
    if(currentFolderPath.length === 0) return;
    
    currentFolderPath.pop();
    if(currentFolderPath.length === 0) {
        loadLibrary(null);
    } else {
        const parent = currentFolderPath[currentFolderPath.length - 1];
        loadLibrary(parent.id);
    }
}

async function promptCreateFolder() {
    const folderName = prompt("Nome da nova pasta:");
    if(!folderName) return;
    
    try {
        const response = await fetch(`${API_URL}/ecm/nodes`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                node_type: 'cm:folder',
                name: folderName,
                parent_id: currentFolderId,
                properties: {}
            })
        });
        
        if(response.ok) {
            loadLibrary(currentFolderId);
        } else {
            alert('Erro ao criar pasta.');
        }
    } catch(e) {
        alert('Erro: ' + e);
    }
}

async function uploadToLibrary(files) {
    if(files.length === 0) return;
    
    const formData = new FormData();
    for(let i=0; i<files.length; i++) {
        formData.append("files", files[i]);
    }
    formData.append("node_type", "cm:content");
    if(currentFolderId) {
        formData.append("parent_id", currentFolderId);
    }
    
    document.getElementById('library-grid').innerHTML = '<p class="text-muted" style="grid-column: 1 / -1; text-align:center;">Fazendo upload...</p>';
    
    try {
        const response = await fetch(`${API_URL}/ecm/nodes/upload`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });
        
        if(response.ok) {
            loadLibrary(currentFolderId);
        } else {
            alert('Erro no upload.');
            loadLibrary(currentFolderId);
        }
    } catch(e) {
        alert('Erro: ' + e);
        loadLibrary(currentFolderId);
    }
    
    // Clear input
    document.getElementById('library-upload-input').value = "";
}

function setupLibraryDropzone() {
    const dropzone = document.getElementById('library-grid');
    if(!dropzone || dropzone.dataset.dropzoneReady) return;

    dropzone.dataset.dropzoneReady = 'true';
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add('is-dragging');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove('is-dragging');
        });
    });

    dropzone.addEventListener('drop', (event) => {
        if(event.dataTransfer.files.length > 0) {
            uploadToLibrary(event.dataTransfer.files);
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    loadSearchDocumentTypes();
    updateOcrHelp();
    document.getElementById('search-document-type')?.addEventListener('change', updateSearchIndexHelp);
    document.getElementById('search-group')?.addEventListener('change', () => {
        loadSearchTypeOptions();
    });
    const searchQuery = document.getElementById('search-query');
    if (searchQuery) {
        searchQuery.addEventListener('keydown', event => {
            if (event.key === 'Enter') performSearch();
        });
    }
    setupLibraryDropzone();
});

// --- Document Details Modal (Metadata & Workflows) ---
function openDocumentDetails(nodeId) {
    const node = loadedNodes[nodeId];
    if(!node) return;
    
    document.getElementById('doc-modal-id').value = node.id;
    document.getElementById('doc-modal-title').innerText = node.name;
    document.getElementById('doc-modal-version').innerText = `${node.major_version}.${node.minor_version}`;
    
    // Formatar JSON de propriedades para exibição
    const propsJson = JSON.stringify(node.properties || {}, null, 2);
    document.getElementById('doc-modal-props').value = propsJson;
    renderDocumentTags(node.tags || []);
    
    // Abrir modal na aba meta
    switchModalTab('meta');
    
    // Obter Workflows disponíveis e popular select (Simplificado, fixaremos o ID 1 se for o único, mas o ideal é fazer GET /api/workflows)
    // Para simplificar, vamos assumir que o Workflow Padrão (Revisar & Aprovar) tem id = "1" ou "workflow_uuid".
    // Isso pode requerer um Fetch na API de workflows disponíveis
    
    document.getElementById('document-modal').classList.add('active');
    document.getElementById('document-modal').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeDocumentDetails() {
    document.getElementById('document-modal').classList.remove('active');
}

function renderDocumentTags(tags) {
    const container = document.getElementById('doc-modal-tags');
    if(!container) return;

    container.innerHTML = '';
    if(!tags || tags.length === 0) {
        container.innerHTML = '<span class="text-muted">Nenhuma etiqueta.</span>';
        return;
    }

    tags.forEach(nodeTag => {
        const tag = nodeTag.tag || nodeTag;
        if(!tag || !tag.id) return;

        const tagElement = document.createElement('span');
        tagElement.className = 'document-tag';
        tagElement.append(document.createTextNode(tag.name));

        const removeButton = document.createElement('button');
        removeButton.className = 'document-tag-remove';
        removeButton.type = 'button';
        removeButton.title = `Remover etiqueta ${tag.name}`;
        removeButton.setAttribute('aria-label', `Remover etiqueta ${tag.name}`);
        removeButton.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';
        removeButton.addEventListener('click', () => removeDocumentTag(tag.id));

        tagElement.appendChild(removeButton);
        container.appendChild(tagElement);
    });
}

async function addDocumentTag() {
    const nodeId = document.getElementById('doc-modal-id').value;
    const input = document.getElementById('doc-modal-tag-input');
    const tagName = input.value.trim();
    if(!nodeId || !tagName) return;

    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/tags`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: tagName })
        });

        if(!response.ok) throw new Error('Não foi possível adicionar a etiqueta.');
        const node = await response.json();
        loadedNodes[nodeId] = node;
        renderDocumentTags(node.tags || []);
        input.value = '';
    } catch(error) {
        alert(error.message);
    }
}

async function removeDocumentTag(tagId) {
    const nodeId = document.getElementById('doc-modal-id').value;
    if(!nodeId || !tagId) return;

    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/tags/${tagId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if(!response.ok) throw new Error('Não foi possível remover a etiqueta.');
        const node = loadedNodes[nodeId];
        if(node) {
            node.tags = (node.tags || []).filter(nodeTag => (nodeTag.tag || nodeTag).id !== tagId);
            renderDocumentTags(node.tags);
        }
    } catch(error) {
        alert(error.message);
    }
}

function switchModalTab(tab) {
    const btnMeta = document.getElementById('tab-btn-meta');
    const btnFlow = document.getElementById('tab-btn-flow');
    const divMeta = document.getElementById('tab-meta');
    const divFlow = document.getElementById('tab-flow');
    
    if(tab === 'meta') {
        btnMeta.style.borderBottom = '2px solid var(--primary)';
        btnMeta.style.color = '#fff';
        btnFlow.style.borderBottom = '2px solid transparent';
        btnFlow.style.color = 'var(--text-muted)';
        
        divMeta.style.display = 'block';
        divFlow.style.display = 'none';
    } else {
        btnFlow.style.borderBottom = '2px solid var(--primary)';
        btnFlow.style.color = '#fff';
        btnMeta.style.borderBottom = '2px solid transparent';
        btnMeta.style.color = 'var(--text-muted)';
        
        divFlow.style.display = 'block';
        divMeta.style.display = 'none';
    }
}

async function saveMetadata() {
    const nodeId = document.getElementById('doc-modal-id').value;
    const propsStr = document.getElementById('doc-modal-props').value;
    
    let propsObj;
    try {
        propsObj = JSON.parse(propsStr);
    } catch(e) {
        alert("O JSON de propriedades é inválido.");
        return;
    }

    function previewCurrentDocument() {
        const nodeId = document.getElementById('doc-modal-id').value;
        if(!nodeId) return;
        window.open(`${API_URL}/ecm/nodes/${encodeURIComponent(nodeId)}/preview`, '_blank', 'noopener,noreferrer');
    }
    
    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/properties`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ properties: propsObj })
        });
        
        if(response.ok) {
            alert('Metadados atualizados com sucesso!');
            // Atualizar o cache local
            if(loadedNodes[nodeId]) {
                loadedNodes[nodeId].properties = propsObj;
            }
        } else {
            alert('Erro ao atualizar metadados.');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

async function uploadDocumentVersion(file) {
    const nodeId = document.getElementById('doc-modal-id').value;
    const versionType = document.getElementById('doc-modal-version-type').value;
    const input = document.getElementById('doc-version-input');
    if(!nodeId || !file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('version_type', versionType);

    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/versions`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });

        const data = await response.json();
        if(!response.ok) throw new Error(data.detail || 'Não foi possível enviar a versão.');

        loadedNodes[nodeId] = data;
        document.getElementById('doc-modal-version').innerText = `${data.major_version}.${data.minor_version}`;
        loadVersionHistory();
        alert(`Versão ${data.major_version}.${data.minor_version} enviada com sucesso.`);
    } catch(error) {
        alert(error.message);
    } finally {
        input.value = '';
    }

    async function loadVersionHistory() {
        const nodeId = document.getElementById('doc-modal-id').value;
        const container = document.getElementById('doc-version-history');
        if(!nodeId || !container) return;
        container.innerHTML = '<p class="text-muted">Carregando histórico...</p>';
        try {
            const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/versions`, {
                headers: getAuthHeaders()
            });
            const versions = await response.json();
            if(!response.ok) throw new Error(versions.detail || 'Não foi possível carregar o histórico.');
            container.innerHTML = versions.length
                ? versions.map(version => `
                    <div style="padding:8px 0; border-top:1px solid var(--glass-border); font-size:12px;">
                        <strong>v${version.major_version}.${version.minor_version}</strong>
                        — ${version.file_name}
                        <span class="text-muted">(${version.size} bytes, ${new Date(version.created_at).toLocaleString()})</span>
                    </div>
                `).join('')
                : '<p class="text-muted">Nenhuma versão registrada.</p>';
        } catch(error) {
            container.innerHTML = `<p style="color:var(--accent);">${error.message}</p>`;
        }
    }
}

async function startWorkflowForDocument() {
    const nodeId = document.getElementById('doc-modal-id').value;
    
    // Obter o ID do primeiro workflow existente
    // Fazemos um GET rapido para pegar um ID de workflow válido
    try {
        const wfResp = await fetch(`${API_URL}/workflows`, { headers: getAuthHeaders() });
        if(!wfResp.ok) throw new Error("Não foi possível listar workflows");
        const wfs = await wfResp.json();
        
        if(wfs.length === 0) {
            alert('Nenhum modelo de Workflow foi criado pelo Administrador no sistema.');
            return;
        }
        
        const targetWf = wfs[0]; // Pega o primeiro (Revisar & Aprovar)
        
        const response = await fetch(`${API_URL}/workflows/instances`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_id: nodeId,
                workflow_id: targetWf.id
            })
        });
        
        if(response.ok) {
            alert(`Processo "${targetWf.name}" iniciado com sucesso! A primeira tarefa foi designada e aparecerá no Dashboard.`);
            closeDocumentDetails();
        } else {
            const data = await response.json();
            alert('Erro ao iniciar fluxo: ' + (data.detail || ''));
        }
    } catch(e) {
        alert('Erro: ' + e);
    }
}
