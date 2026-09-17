// admin_ged_config.js - Gerenciamento de Índices e Tipos Documentais

// --- ÍNDICES ---
async function loadIndices() {
    const tbody = document.getElementById('table-indices-body');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/indices`, { headers: getAuthHeaders() });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Falha ao carregar índices');
        
        tbody.innerHTML = '';
        const items = Array.isArray(data) ? data : (data.items || []);
        if(items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhum índice cadastrado</td></tr>';
            return;
        }

        items.forEach(idx => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${idx.name}</td>
                <td><span class="badge badge-primary">${idx.type}</span></td>
                <td><span class="badge badge-success">${idx.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td>
                    <button class="btn-secondary btn-small" onclick="editIndex('${idx.id}', '${idx.name}', '${idx.type}', '${(idx.options || []).join('\\n')}', '${idx.mask || ''}', ${idx.auto_increment}, ${idx.is_active})">Editar</button>
                    <button class="btn-danger btn-small" onclick="deleteIndex('${idx.id}')">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="4" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

let currentIndexId = null;

function openIndexModal() {
    currentIndexId = null;
    renderIndexModal();
}

function editIndex(id, name, type, options, mask, auto_increment, is_active) {
    currentIndexId = id;
    renderIndexModal(name, type, options, mask, auto_increment, is_active);
}

function renderIndexModal(name = '', type = 'Texto', options = '', mask = '', auto_increment = false, is_active = true) {
    const existing = document.getElementById('modal-index');
    if (existing) existing.remove();

    const html = `
        <div class="modal-overlay active" id="modal-index">
            <div class="modal-content glass-panel" style="width: 400px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>${currentIndexId ? 'Editar Índice' : 'Novo Índice'}</h2>
                    <button class="btn-close" onclick="document.getElementById('modal-index').remove()">✖</button>
                </div>
                <div class="form-group">
                    <label>Nome do Índice (ex: CPF, Matrícula)</label>
                    <input type="text" id="idx-name" value="${name}" required>
                </div>
                <div class="form-group">
                    <label>Tipo de Dado</label>
                    <select id="idx-type" onchange="toggleIndexOptions()">
                        <option value="Texto" ${type === 'Texto' ? 'selected' : ''}>Texto</option>
                        <option value="Data" ${type === 'Data' ? 'selected' : ''}>Data</option>
                        <option value="Número" ${type === 'Número' ? 'selected' : ''}>Número</option>
                        <option value="Booleano" ${type === 'Booleano' ? 'selected' : ''}>Booleano</option>
                        <option value="Lista" ${type === 'Lista' ? 'selected' : ''}>Lista</option>
                    </select>
                </div>
                <div class="form-group" id="idx-options-group" style="display:${type === 'Lista' ? 'block' : 'none'}">
                    <label>Opções da lista (uma por linha)</label>
                    <textarea id="idx-options" rows="5">${options}</textarea>
                </div>
                <div class="form-group">
                    <label>Máscara de validação (expressão regular, opcional)</label>
                    <input type="text" id="idx-mask" value="${mask}" placeholder="Ex.: ^[0-9]{11}$">
                </div>
                <div class="form-group">
                    <label><input type="checkbox" id="idx-auto" ${auto_increment ? 'checked' : ''}> Gerar número automaticamente</label>
                </div>
                ${currentIndexId ? `<div class="form-group">
                    <label><input type="checkbox" id="idx-active" ${is_active ? 'checked' : ''}> Ativo</label>
                </div>` : ''}
                <button class="btn-primary w-100" onclick="saveIndex()">Salvar Índice</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

function toggleIndexOptions() {
    const grupo = document.getElementById('idx-options-group');
    grupo.style.display = document.getElementById('idx-type').value === 'Lista' ? 'block' : 'none';
}

async function saveIndex() {
    const name = document.getElementById('idx-name').value;
    const type = document.getElementById('idx-type').value;
    const options = document.getElementById('idx-options').value.split('\\n').map(v => v.trim()).filter(Boolean);
    const mask = document.getElementById('idx-mask').value.trim() || null;
    const auto_increment = document.getElementById('idx-auto').checked;
    const is_active_el = document.getElementById('idx-active');
    const is_active = is_active_el ? is_active_el.checked : true;
    
    const url = currentIndexId ? `${API_URL}/indices/${currentIndexId}` : `${API_URL}/indices`;
    const method = currentIndexId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, type, options, mask, auto_increment, is_active })
        });
        if(response.ok) {
            document.getElementById('modal-index').remove();
            loadIndices();
        } else {
            const err = await response.json();
            alert("Erro ao salvar índice: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}

async function deleteIndex(id) {
    if(!confirm('Tem certeza que deseja excluir este índice?')) return;
    try {
        const response = await fetch(`${API_URL}/indices/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if(response.ok || response.status === 204) {
            loadIndices();
        } else {
            const err = await response.json();
            alert("Erro ao excluir índice: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}

// --- TIPOS DOCUMENTAIS (MASTER DETAIL) ---
let currentDocTypeId = null;

async function loadDocTypes() {
    const tbody = document.getElementById('table-doctypes-body');
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/document-types`, { headers: getAuthHeaders() });
        const data = await response.json();
        
        tbody.innerHTML = '';
        if(data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Nenhum Tipo Documental cadastrado</td></tr>';
            return;
        }

        data.items.forEach(dt => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${dt.name}</strong><br><small style="color:#888;">${dt.group_id || 'Sem grupo'}</small></td>
                <td>${dt.retention_years} anos<br>${dt.legal_hold ? '<span class="badge badge-primary">Legal Hold</span>' : ''}</td>
                <td>
                    <button class="btn-secondary btn-small" onclick="selectDocType('${dt.id}', '${dt.name}')">Detalhes</button>
                    <button class="btn-primary btn-small" onclick="editDocType('${dt.id}', '${dt.name}', '${dt.group_id || ''}', ${dt.retention_years}, ${dt.legal_hold}, '${dt.storage_area_id || ''}', '${dt.storage_partition_id || ''}', '${dt.workflow_id || ''}')">Editar</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="3" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

function selectDocType(id, name) {
    currentDocTypeId = id;
    document.getElementById('current-doctype-name').innerText = name;
    document.getElementById('btn-add-index').disabled = false;
    document.getElementById('btn-add-xsd').disabled = false;
    
    loadMappedIndices(id);
    loadXsds(id);
}

async function loadMappedIndices(docTypeId = currentDocTypeId) {
    const tbody = document.getElementById('table-mapped-indices-body');
    if (!tbody || !docTypeId) return;
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Carregando...</td></tr>';
    try {
        const response = await fetch(`${API_URL}/document-types/${docTypeId}/indices`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Falha ao carregar índices vinculados');
        const items = Array.isArray(data) ? data : (data.items || []);
        tbody.innerHTML = '';
        if (!items.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhum índice vinculado</td></tr>';
            return;
        }
        items.forEach(mapping => {
            const index = mapping.index || {};
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${index.name || mapping.index_id}</td>
                <td>${index.type || '-'}</td>
                <td>${mapping.is_required ? 'Sim' : 'Não'}</td>
                <td><button class="btn-danger btn-small" onclick="removeDocTypeIndex('${docTypeId}', '${mapping.id}')">Excluir</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="4" style="color:red">Erro: ${error.message}</td></tr>`;
    }
}

async function removeDocTypeIndex(docTypeId, mappingId) {
    if (!confirm('Excluir este vínculo de índice?')) return;
    const response = await fetch(`${API_URL}/document-types/${docTypeId}/indices/${mappingId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!response.ok) {
        const data = await response.json();
        alert(`Erro ao excluir vínculo: ${data.detail || 'operação recusada'}`);
        return;
    }
    await loadMappedIndices(docTypeId);
}

let currentEditDocTypeId = null;

async function openDocTypeModal() {
    currentEditDocTypeId = null;
    document.getElementById('dt-name').value = '';
    document.getElementById('dt-group').value = '';
    document.getElementById('dt-retention').value = '5';
    document.getElementById('dt-legal-hold').checked = false;
    document.getElementById('dt-workflow').value = '';
    document.getElementById('dt-partition').value = '';
    
    await loadStorageAreas();
    document.getElementById('modal-doc-type').classList.add('active');
}

async function editDocType(id, name, group_id, retention_years, legal_hold, area_id, partition_id, workflow_id) {
    currentEditDocTypeId = id;
    document.getElementById('dt-name').value = name;
    document.getElementById('dt-group').value = group_id;
    document.getElementById('dt-retention').value = retention_years;
    document.getElementById('dt-legal-hold').checked = legal_hold;
    document.getElementById('dt-workflow').value = workflow_id;
    
    document.getElementById('dt-partition').value = partition_id || slugifyDocumentType(name);
    await loadStorageAreas(area_id || null);
    document.getElementById('dt-area').value = area_id || '';
    
    document.getElementById('modal-doc-type').classList.add('active');
}

async function loadStorageAreas(selectedAreaId = null) {
    const areaSelect = document.getElementById('dt-area');
    areaSelect.innerHTML = '<option value="">Carregando armazenamentos...</option>';
    try {
        const response = await fetch(`${API_URL}/storage-rules?size=200`, {
            headers: getAuthHeaders()
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || 'Falha ao carregar armazenamentos');
        }

        const rules = Array.isArray(data) ? data : (data.items || []);
        areaSelect.innerHTML = '<option value="">-- Selecione (Opcional) --</option>';
        rules.forEach(rule => {
            const status = rule.is_active ? '' : ' (inativo)';
            const option = document.createElement('option');
            option.value = rule.id;
            option.textContent = `${rule.name} - ${rule.storage_type} - ${rule.base_path}${status}`;
            areaSelect.appendChild(option);
        });
        areaSelect.value = selectedAreaId || '';
        if (!rules.length) {
            areaSelect.innerHTML = '<option value="">Nenhuma regra de armazenamento cadastrada</option>';
        }
    } catch (error) {
        areaSelect.innerHTML = `<option value="">Erro: ${error.message}</option>`;
    }
}

function loadPartitionsForArea() {
    // A partição é um subdiretório lógico, não uma entidade de storage separada.
}

function slugifyDocumentType(value) {
    return value
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');
}

async function saveDocType() {
    const name = document.getElementById('dt-name').value;
    const group_id = document.getElementById('dt-group').value;
    const retention = parseInt(document.getElementById('dt-retention').value);
    const legalHold = document.getElementById('dt-legal-hold').checked;
    const areaId = document.getElementById('dt-area').value;
    const partId = document.getElementById('dt-partition').value.trim() || slugifyDocumentType(name);
    
    const workflowId = document.getElementById('dt-workflow').value.trim() || null;

    if(!name || !group_id || Number.isNaN(retention) || retention < 0) {
        alert("Preencha todos os campos obrigatórios.");
        return;
    }

    const url = currentEditDocTypeId ? `${API_URL}/document-types/${currentEditDocTypeId}` : `${API_URL}/document-types`;
    const method = currentEditDocTypeId ? 'PUT' : 'POST';

    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                name: name, 
                storage_area_id: areaId || null,
                storage_partition_id: partId || null,
                is_active: true,
                group_id: group_id,
                retention_years: retention,
                legal_hold: legalHold
                ,workflow_id: workflowId
            })
        });
        if(response.ok) {
            document.getElementById('modal-doc-type').classList.remove('active');
            loadDocTypes();
        } else {
            alert("Erro ao salvar tipo documental");
        }
    } catch(e) {
        alert(e.message);
    }
}

// --- SCHEMA XSD ---

async function loadXsds(docTypeId) {
    const tbody = document.getElementById('table-xsd-body');
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/xsd?document_type_id=${docTypeId}`, { headers: getAuthHeaders() });
        const data = await response.json();
        
        tbody.innerHTML = '';
        if(data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Nenhum Schema cadastrado</td></tr>';
            return;
        }

        data.items.forEach(xsd => {
            const tr = document.createElement('tr');
            let statusBadge = '<span class="badge badge-warning">Proposto</span>';
            if(xsd.status === 'approved') statusBadge = '<span class="badge badge-success">Vigente</span>';
            if(xsd.status === 'retired') statusBadge = '<span class="badge badge-secondary">Aposentado</span>';
            
            let btnApprove = xsd.status === 'proposed' ? `<button class="btn-primary btn-small" onclick="approveXsd('${xsd.id}')">Aprovar</button>` : '';
            
            tr.innerHTML = `
                <td><strong>${xsd.code}</strong><br><small style="color:#888;">${xsd.namespace}</small></td>
                <td>${statusBadge}</td>
                <td>${btnApprove}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="3" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

function openXsdModal() {
    if(!currentDocTypeId) return;
    document.getElementById('xsd-id').value = '';
    document.getElementById('xsd-code').value = '';
    document.getElementById('xsd-namespace').value = '';
    document.getElementById('xsd-hash').value = '';
    document.getElementById('modal-xsd').classList.add('active');
}

function editXsd(id, code, namespace, hash) {
    document.getElementById('xsd-id').value = id;
    document.getElementById('xsd-code').value = code;
    document.getElementById('xsd-namespace').value = namespace;
    document.getElementById('xsd-hash').value = hash;
    document.getElementById('modal-xsd').classList.add('active');
}

async function saveXsd() {
    if(!currentDocTypeId) return;
    
    const xsdId = document.getElementById('xsd-id').value;
    const payload = {
        document_type_id: currentDocTypeId,
        code: document.getElementById('xsd-code').value,
        namespace: document.getElementById('xsd-namespace').value,
        xsd_hash: document.getElementById('xsd-hash').value,
        environment: 'homologation'
    };
    
    const method = xsdId ? 'PUT' : 'POST';
    const url = xsdId ? `${API_URL}/xsd/${xsdId}` : `${API_URL}/xsd`;
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        if(response.ok) {
            document.getElementById('modal-xsd').classList.remove('active');
            loadXsds(currentDocTypeId);
        } else {
            const err = await response.json();
            alert("Erro ao salvar XSD: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}

async function deleteXsd(id) {
    if(!confirm("Tem certeza que deseja excluir este schema?")) return;
    try {
        const response = await fetch(`${API_URL}/xsd/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if(response.ok || response.status === 204) {
            loadXsds(currentDocTypeId);
        } else {
            const err = await response.json();
            alert("Erro ao excluir XSD: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}

async function approveXsd(id) {
    if(!confirm('Tem certeza que deseja aprovar e tornar este schema Vigente? Isso irá aposentar o schema atual.')) return;
    
    try {
        const response = await fetch(`${API_URL}/xsd/${id}/approve`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if(response.ok) {
            loadXsds(currentDocTypeId);
        } else {
            alert("Erro ao aprovar XSD");
        }
    } catch(e) {
        alert(e.message);
    }
}

async function openDocTypeIndexModal() {
    if (!currentDocTypeId) return alert("Selecione um tipo documental primeiro.");
    
    document.getElementById('dt-index-required').checked = true;
    document.getElementById('dt-index-unique').checked = false;
    
    // Load indices
    const select = document.getElementById('dt-index-select');
    select.innerHTML = '<option value="">Carregando...</option>';
    
    try {
        const response = await fetch(`${API_URL}/indices`, { headers: getAuthHeaders() });
        const data = await response.json();
        select.innerHTML = '';
        if (data.items.length === 0) {
            select.innerHTML = '<option value="">Nenhum índice cadastrado</option>';
        } else {
            data.items.forEach(idx => {
                const opt = document.createElement('option');
                opt.value = idx.id;
                opt.text = idx.name;
                select.appendChild(opt);
            });
        }
    } catch(e) {
        console.error(e);
        select.innerHTML = '<option value="">Erro ao carregar</option>';
    }
    
    document.getElementById('modal-doctype-index').classList.add('active');
}

async function saveDocTypeIndex() {
    if (!currentDocTypeId) return;
    
    const index_id = document.getElementById('dt-index-select').value;
    const is_required = document.getElementById('dt-index-required').checked;
    const is_unique = document.getElementById('dt-index-unique').checked;
    
    if (!index_id) return alert("Selecione um índice");
    
    try {
        const response = await fetch(`${API_URL}/document-types/${currentDocTypeId}/indices`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ index_id, is_required, is_unique })
        });
        
        if (response.ok) {
            document.getElementById('modal-doctype-index').classList.remove('active');
            await loadMappedIndices();
            alert("Índice vinculado com sucesso!");
        } else {
            const err = await response.json();
            alert("Erro: " + (err.detail || "Falha ao vincular"));
        }
    } catch(e) {
        alert("Erro de conexão");
        console.error(e);
    }
}
