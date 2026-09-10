// Scripts para o Gestor de Instituição

// ---- Configurações da Instituição ----
async function loadInstitutionSettings() {
    try {
        const res = await fetch(`${API_URL}/admin/settings`, { headers: getAuthHeaders() });
        if(res.ok) {
            const settings = await res.json();
            document.getElementById('set-max-upload').value = settings.max_upload_size_mb;
            document.getElementById('set-mime-types').value = settings.allowed_mime_types;
            document.getElementById('set-antimalware').checked = settings.antimalware_enabled;
            document.getElementById('set-quarantine').checked = settings.quarantine_enabled;
            document.getElementById('set-quarantine-policy').value = settings.quarantine_policy;
        }
        
        // Carrega propostas
        loadProposals();
    } catch(e) {
        console.error("Erro ao carregar configurações", e);
    }
}

async function loadProposals() {
    try {
        const res = await fetch(`${API_URL}/admin/settings/proposals`, { headers: getAuthHeaders() });
        if(res.ok) {
            const proposals = await res.json();
            const tbody = document.getElementById('table-proposals-body');
            tbody.innerHTML = '';
            
            proposals.forEach(p => {
                const tr = document.createElement('tr');
                const date = new Date(p.created_at).toLocaleString();
                
                let actions = '';
                if (p.status === 'PENDING') {
                    actions = `
                        <button class="btn-primary btn-small" onclick="approveProposal('${p.id}')">Aprovar</button>
                        <button class="btn-secondary btn-small" onclick="rejectProposal('${p.id}')">Rejeitar</button>
                    `;
                } else if (p.status === 'APPROVED' && p.previous_payload_json) {
                    actions = `<button class="btn-secondary btn-small" onclick="revertProposal('${p.id}')">Reverter</button>`;
                }
                
                let statusBadge = p.status;
                if (p.status === 'APPROVED') statusBadge = '<span style="color: green; font-weight: bold;">APROVADA</span>';
                if (p.status === 'REJECTED') statusBadge = '<span style="color: red; font-weight: bold;">REJEITADA</span>';
                if (p.status === 'PENDING') statusBadge = '<span style="color: orange; font-weight: bold;">PENDENTE</span>';
                if (p.status === 'REVERTED') statusBadge = '<span style="color: gray; font-weight: bold;">REVERTIDA</span>';
                
                tr.innerHTML = `
                    <td>${date}</td>
                    <td>${p.proposed_by_id.substring(0,8)}...</td>
                    <td>${statusBadge}</td>
                    <td>${actions}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch(e) {
        console.error("Erro ao carregar propostas", e);
    }
}

async function approveProposal(id) {
    if(!confirm("Tem certeza que deseja aprovar e aplicar essa configuração imediatamente?")) return;
    try {
        const res = await fetch(`${API_URL}/admin/settings/proposals/${id}/approve`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if(res.ok) {
            alert('Proposta aprovada! O Hot-Reload já aplicou as regras no servidor.');
            loadInstitutionSettings();
        } else {
            alert('Erro ao aprovar.');
        }
    } catch(e) {
        console.error(e);
    }
}

async function rejectProposal(id) {
    if(!confirm("Tem certeza que deseja rejeitar essa proposta?")) return;
    try {
        const res = await fetch(`${API_URL}/admin/settings/proposals/${id}/reject`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if(res.ok) {
            alert('Proposta rejeitada.');
            loadProposals();
        } else {
            alert('Erro ao rejeitar.');
        }
    } catch(e) {
        console.error(e);
    }
}

async function revertProposal(id) {
    if(!confirm("Atenção: Isso fará um Rollback imediato (Hot-Reload) para as configurações antes dessa proposta. Confirma?")) return;
    try {
        const res = await fetch(`${API_URL}/admin/settings/proposals/${id}/revert`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if(res.ok) {
            alert('Rollback executado com sucesso! A configuração antiga está valendo novamente.');
            loadInstitutionSettings();
        } else {
            alert('Erro ao reverter.');
        }
    } catch(e) {
        console.error(e);
    }
}

async function saveInstitutionSettings() {
    const payload = {
        max_upload_size_mb: parseInt(document.getElementById('set-max-upload').value),
        allowed_mime_types: document.getElementById('set-mime-types').value,
        antimalware_enabled: document.getElementById('set-antimalware').checked,
        quarantine_enabled: document.getElementById('set-quarantine').checked,
        quarantine_policy: document.getElementById('set-quarantine-policy').value
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
            alert('Proposta de configuração enviada/salva com sucesso!');
            loadProposals();
        } else {
            alert('Erro ao salvar/propor configurações.');
        }
    } catch(e) {
        console.error("Erro ao propor configurações", e);
    }
}

// Para manter compatibilidade com admin.html
window.saveClinicSettings = saveInstitutionSettings;

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
