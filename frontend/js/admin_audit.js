async function loadAuditEvents() {
    try {
        const res = await fetch(`${API_URL}/audit`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error('Falha ao carregar auditoria');
        const data = await res.json();
        
        const tbody = document.getElementById('table-audit-body');
        tbody.innerHTML = '';
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">Nenhum evento registrado.</td></tr>';
            return;
        }
        
        data.forEach(event => {
            const tr = document.createElement('tr');
            
            const dateStr = new Date(event.created_at).toLocaleString('pt-BR');
            const userId = event.user_id ? event.user_id.substring(0,8) + '...' : 'Sistema';
            
            tr.innerHTML = `
                <td>${dateStr}</td>
                <td><span class="badge" style="background:var(--primary); color:#000;">${userId}</span></td>
                <td><strong>${event.action}</strong></td>
                <td>${event.entity} <em>(${event.entity_id.substring(0,8)}...)</em></td>
                <td>${event.details}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        console.error(e);
        alert('Erro ao carregar auditoria');
    }
}

async function verifyAuditChain() {
    try {
        const btn = document.getElementById('btn-verify-audit');
        btn.innerText = 'Verificando...';
        btn.disabled = true;
        
        const res = await fetch(`${API_URL}/audit/verify`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error('Falha ao verificar cadeia');
        const data = await res.json();
        
        if (data.valid) {
            alert(`✅ SUCESSO: A cadeia de auditoria é válida e está intacta.\n\n${data.events_checked} eventos verificados com sucesso.`);
        } else {
            alert(`🚨 ALERTA CRÍTICO: Cadeia adulterada ou inválida!\n\nID do evento suspeito: ${data.tampered_event_id}`);
        }
    } catch(e) {
        console.error(e);
        alert('Erro ao verificar cadeia de auditoria. Talvez você não tenha permissão.');
    } finally {
        const btn = document.getElementById('btn-verify-audit');
        btn.innerText = 'Verificar Integridade (Global)';
        btn.disabled = false;
    }
}

function exportAuditCSV() {
    // Para simplificar, abre a rota de exportação diretamente. 
    // Como a rota requer token, e 'window.open' não manda headers, 
    // precisaremos fazer fetch, criar blob e forçar download.
    
    fetch(`${API_URL}/audit/export/csv`, { headers: getAuthHeaders() })
        .then(res => {
            if (!res.ok) throw new Error('Falha ao exportar');
            return res.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'auditoria.csv';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
        })
        .catch(e => {
            console.error(e);
            alert('Erro ao exportar auditoria para CSV.');
        });
}
