// JS para gestão de Workflows (Inspirado no Mayan EDMS / Alfresco)
const WORKFLOWS_API = `${API_URL}/workflows`;
let currentWorkflowId = null;

async function loadWorkflows() {
    try {
        const response = await fetch(WORKFLOWS_API, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        const workflows = await response.json();
        
        const tbody = document.getElementById('table-workflows-body');
        tbody.innerHTML = '';
        
        if (workflows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" style="text-align:center">Nenhum workflow cadastrado.</td></tr>';
            return;
        }
        
        workflows.forEach(w => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.onclick = () => selectWorkflow(w);
            tr.innerHTML = `
                <td>${w.name}</td>
                <td><span class="badge" style="background: ${w.is_active ? '#4ade80' : '#ef4444'}">${w.is_active ? 'Ativo' : 'Inativo'}</span></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro ao carregar workflows', err);
    }
}

function selectWorkflow(workflow) {
    currentWorkflowId = workflow.id;
    document.getElementById('current-workflow-name').innerText = workflow.name;
    document.getElementById('btn-add-state').disabled = false;
    document.getElementById('btn-add-transition').disabled = false;
    
    renderStates(workflow.states || []);
    renderTransitions(workflow.transitions || [], workflow.states || []);
}

function renderStates(states) {
    const list = document.getElementById('list-states');
    list.innerHTML = '';
    
    if (states.length === 0) {
        list.innerHTML = '<li style="text-align:center; color: #aaa; margin-top: 20px;">Nenhum estado cadastrado.</li>';
        return;
    }
    
    states.forEach(s => {
        const li = document.createElement('li');
        li.style.padding = '8px';
        li.style.borderBottom = '1px solid rgba(255,255,255,0.1)';
        li.innerHTML = `
            <strong>${s.label}</strong>
            <div style="font-size: 11px; color: #aaa;">
                ${s.is_initial ? '🟢 Inicial' : ''}
                ${s.is_completion ? '🔴 Final' : ''}
            </div>
        `;
        list.appendChild(li);
    });
}

function renderTransitions(transitions, states) {
    const list = document.getElementById('list-transitions');
    list.innerHTML = '';
    
    if (transitions.length === 0) {
        list.innerHTML = '<li style="text-align:center; color: #aaa; margin-top: 20px;">Nenhuma transição cadastrada.</li>';
        return;
    }
    
    const stateMap = {};
    states.forEach(s => stateMap[s.id] = s.label);
    
    transitions.forEach(t => {
        const li = document.createElement('li');
        li.style.padding = '8px';
        li.style.borderBottom = '1px solid rgba(255,255,255,0.1)';
        li.innerHTML = `
            <div style="font-weight: bold; color: #60a5fa;">${t.label}</div>
            <div style="font-size: 11px; color: #aaa;">
                De: ${stateMap[t.origin_state_id] || 'Desconhecido'} ➔ 
                Para: ${stateMap[t.destination_state_id] || 'Desconhecido'}
            </div>
        `;
        list.appendChild(li);
    });
}

// Inicializar carregamento quando a view é mostrada
document.addEventListener('DOMContentLoaded', () => {
    const menus = document.querySelectorAll('.sidebar-nav li');
    menus.forEach(menu => {
        menu.addEventListener('click', () => {
            if (menu.innerText.includes('Workflows')) {
                loadWorkflows();
            }
        });
    });
});
