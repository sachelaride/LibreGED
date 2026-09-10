// JS para gestão de Workflows (Inspirado no Mayan EDMS / Alfresco)
const WORKFLOWS_API = `${API_URL}/workflows`;
let currentWorkflowId = null;

async function loadWorkflows() {
    try {
        const response = await fetch(WORKFLOWS_API, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        const rawData = await response.json();
        const workflows = rawData.items ? rawData.items : rawData;
        
        const tbody = document.getElementById('table-workflows-body');
        tbody.innerHTML = '';
        
        if (!workflows || workflows.length === 0) {
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
    loadedStates = states;
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
                <br>
                Roles: <span style="color:#fcd34d;">${t.allowed_roles || 'Todos'}</span>
            </div>
        `;
        list.appendChild(li);
    });
}

let loadedStates = [];

function openWorkflowModal() {
    document.getElementById('wf-name').value = '';
    document.getElementById('wf-internal').value = '';
    document.getElementById('modal-workflow').classList.add('active');
}

async function saveWorkflow() {
    const name = document.getElementById('wf-name').value;
    const internal = document.getElementById('wf-internal').value;
    
    try {
        const resp = await fetch(WORKFLOWS_API, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: name, internal_name: internal, is_active: true })
        });
        
        if (resp.ok) {
            document.getElementById('modal-workflow').classList.remove('active');
            loadWorkflows();
        } else {
            alert('Erro ao salvar workflow');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

function openStateModal() {
    document.getElementById('state-label').value = '';
    document.getElementById('state-initial').checked = false;
    document.getElementById('state-completion').checked = false;
    document.getElementById('modal-state').classList.add('active');
}

async function saveState() {
    const label = document.getElementById('state-label').value;
    const is_initial = document.getElementById('state-initial').checked;
    const is_completion = document.getElementById('state-completion').checked;
    
    try {
        const resp = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/states`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ label, is_initial, is_completion })
        });
        
        if(resp.ok) {
            document.getElementById('modal-state').classList.remove('active');
            loadWorkflows(); // Recarrega tudo para atualizar a lista
        } else {
            alert('Erro ao salvar estado');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

function openTransitionModal() {
    const origin = document.getElementById('trans-origin');
    const dest = document.getElementById('trans-dest');
    origin.innerHTML = '';
    dest.innerHTML = '';
    
    loadedStates.forEach(s => {
        const opt1 = document.createElement('option');
        opt1.value = s.id; opt1.innerText = s.label;
        origin.appendChild(opt1);
        
        const opt2 = document.createElement('option');
        opt2.value = s.id; opt2.innerText = s.label;
        dest.appendChild(opt2);
    });
    
    document.getElementById('trans-label').value = '';
    document.getElementById('trans-roles').value = '';
    document.getElementById('modal-transition').classList.add('active');
}

async function saveTransition() {
    const originId = document.getElementById('trans-origin').value;
    const destId = document.getElementById('trans-dest').value;
    const label = document.getElementById('trans-label').value;
    const roles = document.getElementById('trans-roles').value;
    
    try {
        const resp = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/transitions`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ origin_state_id: originId, destination_state_id: destId, label, allowed_roles: roles || null })
        });
        
        if(resp.ok) {
            document.getElementById('modal-transition').classList.remove('active');
            loadWorkflows();
        } else {
            alert('Erro ao salvar transição');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

// Inicializar carregamento quando a view é mostrada
document.addEventListener('DOMContentLoaded', () => {
    const menus = document.querySelectorAll('.sidebar-nav li, .menu-item');
    menus.forEach(menu => {
        menu.addEventListener('click', () => {
            if (menu.innerText.includes('Workflows')) {
                loadWorkflows();
            }
        });
    });
});
