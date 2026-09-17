function obterUsuarioAtual() {
    try {
        const token = localStorage.getItem('ged_token');
        return token && typeof parseJwt === 'function' ? parseJwt(token) : null;
    } catch (erro) {
        console.error('Não foi possível ler o usuário atual.', erro);
        return null;
    }
}

async function openUserModal() {
    let instSelectHtml = '';
    let campusSelectHtml = '';
    const currentUser = obterUsuarioAtual();
    
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

    campusSelectHtml = `
        <div class="form-group">
            <label>Campus (opcional)</label>
            <select id="new-campus" disabled>
                <option value="">Selecione a instituição primeiro</option>
            </select>
        </div>
    `;

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
                        <option value="admin_instituicao">Gestor de Instituição</option>
                        ${currentUser && currentUser.role === 'admin_global' ? '<option value="admin_global">Administrador Global</option>' : ''}
                    </select>
                </div>
                ${instSelectHtml}
                ${campusSelectHtml}
                <button class="btn-primary w-100" onclick="saveUser()">Salvar</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
    const institution = document.getElementById('new-institution');
    if (institution) institution.addEventListener('change', () => carregarCampi(institution.value, 'new-campus'));
    if (currentUser && currentUser.role === 'admin_instituicao') {
        carregarCampi(currentUser.institution_id, 'new-campus');
    }
}

async function carregarCampi(institutionId, selectId, selectedId = '') {
    const select = document.getElementById(selectId);
    if (!select) return;
    if (!institutionId) {
        select.disabled = true;
        select.innerHTML = '<option value="">Selecione a instituição primeiro</option>';
        return;
    }
    select.disabled = true;
    select.innerHTML = '<option value="">Carregando...</option>';
    try {
        const resposta = await fetch(`${API_URL}/campuses?institution_id=${encodeURIComponent(institutionId)}`, {
            headers: getAuthHeaders()
        });
        if (!resposta.ok) throw new Error('Não foi possível carregar os campi.');
        const campi = await resposta.json();
        select.innerHTML = '<option value="">Sem restrição de campus</option>';
        campi.forEach(campus => {
            const option = new Option(campus.name, campus.id, false, campus.id === selectedId);
            select.append(option);
        });
        select.disabled = false;
    } catch (erro) {
        select.innerHTML = '<option value="">Erro ao carregar campi</option>';
        alert(erro.message);
    }
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
            const isActiveText = u.is_active ? 'Ativo' : 'Bloqueado';
            const isActiveClass = u.is_active ? 'badge-success' : 'badge-danger';
            
            tr.innerHTML = `
                <td>${u.username}</td>
                <td><span class="badge ${u.role === 'admin_global' ? 'badge-danger' : 'badge-primary'}">${u.role}</span></td>
                <td><span class="badge ${isActiveClass}">${isActiveText}</span></td>
                <td style="display: flex; gap: 5px;"></td>
            `;
            const tdActions = tr.lastElementChild;
            
            const btnPriv = document.createElement('button');
            btnPriv.className = 'btn-secondary btn-small';
            btnPriv.textContent = 'Tipos e privilégios';
            btnPriv.onclick = () => abrirPermissoesDocumentais(u);
            
            const btnEdit = document.createElement('button');
            btnEdit.className = 'btn-primary btn-small';
            btnEdit.textContent = 'Editar';
            btnEdit.title = 'Editar usuário';
            btnEdit.onclick = () => openEditUserModal(u);

            const btnPassword = document.createElement('button');
            btnPassword.className = 'btn-secondary btn-small';
            btnPassword.textContent = 'Trocar senha';
            btnPassword.title = 'Trocar senha do usuário';
            btnPassword.onclick = () => openChangePasswordModal(u);
            
            const btnToggle = document.createElement('button');
            btnToggle.className = u.is_active ? 'btn-danger btn-small' : 'btn-success btn-small';
            btnToggle.textContent = u.is_active ? 'Bloquear' : 'Desbloquear';
            btnToggle.title = u.is_active ? 'Bloquear usuário' : 'Desbloquear usuário';
            btnToggle.onclick = () => toggleUserStatus(u.id, !u.is_active);
            
            tdActions.appendChild(btnPriv);
            tdActions.appendChild(btnEdit);
            tdActions.appendChild(btnPassword);
            tdActions.appendChild(btnToggle);
            tbody.appendChild(tr);
        });
    } catch(e) {
        tbody.innerHTML = `<tr><td colspan="4" style="color:red">Erro: ${e.message}</td></tr>`;
    }

    function openChangePasswordModal(user) {
        document.getElementById('modal-change-password')?.remove();
        const html = `
            <div class="modal-overlay active" id="modal-change-password">
                <div class="modal-content glass-panel" style="width:400px;padding:30px">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
                        <h2>Trocar senha</h2>
                        <button class="btn-close" type="button" onclick="document.getElementById('modal-change-password').remove()">✖</button>
                    </div>
                    <p>Usuário: <strong>${user.username}</strong></p>
                    <form id="change-password-form">
                        <div class="form-group">
                            <label for="change-password">Nova senha</label>
                            <input type="password" id="change-password" minlength="8" autocomplete="new-password" required>
                        </div>
                        <div class="form-group">
                            <label for="change-password-confirm">Confirmar nova senha</label>
                            <input type="password" id="change-password-confirm" minlength="8" autocomplete="new-password" required>
                        </div>
                        <p id="change-password-error" style="color:#b91c1c" role="alert"></p>
                        <button class="btn-primary w-100" type="submit">Salvar nova senha</button>
                    </form>
                </div>
            </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        document.getElementById('change-password-form').onsubmit = evento => changeUserPassword(evento, user.id);
    }

    async function changeUserPassword(evento, userId) {
        evento.preventDefault();
        const erro = document.getElementById('change-password-error');
        const password = document.getElementById('change-password').value;
        const confirmation = document.getElementById('change-password-confirm').value;
        if (password !== confirmation) {
            erro.textContent = 'As senhas não conferem.';
            return;
        }
        const botao = evento.target.querySelector('button[type="submit"]');
        botao.disabled = true;
        try {
            const response = await fetch(`${API_URL}/users/${userId}/password`, {
                method: 'PUT',
                headers: {...getAuthHeaders(), 'Content-Type': 'application/json'},
                body: JSON.stringify({password})
            });
            if (!response.ok) {
                const detalhe = await response.json().catch(() => ({}));
                throw new Error(detalhe.detail || 'Não foi possível trocar a senha.');
            }
            document.getElementById('modal-change-password').remove();
            alert('Senha alterada com sucesso.');
        } catch (error) {
            erro.textContent = error.message;
            botao.disabled = false;
        }
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
    const campusSelect = document.getElementById('new-campus');
    const campus_id = campusSelect && !campusSelect.disabled ? campusSelect.value || null : null;
    
    try {
        const response = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, role, institution_id, campus_id })
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

function openEditUserModal(user) {
    const currentUser = obterUsuarioAtual();
    const html = `
        <div class="modal-overlay active" id="modal-edit-user">
            <div class="modal-content glass-panel" style="width: 400px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Editar Usuário: ${user.username}</h2>
                    <button class="btn-close" onclick="document.getElementById('modal-edit-user').remove()">✖</button>
                </div>
                <div class="form-group">
                    <label>Papel (Role)</label>
                    <select id="edit-role">
                        <option value="operador" ${user.role === 'operador' ? 'selected' : ''}>Secretaria (Operador)</option>
                        <option value="leitor" ${user.role === 'leitor' ? 'selected' : ''}>Auditor / Leitor</option>
                        <option value="admin_global" ${user.role === 'admin_global' ? 'selected' : ''}>Administrador Global</option>
                        <option value="admin_instituicao" ${user.role === 'admin_instituicao' ? 'selected' : ''}>Gestor de Instituição</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Campus (opcional)</label>
                    <select id="edit-campus" disabled>
                        <option value="">Carregando...</option>
                    </select>
                </div>
                <div class="form-group" style="display: flex; align-items: center; gap: 10px;">
                    <input type="checkbox" id="edit-active" ${user.is_active ? 'checked' : ''} style="width: auto;">
                    <label for="edit-active" style="margin-bottom: 0;">Usuário Ativo</label>
                </div>
                <button class="btn-primary w-100 mt-20" onclick="updateUser('${user.id}')">Salvar Alterações</button>
            </div>
        </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
    carregarCampi(user.institution_id, 'edit-campus', user.campus_id || '');
}

async function updateUser(userId) {
    const role = document.getElementById('edit-role').value;
    const is_active = document.getElementById('edit-active').checked;
    const campus_id = document.getElementById('edit-campus').disabled
        ? null
        : (document.getElementById('edit-campus').value || null);
    
    try {
        const response = await fetch(`${API_URL}/users/${userId}`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ role, is_active, campus_id })
        });
        if(response.ok) {
            document.getElementById('modal-edit-user').remove();
            loadUsers();
        } else {
            const err = await response.json();
            alert("Erro ao editar usuário: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}

async function toggleUserStatus(userId, newStatus) {
    if (!confirm(`Deseja ${newStatus ? 'desbloquear' : 'bloquear'} este usuário?`)) return;
    try {
        const response = await fetch(`${API_URL}/users/${userId}`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ is_active: newStatus })
        });
        if(response.ok) {
            loadUsers();
        } else {
            const err = await response.json();
            alert("Erro ao alterar status: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}
