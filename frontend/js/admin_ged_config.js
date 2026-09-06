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
                    <select id="idx-type">
                        <option value="Texto">Texto</option>
                        <option value="Data">Data</option>
                        <option value="Número">Número</option>
                        <option value="Booleano">Booleano</option>
                    </select>
                </div>
                <button class="btn-primary w-100" onclick="saveIndex()">Salvar Índice</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function saveIndex() {
    const name = document.getElementById('idx-name').value;
    const type = document.getElementById('idx-type').value;
    
    try {
        const response = await fetch(`${API_URL}/indices`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, type, is_active: true })
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

// --- TIPOS DOCUMENTAIS ---
async function loadDocTypes() {
    const tbody = document.getElementById('table-doc-types-body');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/document-types`, { headers: getAuthHeaders() });
        const data = await response.json();
        
        tbody.innerHTML = '';
        if(data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhum Tipo Documental cadastrado</td></tr>';
            return;
        }

        data.items.forEach(dt => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${dt.name}</td>
                <td><span class="badge" style="background:rgba(255,255,255,0.2)">${dt.storage_area_id.substring(0,8)}...</span></td>
                <td><span class="badge badge-success">${dt.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td><button class="btn-secondary btn-small" onclick="alert('Associar indices em breve...')">Vincular Índices</button></td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="4" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

async function openDocTypeModal() {
    // Buscar areas e particoes para preencher os selects
    let areasHtml = '<option value="">Carregando...</option>';
    let partsHtml = '<option value="">Selecione uma área primeiro</option>';
    
    try {
        const res = await fetch(`${API_URL}/storage/areas`, { headers: getAuthHeaders() });
        const areas = await res.json();
        if(areas.length > 0) {
            areasHtml = '<option value="">Selecione a Área Base</option>';
            areas.forEach(a => { areasHtml += `<option value="${a.id}">${a.name}</option>`; });
        } else {
            areasHtml = '<option value="">Crie uma Área de Armazenamento primeiro</option>';
        }
    } catch(e) { }

    const html = `
        <div class="modal-overlay active" id="modal-doctype">
            <div class="modal-content glass-panel" style="width: 450px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Novo Tipo Documental</h2>
                    <button class="btn-close" onclick="document.getElementById('modal-doctype').remove()">✖</button>
                </div>
                <div class="form-group">
                    <label>Nome do Tipo (ex: Histórico Escolar)</label>
                    <input type="text" id="dt-name" required>
                </div>
                <div class="form-group">
                    <label>Área de Armazenamento Destino</label>
                    <select id="dt-area" onchange="loadPartitionsForArea(this.value)">
                        ${areasHtml}
                    </select>
                </div>
                <div class="form-group">
                    <label>Partição Específica</label>
                    <select id="dt-partition">
                        ${partsHtml}
                    </select>
                </div>
                <button class="btn-primary w-100" onclick="saveDocType()">Salvar Tipo Documental</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
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
    const areaId = document.getElementById('dt-area').value;
    const partId = document.getElementById('dt-partition').value;
    
    if(!name || !areaId || !partId) {
        alert("Preencha o nome, selecione a Área e a Partição.");
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
                is_active: true 
            })
        });
        if(response.ok) {
            document.getElementById('modal-doctype').remove();
            loadDocTypes();
        } else {
            alert("Erro ao salvar tipo documental");
        }
    } catch(e) {
        alert(e.message);
    }
}
