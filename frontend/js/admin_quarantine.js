async function loadQuarantine() {
    try {
        const res = await fetch(`${API_URL}/quarantine`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('Falha ao carregar quarentena');
        const docs = await res.json();
        
        const tbody = document.getElementById('table-quarantine-body');
        tbody.innerHTML = '';
        
        if (docs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhum documento na quarentena.</td></tr>';
            return;
        }
        
        docs.forEach(d => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${d.id.split('-')[0]}...</td>
                <td>${d.title}</td>
                <td>${new Date(d.created_at).toLocaleString()}</td>
                <td>
                    <button class="btn-primary btn-small" onclick="releaseQuarantine('${d.id}')">Liberar</button>
                    <button class="btn-danger btn-small" style="background:#ef4444; color:white; border:none; padding:5px 10px; border-radius:4px; cursor:pointer;" onclick="deleteQuarantine('${d.id}')">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
        alert('Erro ao carregar quarentena');
    }
}

async function releaseQuarantine(id) {
    if(!confirm('Tem certeza que deseja liberar este arquivo? O risco será assumido por você.')) return;
    
    try {
        const res = await fetch(`${API_URL}/quarantine/${id}/release`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('Falha ao liberar');
        
        alert('Arquivo liberado com sucesso!');
        loadQuarantine();
    } catch(e) {
        alert(e.message);
    }
}

async function deleteQuarantine(id) {
    if(!confirm('Tem certeza que deseja apagar DEFINITIVAMENTE este arquivo malicioso?')) return;
    
    try {
        const res = await fetch(`${API_URL}/quarantine/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('Falha ao excluir');
        
        alert('Arquivo excluído com sucesso!');
        loadQuarantine();
    } catch(e) {
        alert(e.message);
    }
}
