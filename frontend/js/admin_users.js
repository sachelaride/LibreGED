function openUserModal() {
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
                        <option value="recepcao">Usuário Padrão (Secretaria)</option>
                        <option value="admin_global">Administrador Global</option>
                    </select>
                </div>
                <button class="btn-primary w-100" onclick="saveUser()">Salvar</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
}

async function loadUsers() {
    const tbody = document.getElementById('table-users-body');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/users`, { headers: getAuthHeaders() });
        const users = await response.json();
        tbody.innerHTML = '';
        users.forEach(u => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${u.username}</td>
                <td><span class="badge ${u.role === 'admin' ? 'badge-danger' : 'badge-primary'}">${u.role}</span></td>
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
    
    try {
        const response = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, role })
        });
        if(response.ok) {
            document.getElementById('modal-user').remove();
            loadUsers();
        } else {
            alert("Erro ao salvar usuário");
        }
    } catch(e) {
        alert(e.message);
    }
}
