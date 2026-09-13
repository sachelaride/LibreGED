// admin_ged_config.js - Gerenciamento de Índices e Tipos Documentais

// --- ÍNDICES ---
async function loadIndices() {
    const tbody = document.getElementById('table-indices-body');
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/indices`, { headers: getAuthHeaders() });
        const data = await response.json();
        
        tbody.innerHTML = '';
        if(data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Nenhum índice cadastrado</td></tr>';
            return;
        }

        data.items.forEach(idx => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${idx.name}</td>
                <td><span class="badge badge-primary">${idx.type}</span></td>
                <td><span class="badge badge-success">${idx.is_active ? 'Ativo' : 'Inativo'}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="3" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

function openIndexModal() {
    const html = `
        <div class="modal-overlay active" id="modal-index">
            <div class="modal-content glass-panel" style="width: 400px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Novo Índice</h2>
                    <button class="btn-close" onclick="document.getElementById('modal-index').remove()">✖</button>
                </div>
                <div class="form-group">
                    <label>Nome do Índice (ex: CPF, Matrícula)</label>
                    <input type="text" id="idx-name" required>
                </div>
                <div class="form-group">
                    <label>Tipo de Dado</label>
                    <select id="idx-type" onchange="toggleIndexOptions()">
                        <option value="Texto">Texto</option>
                        <option value="Data">Data</option>
                        <option value="Número">Número</option>
                        <option value="Booleano">Booleano</option>
                        <option value="Lista">Lista</option>
                    </select>
                </div>
                <div class="form-group" id="idx-options-group" style="display:none">
                    <label>Opções da lista (uma por linha)</label>
                    <textarea id="idx-options" rows="5"></textarea>
                </div>
                <div class="form-group">
                    <label>Máscara de validação (expressão regular, opcional)</label>
                    <input type="text" id="idx-mask" placeholder="Ex.: ^[0-9]{11}$">
                </div>
                <div class="form-group">
                    <label><input type="checkbox" id="idx-auto"> Gerar número automaticamente</label>
                </div>
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
    const options = document.getElementById('idx-options').value.split('\n').map(v => v.trim()).filter(Boolean);
    const mask = document.getElementById('idx-mask').value.trim() || null;
    const auto_increment = document.getElementById('idx-auto').checked;
    
    try {
        const response = await fetch(`${API_URL}/indices`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, type, options, mask, auto_increment, is_active: true })
        });
        if(response.ok) {
            document.getElementById('modal-index').remove();
            loadIndices();
        } else {
            alert("Erro ao salvar índice");
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
                <td><button class="btn-secondary btn-small" onclick="selectDocType('${dt.id}', '${dt.name}')">Detalhes</button></td>
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
    
    // TODO: load indices
    loadXsds(id);
}

async function openDocTypeModal() {
    document.getElementById('modal-doc-type').classList.add('active');
    
    // Load storage areas
    const areaSelect = document.getElementById('dt-area');
    areaSelect.innerHTML = '<option value="">Carregando...</option>';
    try {
        const res = await fetch(`${API_URL}/storage/areas`, { headers: getAuthHeaders() });
        const areas = await res.json();
        let html = '<option value="">-- Selecione (Opcional) --</option>';
        areas.forEach(a => { html += `<option value="${a.id}">${a.name}</option>`; });
        areaSelect.innerHTML = html;
    } catch(e) {
        areaSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

async function loadPartitionsForArea(areaId) {
    const partSelect = document.getElementById('dt-partition');
    if(!areaId) {
        partSelect.innerHTML = '<option value="">Selecione uma área primeiro</option>';
        return;
    }
    partSelect.innerHTML = '<option value="">Carregando partições...</option>';
    try {
        const res = await fetch(`${API_URL}/storage/areas/${areaId}/partitions`, { headers: getAuthHeaders() });
        const parts = await res.json();
        if(parts.length > 0) {
            let html = '<option value="">Selecione a Partição</option>';
            parts.forEach(p => { html += `<option value="${p.id}">${p.name}</option>`; });
            partSelect.innerHTML = html;
        } else {
            partSelect.innerHTML = '<option value="">Nenhuma partição encontrada. Crie uma na aba Armazenamento.</option>';
        }
    } catch(e) {
        partSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

async function saveDocType() {
    const name = document.getElementById('dt-name').value;
    const group_id = document.getElementById('dt-group').value;
    const retention = parseInt(document.getElementById('dt-retention').value);
    const legalHold = document.getElementById('dt-legal-hold').checked;
    const areaId = document.getElementById('dt-area').value;
    const partId = document.getElementById('dt-partition').value;
    
    const workflowId = document.getElementById('dt-workflow').value.trim() || null;

    if(!name || !group_id || Number.isNaN(retention) || retention < 0) {
        alert("Preencha todos os campos obrigatórios.");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/document-types`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                name: name, 
                storage_area_id: areaId,
                storage_partition_id: partId,
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

