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
                <button class="btn-primary w-100" onclick="saveInstitution()">Salvar</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function loadInstitutions() {
    const tbody = document.getElementById('table-institutions-body');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/institutions`, { headers: getAuthHeaders() });
        const data = await response.json();
        tbody.innerHTML = '';
        
        if (data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhuma instituição encontrada.</td></tr>';
            return;
        }
        
        data.items.forEach(inst => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${inst.name}</td>
                <td>${inst.cnpj}</td>
                <td>${inst.legal_name}</td>
                <td><span class="badge badge-success">Ativa</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="4" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

async function saveInstitution() {
    const name = document.getElementById('inst-name').value;
    const legal_name = document.getElementById('inst-legal-name').value;
    const cnpj = document.getElementById('inst-cnpj').value;
    
    try {
        const response = await fetch(`${API_URL}/institutions`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, legal_name, cnpj })
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
