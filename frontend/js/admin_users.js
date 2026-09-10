async function openUserModal() {
    let instSelectHtml = '';
    const currentUser = JSON.parse(localStorage.getItem('user'));
    
    if (currentUser && currentUser.role === 'admin_global') {
        try {
            const res = await fetch(`${API_URL}/institutions`, { headers: getAuthHeaders() });
            const data = await res.json();
            
            let options = '<option value="">-- Selecione uma Instituição --</option>';
            data.items.forEach(inst => {
                options += `<option value="${inst.id}">${inst.name} (${inst.cnpj})</option>`;
            });
            
            instSelectHtml = `
                <div class="form-group">
                    <label>Instituição</label>
                    <select id="new-institution">
                        ${options}
                    </select>
                </div>
            `;
        } catch (e) {
            console.error("Erro ao carregar instituições:", e);
        }
    }

    const html = `
        <div class="modal-overlay active" id="modal-user">
            <div class="modal-content glass-panel" style="width: 400px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Novo Usuário</h2>
                    <button class="btn-close" onclick="document.getElementById('modal-user').remove()">✖</button>
                </div>
                <div class="form-group">
                    <label>Usuário</label>
                    <input type="text" id="new-username" required>
                </div>
                <div class="form-group">
                    <label>Senha</label>
                    <input type="password" id="new-password" required>
                </div>
                <div class="form-group">
                    <label>Papel (Role)</label>
                    <select id="new-role">
                        <option value="operador">Secretaria (Operador)</option>
                        <option value="leitor">Auditor / Leitor</option>
                        <option value="admin_global">Administrador Global</option>
                        <option value="admin_instituicao">Gestor de Instituição</option>
                        ${currentUser && currentUser.role === 'admin_global' ? '<option value="admin_global">Administrador Global</option>' : ''}
                    </select>
                </div>
                ${instSelectHtml}
                <button class="btn-primary w-100" onclick="saveUser()">Salvar</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function loadUsers() {
    const tbody = document.getElementById('table-users-body');
    if (!tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/users`, { headers: getAuthHeaders() });
        const data = await response.json();
        tbody.innerHTML = '';
        
        if (data.items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhum usuário encontrado.</td></tr>';
            return;
        }
        
        data.items.forEach(u => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${u.username}</td>
                <td><span class="badge ${u.role === 'admin_global' ? 'badge-danger' : 'badge-primary'}">${u.role}</span></td>
                <td>Ativo</td>
                <td>-</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="4" style="color:red">Erro: ${e.message}</td></tr>`;
    }
}

async function saveUser() {
    const username = document.getElementById('new-username').value;
    const password = document.getElementById('new-password').value;
    const role = document.getElementById('new-role').value;
    
    let institution_id = null;
    const instSelect = document.getElementById('new-institution');
    if (instSelect) {
        institution_id = instSelect.value;
    }
    
    try {
        const response = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, role, institution_id })
        });
        if(response.ok) {
            document.getElementById('modal-user').remove();
            loadUsers();
        } else {
            const err = await response.json();
            alert("Erro ao salvar usuário: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}
