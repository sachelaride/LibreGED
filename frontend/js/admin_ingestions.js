// JS para Ingestões
const INGESTIONS_API = `${API_URL}/admin/ingestions`;

async function loadIngestions() {
    const status = document.getElementById('ingestion-filter').value;
    let url = INGESTIONS_API;
    if (status) url += `?status=${status}`;

    try {
        const resp = await fetch(url, { headers: getAuthHeaders() });
        const ingestions = await resp.json();

        const tbody = document.getElementById('table-ingestions-body');
        tbody.innerHTML = '';

        if (ingestions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">Nenhuma ingestão encontrada.</td></tr>';
            return;
        }

        ingestions.forEach(ing => {
            const tr = document.createElement('tr');
            let actions = '';
            if (ing.status === 'FAILED' || ing.status === 'QUARANTINE') {
                actions = `<button class="btn-primary btn-small" onclick="retryIngestion('${ing.id}')">Tentar Novamente</button>`;
            }
            if (ing.status === 'CONFLICT') {
                actions = `<button class="btn-secondary btn-small" onclick="inspectConflict('${ing.id}')">Detalhes</button>
                    <button class="btn-primary btn-small" onclick="resolveConflict('${ing.id}')">Encerrar conflito</button>`;
            }

            tr.innerHTML = `
                <td>${ing.id.substring(0, 8)}...</td>
                <td>${new Date(ing.created_at).toLocaleString()}</td>
                <td>${ing.file_path || '-'}</td>
                <td><span class="badge" style="background:${getStatusColor(ing.status)}">${ing.status}</span></td>
                <td style="color:red; font-size:12px;">${ing.error_message || '-'}</td>
                <td>${actions}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        console.error('Erro ao buscar ingestões:', e);
    }
}

async function retryIngestion(jobId) {
    if(!confirm("Tentar reprocessar esta ingestão?")) return;

    try {
        const resp = await fetch(`${INGESTIONS_API}/${jobId}/retry`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        
        if (resp.ok) {
            alert('Ingestão reenviada para a fila.');
            loadIngestions();
        } else {
            alert('Erro ao tentar novamente.');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

function getStatusColor(status) {
    if (status === 'COMPLETED') return '#4ade80';
    if (status === 'FAILED') return '#ef4444';
    if (status === 'QUARANTINE') return '#f59e0b';
    if (status === 'CONFLICT') return '#dc2626';
    if (status === 'CONFLICT_RESOLVED') return '#6b7280';
    if (status === 'RETRY') return '#a78bfa';
    return '#60a5fa'; // PENDING
}

async function inspectConflict(jobId) {
    const resp = await fetch(`${INGESTIONS_API}/${jobId}/conflict`, { headers: getAuthHeaders() });
    const data = await resp.json();
    if (!resp.ok) {
        alert(data.detail || 'Não foi possível consultar o conflito.');
        return;
    }
    alert(`Conflito ${data.id}\nHash: ${data.file_hash || '-'}\nErro: ${data.error_message || '-'}`);
}

async function resolveConflict(jobId) {
    if (!confirm('Encerrar este conflito sem sobrescrever a entrega original?')) return;
    const resp = await fetch(`${INGESTIONS_API}/${jobId}/resolve-conflict`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    const data = await resp.json();
    if (!resp.ok) {
        alert(data.detail || 'Não foi possível encerrar o conflito.');
        return;
    }
    alert('Conflito encerrado e preservado para auditoria.');
    loadIngestions();
}
