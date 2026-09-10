async function loadDashboardStats() {
    try {
        const res = await fetch(`${API_URL}/dashboard/stats`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error('Falha ao carregar dashboard');
        const data = await res.json();
        
        // Health
        const dbStatus = document.getElementById('dash-db-status');
        dbStatus.innerText = data.health.database;
        dbStatus.style.color = data.health.database === 'Online' ? '#4ade80' : '#ef4444';
        document.getElementById('dash-int-count').innerText = data.health.integrations_count;
        
        // Ingestion
        document.getElementById('dash-ingest-processing').innerText = data.ingestion.processing;
        document.getElementById('dash-ingest-pending').innerText = data.ingestion.pending;
        document.getElementById('dash-ingest-failed').innerText = data.ingestion.failed;
        
        // Alerts
        const quarantineEl = document.getElementById('dash-quarantine-count');
        quarantineEl.innerText = data.quarantine_documents;
        if (data.quarantine_documents > 0) {
            quarantineEl.style.color = '#ef4444'; // Red alert
        } else {
            quarantineEl.style.color = '#fff';
        }
        
        document.getElementById('dash-wf-active').innerText = data.workflow.active_instances;
        
    } catch(e) {
        console.error(e);
        document.getElementById('dash-db-status').innerText = 'Erro';
        document.getElementById('dash-db-status').style.color = '#ef4444';
    }
}

// Quando carregar a aba de dashboard, carrega os dados
document.addEventListener('DOMContentLoaded', () => {
    // Por padrão o admin já carrega na view-dashboard (tá ativa no HTML)
    // Então vamos chamar a função de cara
    const token = localStorage.getItem('ged_token');
    if (token) {
        loadDashboardStats();
    }
});
