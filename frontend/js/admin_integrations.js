async function loadIntegrations() {
    try {
        const res = await fetch(`${API_URL}/integrations`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error('Falha ao carregar');
        const integrations = await res.json();
        
        const tbody = document.getElementById('table-integrations-body');
        tbody.innerHTML = '';
        
        if (integrations.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">Nenhuma integração configurada.</td></tr>';
            return;
        }
        
        integrations.forEach(int => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${int.name}</td>
                <td><span class="badge" style="background:#3b82f6;">${int.integration_type}</span></td>
                <td>${int.base_url || '-'}</td>
                <td><span class="badge" style="background:${int.is_active ? '#4ade80' : '#ef4444'};">${int.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td>${int.has_secret ? '<span style="color:#4ade80">Sim (Criptografado)</span>' : '<span style="color:#aaa">Não</span>'}</td>
                <td>
                    <button class="btn-secondary btn-small" onclick="editIntegration('${int.id}')">Editar</button>
                    <button class="btn-danger btn-small" style="background:#ef4444; border:none; padding:5px; border-radius:4px; color:white; cursor:pointer;" onclick="deleteIntegration('${int.id}')">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        console.error(e);
        alert('Erro ao carregar integrações');
    }
}

function openIntegrationModal() {
    document.getElementById('integration-modal-title').innerText = 'Nova Integração';
    document.getElementById('int-id').value = '';
    document.getElementById('int-name').value = '';
    document.getElementById('int-type').value = 'WEBHOOK';
    document.getElementById('int-base-url').value = '';
    document.getElementById('int-secret').value = '';
    document.getElementById('int-active').checked = true;
    document.getElementById('int-secret-help').innerText = 'Será criptografado no banco de dados.';
    document.getElementById('modal-integration').classList.add('active');
}

let allIntegrations = [];

async function editIntegration(id) {
    // Busca a integração na api
    try {
        const res = await fetch(`${API_URL}/integrations`, { headers: getAuthHeaders() });
        const integrations = await res.json();
        const int = integrations.find(i => i.id === id);
        if(!int) return;
        
        document.getElementById('integration-modal-title').innerText = 'Editar Integração';
        document.getElementById('int-id').value = int.id;
        document.getElementById('int-name').value = int.name;
        document.getElementById('int-type').value = int.integration_type;
        document.getElementById('int-base-url').value = int.base_url || '';
        document.getElementById('int-secret').value = ''; // Sempre vazio
        document.getElementById('int-active').checked = int.is_active;
        document.getElementById('int-secret-help').innerText = 'Deixe em branco para manter a credencial atual. (Seguro)';
        
        document.getElementById('modal-integration').classList.add('active');
    } catch(e) {
        alert(e);
    }
}

async function saveIntegration() {
    const id = document.getElementById('int-id').value;
    const name = document.getElementById('int-name').value;
    const type = document.getElementById('int-type').value;
    const baseUrl = document.getElementById('int-base-url').value;
    const secret = document.getElementById('int-secret').value;
    const isActive = document.getElementById('int-active').checked;
    
    const payload = {
        name,
        integration_type: type,
        base_url: baseUrl || null,
        is_active: isActive
    };
    
    if (secret) payload.secret = secret; // Só envia se o usuário digitou algo
    
    try {
        let url = `${API_URL}/integrations`;
        let method = 'POST';
        if (id) {
            url += `/${id}`;
            method = 'PUT';
        }
        
        const res = await fetch(url, {
            method,
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if(!res.ok) throw new Error('Erro ao salvar');
        
        document.getElementById('modal-integration').classList.remove('active');
        loadIntegrations();
    } catch(e) {
        alert(e);
    }
}

async function deleteIntegration(id) {
    if(!confirm('Certeza que deseja excluir esta integração? Isso pode quebrar automações.')) return;
    
    try {
        const res = await fetch(`${API_URL}/integrations/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if(!res.ok) throw new Error('Erro ao excluir');
        loadIntegrations();
    } catch(e) {
        alert(e);
    }
}
