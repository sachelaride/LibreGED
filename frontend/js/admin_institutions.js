function openInstitutionModal() {
    const html = `
        <div class="modal-overlay active" id="modal-institution">
            <div class="modal-content glass-panel" style="width: 400px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Nova Instituição</h2>
                    <button class="btn-close" onclick="document.getElementById('modal-institution').remove()">✖</button>
                </div>
                <div class="form-group">
                    <label>Nome Fantasia</label>
                    <input type="text" id="inst-name" required>
                </div>
                <div class="form-group">
                    <label>Razão Social</label>
                    <input type="text" id="inst-legal-name" required>
                </div>
                <div class="form-group">
                    <label>CNPJ</label>
                    <input type="text" id="inst-cnpj" required>
                </div>
                <input type="hidden" id="inst-id">
                <button class="btn-primary w-100" onclick="saveInstitution()">Salvar</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function loadInstitutions() {
    const tbody = document.getElementById('table-institutions-body');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/institutions`, { headers: getAuthHeaders() });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || `Falha ao carregar instituições (${response.status})`);
        }

        // Accept both the paginated contract and the legacy list response while
        // deployments are upgraded independently.
        const institutions = Array.isArray(data) ? data : data.items;
        if (!Array.isArray(institutions)) {
            throw new Error('Resposta inválida da API de instituições.');
        }

        tbody.innerHTML = '';
        
        if (institutions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Nenhuma instituição encontrada.</td></tr>';
            return;
        }
        
        institutions.forEach(inst => {
            const tr = document.createElement('tr');
            // Safe JSON stringify for the button onclick
            const instJson = JSON.stringify(inst).replace(/"/g, '&quot;');
            tr.innerHTML = `
                <td>${inst.name}</td>
                <td>${inst.cnpj}</td>
                <td>${inst.legal_name}</td>
                <td><span class="badge badge-success">Ativa</span></td>
                <td>
                    <button class="btn-secondary btn-small" onclick="editInstitution('${instJson}')">Editar</button>
                    <button class="btn-secondary btn-small" onclick="deleteInstitution('${inst.id}')" style="background:#ef4444;border-color:#ef4444;">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="5" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

async function saveInstitution() {
    const name = document.getElementById('inst-name').value;
    const legal_name = document.getElementById('inst-legal-name').value;
    const cnpj = document.getElementById('inst-cnpj').value;
    const instId = document.getElementById('inst-id').value;
    
    try {
        const method = instId ? 'PUT' : 'POST';
        const url = instId ? `${API_URL}/institutions/${instId}` : `${API_URL}/institutions`;
        const payload = instId ? { name, legal_name } : { name, legal_name, cnpj };
        
        const response = await fetch(url, {
            method: method,
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if(response.ok) {
            document.getElementById('modal-institution').remove();
            loadInstitutions();
        } else {
            const err = await response.json();
            alert("Erro ao salvar instituição: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}

function editInstitution(instStr) {
    const inst = JSON.parse(instStr);
    openInstitutionModal();
    document.getElementById('inst-name').value = inst.name;
    document.getElementById('inst-legal-name').value = inst.legal_name;
    document.getElementById('inst-cnpj').value = inst.cnpj;
    document.getElementById('inst-cnpj').disabled = true; // CNPJ não pode ser editado
    document.getElementById('inst-id').value = inst.id;
}

async function deleteInstitution(id) {
    if(!confirm("Tem certeza que deseja excluir esta instituição? Apenas será possível se não houver vínculos.")) return;
    
    try {
        const response = await fetch(`${API_URL}/institutions/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if(response.ok || response.status === 204) {
            alert('Instituição excluída com sucesso.');
            loadInstitutions();
        } else {
            const err = await response.json();
            alert("Erro ao excluir: " + (err.detail || ""));
        }
    } catch(e) {
        alert("Erro de conexão.");
    }
}
