// Scripts para o Gestor de Clínica

// ---- Configurações da Clínica ----
async function loadClinicSettings() {
    try {
        const res = await fetch(`${API_URL}/admin/settings`, { headers: getAuthHeaders() });
        if(res.ok) {
            const settings = await res.json();
            document.getElementById('set-max-upload').value = settings.max_upload_size_mb;
            document.getElementById('set-mime-types').value = settings.allowed_mime_types;
        }
    } catch(e) {
        console.error("Erro ao carregar configurações", e);
    }
}

async function saveClinicSettings() {
    const payload = {
        max_upload_size_mb: parseInt(document.getElementById('set-max-upload').value),
        allowed_mime_types: document.getElementById('set-mime-types').value
    };

    try {
        const res = await fetch(`${API_URL}/admin/settings`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        if(res.ok) {
            alert('Configurações salvas com sucesso!');
        } else {
            alert('Erro ao salvar configurações.');
        }
    } catch(e) {
        console.error("Erro ao salvar configurações", e);
    }
}

// ---- Tipos Documentais ----
function openDocTypeModal() {
    document.getElementById('dt-code').value = '';
    document.getElementById('dt-name').value = '';
    document.getElementById('dt-retention').value = '5';
    document.getElementById('modal-doc-type').classList.add('active');
}

async function loadDocTypes() {
    try {
        const res = await fetch(`${API_URL}/admin/document-types`, { headers: getAuthHeaders() });
        if(res.ok) {
            const types = await res.json();
            const tbody = document.getElementById('table-doc-types-body');
            tbody.innerHTML = '';
            
            if(types.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhum tipo documental cadastrado.</td></tr>';
                return;
            }
            
            types.forEach(t => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${t.code}</td>
                    <td>${t.name}</td>
                    <td>${t.retention_years}</td>
                    <td><span class="badge ${t.is_active ? 'badge-success' : 'badge-danger'}">${t.is_active ? 'Ativo' : 'Inativo'}</span></td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch(e) {
        console.error("Erro ao carregar tipos documentais", e);
        document.getElementById('table-doc-types-body').innerHTML = '<tr><td colspan="4" style="text-align:center">Erro ao carregar.</td></tr>';
    }
}

async function saveDocType() {
    const payload = {
        code: document.getElementById('dt-code').value,
        name: document.getElementById('dt-name').value,
        retention_years: parseInt(document.getElementById('dt-retention').value),
        is_active: true
    };

    try {
        const res = await fetch(`${API_URL}/admin/document-types`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        if(res.ok) {
            document.getElementById('modal-doc-type').classList.remove('active');
            loadDocTypes();
        } else {
            alert('Erro ao salvar tipo documental.');
        }
    } catch(e) {
        console.error("Erro ao salvar tipo documental", e);
    }
}

// ---- Fila de Ingestão (FileWatch) ----
async function loadIngestions() {
    const statusFilter = document.getElementById('ingestion-filter').value;
    let url = `${API_URL}/admin/ingestions`;
    if(statusFilter) {
        url += `?status=${statusFilter}`;
    }

    try {
        const res = await fetch(url, { headers: getAuthHeaders() });
        if(res.ok) {
            const jobs = await res.json();
            const tbody = document.getElementById('table-ingestions-body');
            tbody.innerHTML = '';
            
            if(jobs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">Nenhum arquivo na fila.</td></tr>';
                return;
            }
            
            jobs.forEach(job => {
                let statusBadge = '';
                switch(job.status) {
                    case 'PENDING': statusBadge = '<span class="badge badge-warning">Pendente</span>'; break;
                    case 'PROCESSING': statusBadge = '<span class="badge badge-warning">Processando</span>'; break;
                    case 'COMPLETED': statusBadge = '<span class="badge badge-success">Concluído</span>'; break;
                    case 'FAILED': statusBadge = '<span class="badge badge-danger">Falha</span>'; break;
                    case 'QUARANTINE': statusBadge = '<span class="badge badge-danger">Quarentena</span>'; break;
                    default: statusBadge = `<span class="badge">${job.status}</span>`;
                }

                const filename = job.file_path ? job.file_path.split(/[\/\\]/).pop() : 'N/A';
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-size:12px; font-family:monospace;">${job.id.substring(0,8)}</td>
                    <td>${new Date(job.created_at).toLocaleString('pt-BR')}</td>
                    <td>${filename}</td>
                    <td>${statusBadge}</td>
                    <td style="color:#ef4444; font-size:12px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${job.error_message || ''}">${job.error_message || '-'}</td>
                    <td>
                        ${(job.status === 'QUARANTINE' || job.status === 'FAILED') ? 
                            `<button class="btn-primary btn-small" onclick="retryIngestion('${job.id}')">Retry</button>` : ''}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch(e) {
        console.error("Erro ao carregar ingestions", e);
    }
}

async function retryIngestion(jobId) {
    try {
        const res = await fetch(`${API_URL}/admin/ingestions/${jobId}/retry`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if(res.ok) {
            loadIngestions();
        } else {
            const err = await res.json();
            alert(`Erro: ${err.detail || 'Não foi possível fazer retry.'}`);
        }
    } catch(e) {
        console.error("Erro ao fazer retry", e);
    }
}

setInterval(() => {
    const viewIngestions = document.getElementById('view-ingestions');
    if (viewIngestions && viewIngestions.style.display !== 'none' && viewIngestions.classList.contains('active')) {
        loadIngestions();
    }
}, 15000);
