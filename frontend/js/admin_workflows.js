// JS para gestão de Workflows (Inspirado no Mayan EDMS / Alfresco)
const WORKFLOWS_API = `${API_URL}/workflows`;
let currentWorkflowId = null;
let currentWorkflowData = null;
let editor = null;

async function loadWorkflows() {
    try {
        const response = await fetch(WORKFLOWS_API, {
            headers: getAuthHeaders()
        });
        if (!response.ok) {
            throw new Error((await response.json()).detail || `HTTP ${response.status}`);
        }
        const rawData = await response.json();
        const workflows = rawData.items ? rawData.items : rawData;
        window.workflowsData = workflows;
        
        const tbody = document.getElementById('table-workflows-body');
        tbody.innerHTML = '';
        
        if (!workflows || workflows.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" style="text-align:center">Nenhum workflow cadastrado.</td></tr>';
            return;
        }
        
        workflows.forEach(w => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.innerHTML = `
                <td onclick="selectWorkflow('${w.id}')">${w.name}</td>
                <td onclick="selectWorkflow('${w.id}')"><span class="badge" style="background: ${w.is_active ? '#4ade80' : '#ef4444'}">${w.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td>
                    <button class="btn-secondary btn-small" onclick="editWorkflow('${w.id}'); event.stopPropagation();">Editar</button>
                    <button class="btn-secondary btn-small" onclick="deleteWorkflow('${w.id}'); event.stopPropagation();" style="background:#ef4444;border-color:#ef4444;">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro ao carregar workflows', err);
        const tbody = document.getElementById('table-workflows-body');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align:center;color:#ef4444">Erro ao carregar: ${err.message}</td></tr>`;
        }
    }
}

function selectWorkflow(idOrObj) {
    const workflow = typeof idOrObj === 'string' ? window.workflowsData.find(w => w.id === idOrObj) : idOrObj;
    if (!workflow) return;
    currentWorkflowId = workflow.id;
    currentWorkflowData = workflow;
    document.getElementById('current-workflow-name').innerText = workflow.name;
    document.getElementById('btn-add-state').disabled = false;
    document.getElementById('bpmn-toolbox').style.display = 'flex';
    document.getElementById('editor-hint').innerText = 'Arraste ou clique em um elemento do painel esquerdo para criar um nó';
    
    initDrawflow();
    renderDrawflow(workflow.states || [], workflow.transitions || []);
}

function initDrawflow() {
    if (editor) return;
    const container = document.getElementById("drawflow");
    editor = new Drawflow(container);
    editor.reroute = true;
    editor.start();
    
    // Events
    editor.on('nodeMoved', async (id) => {
        if(isRendering) return;
        const node = editor.getNodeFromId(id);
        const stateId = node.data.stateId;
        const posX = node.pos_x;
        const posY = node.pos_y;
        
        try {
            await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/states/${stateId}`, {
                method: 'PUT',
                headers: {
                    ...getAuthHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ ui_pos_x: posX, ui_pos_y: posY })
            });
        } catch(e) { console.error(e); }
    });
    
    editor.on('connectionCreated', (info) => {
        if(isRendering) return; // ignore events during render
        const originNode = editor.getNodeFromId(info.output_id);
        const destNode = editor.getNodeFromId(info.input_id);
        openTransitionVisualModal(originNode.data.stateId, destNode.data.stateId);
    });
    
    editor.on('connectionRemoved', async (info) => {
        if(isRendering) return;
        const originNode = editor.getNodeFromId(info.output_id);
        const destNode = editor.getNodeFromId(info.input_id);
        const originStateId = originNode.data.stateId;
        const destStateId = destNode.data.stateId;
        
        const transition = currentWorkflowData.transitions.find(t => t.origin_state_id === originStateId && t.destination_state_id === destStateId);
        
        if (transition) {
            try {
                const resp = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/transitions/${transition.id}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                });
                if(resp.ok) {
                    const wRes = await fetch(WORKFLOWS_API, { headers: getAuthHeaders() });
                    const wData = await wRes.json();
                    const workflows = wData.items ? wData.items : wData;
                    const updated = workflows.find(w => w.id === currentWorkflowId);
                    if(updated) { currentWorkflowData = updated; }
                }
            } catch(e) { console.error(e); }
        }
    });

    editor.on('nodeRemoved', async (id) => {
        if(isRendering) return;
        const stateId = nodeStateMap_inv[id];
        if(!stateId) return;
        
        try {
            const resp = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/states/${stateId}`, {
                method: 'DELETE',
                headers: getAuthHeaders()
            });
            if(resp.ok) {
                const wRes = await fetch(WORKFLOWS_API, { headers: getAuthHeaders() });
                const wData = await wRes.json();
                const workflows = wData.items ? wData.items : wData;
                const updated = workflows.find(w => w.id === currentWorkflowId);
                if(updated) { currentWorkflowData = updated; }
            } else {
                alert("Erro ao remover o estado visualmente.");
            }
        } catch(e) { console.error(e); }
    });
}

let isRendering = false;
let nodeStateMap = {}; // stateId -> drawflowNodeId
let nodeStateMap_inv = {}; // drawflowNodeId -> stateId

function renderSingleNode(s, fallbackIndex = 0) {
    let nType = s.node_type || 'task_user';
    let html_content = '';
    
    if (nType.startsWith('event_')) {
        let color = '#3b82f6';
        let icon = 'fa-envelope';
        if(nType === 'event_start') { color = '#4ade80'; icon = 'fa-play'; }
        if(nType === 'event_end') { color = '#ef4444'; icon = 'fa-stop'; }
        
        html_content = `
        <div style="border-radius:50%; width:60px; height:60px; border:3px solid ${color}; display:flex; align-items:center; justify-content:center; background:#fff; flex-direction:column; margin:0 auto; user-select:none; pointer-events:none;">
            <i class="fa-solid ${icon}" style="color:${color}; font-size:20px;"></i>
        </div>
        <div style="text-align:center; font-size:10px; margin-top:5px; color:#333; user-select:none;"><strong>${s.label}</strong></div>`;
    } else if (nType.startsWith('gateway_')) {
        let icon = nType === 'gateway_exclusive' ? 'fa-xmark' : 'fa-plus';
        html_content = `
        <div style="width:50px; height:50px; border:2px solid #facc15; background:#fef08a; transform: rotate(45deg); display:flex; align-items:center; justify-content:center; margin:10px auto; user-select:none; pointer-events:none;">
            <i class="fa-solid ${icon}" style="transform: rotate(-45deg); color:#ca8a04;"></i>
        </div>
        <div style="text-align:center; font-size:10px; margin-top:15px; color:#333; user-select:none;"><strong>${s.label}</strong></div>`;
    } else {
        let icon = 'fa-user';
        if(nType === 'task_service') icon = 'fa-gear';
        if(nType === 'task_script') icon = 'fa-code';
        
        html_content = `
        <div style="border:2px solid #cbd5e1; border-radius:8px; background:#fff; min-width:120px; padding:10px; box-shadow:0 2px 4px rgba(0,0,0,0.05); user-select:none;">
            <div style="display:flex; align-items:center; margin-bottom:5px; pointer-events:none;">
                <i class="fa-solid ${icon}" style="color:#64748b; font-size:12px; margin-right:5px;"></i>
                <strong style="font-size:11px; color:#334155;">${nType === 'task_user' ? 'Usuário' : (nType === 'task_service' ? 'Serviço' : 'Script')}</strong>
            </div>
            <div style="font-size:12px; font-weight:600; text-align:center; pointer-events:none;">${s.label}</div>
        </div>`;
    }

    const storedX = Number(s.ui_pos_x);
    const storedY = Number(s.ui_pos_y);
    const hasUsablePosition = Number.isFinite(storedX) && Number.isFinite(storedY)
        && storedX >= 20 && storedY >= 20 && storedX < 3000 && storedY < 3000;
    const posX = hasUsablePosition ? storedX : 80 + (fallbackIndex % 3) * 220;
    const posY = hasUsablePosition ? storedY : 80 + Math.floor(fallbackIndex / 3) * 150;
    
    let in_con = 1;
    let out_con = 1;
    if(nType === 'event_start') in_con = 0;
    if(nType === 'event_end') out_con = 0;
    
    const nodeId = editor.addNode('state', in_con, out_con, posX, posY, 'state', { stateId: s.id }, html_content);
    nodeStateMap[s.id] = nodeId;
    nodeStateMap_inv[nodeId] = s.id;
}

function renderDrawflow(states, transitions) {
    if(!editor) return;
    isRendering = true;
    editor.clear();
    editor.clearModuleSelected();
    nodeStateMap = {};
    nodeStateMap_inv = {};
    
    // Create nodes
    states.forEach((s, index) => {
        renderSingleNode(s, index);
    });
    // Create connections
    transitions.forEach(t => {
        const originNodeId = nodeStateMap[t.origin_state_id];
        const destNodeId = nodeStateMap[t.destination_state_id];
        if(originNodeId && destNodeId) {
            editor.addConnection(originNodeId, destNodeId, 'output_1', 'input_1');
        }
    });
    
    isRendering = false;
}

function openWorkflowModal() {
    document.getElementById('wf-id').value = '';
    document.getElementById('wf-name').value = '';
    document.getElementById('wf-internal').value = '';
    document.getElementById('modal-workflow').classList.add('active');
}

async function saveWorkflow() {
    const wfId = document.getElementById('wf-id').value;
    const payload = {
        name: document.getElementById('wf-name').value,
        internal_name: document.getElementById('wf-internal').value,
        is_active: true
    };
    
    const method = wfId ? 'PUT' : 'POST';
    const url = wfId ? `${WORKFLOWS_API}/${wfId}` : WORKFLOWS_API;

    try {
        const resp = await fetch(url, {
            method: method,
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (resp.ok) {
            document.getElementById('modal-workflow').classList.remove('active');
            loadWorkflows();
        } else {
            const err = await resp.json();
            alert("Erro ao salvar: " + (err.detail || ''));
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

function editWorkflow(idOrObj) {
    const wkf = typeof idOrObj === 'string' ? window.workflowsData.find(w => w.id === idOrObj) : idOrObj;
    if (!wkf) return;
    document.getElementById('wf-id').value = wkf.id;
    document.getElementById('wf-name').value = wkf.name;
    document.getElementById('wf-internal').value = wkf.internal_name;
    document.getElementById('modal-workflow').classList.add('active');
}

async function deleteWorkflow(id) {
    if(!confirm("Tem certeza que deseja excluir este workflow?")) return;
    
    try {
        const response = await fetch(`${WORKFLOWS_API}/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if(response.ok || response.status === 204) {
            alert('Workflow excluído com sucesso.');
            if (currentWorkflowId === id) {
                currentWorkflowId = null;
                document.getElementById('current-workflow-name').innerText = "Selecione um workflow";
                document.getElementById('btn-add-state').disabled = true;
                if(editor) editor.clearModuleSelected();
            }
            loadWorkflows();
        } else {
            const err = await response.json();
            alert("Erro ao excluir workflow: " + (err.detail || ""));
        }
    } catch(e) {
        alert("Erro de conexão.");
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
            body: JSON.stringify({ label, is_initial, is_completion, ui_pos_x: 100, ui_pos_y: 100 })
        });
        
        if(resp.ok) {
            document.getElementById('modal-state').classList.remove('active');
            
            // Reload just this workflow to get the new state
            const wRes = await fetch(WORKFLOWS_API, { headers: getAuthHeaders() });
            const wData = await wRes.json();
            const workflows = wData.items ? wData.items : wData;
            const updated = workflows.find(w => w.id === currentWorkflowId);
            if(updated) selectWorkflow(updated);
        } else {
            alert('Erro ao salvar estado');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

let pendingTransitionData = null;

function openTransitionVisualModal(originId, destId) {
    pendingTransitionData = { originId, destId };
    
    // We reuse the transition modal, but we lock the selects
    const origin = document.getElementById('trans-origin');
    const dest = document.getElementById('trans-dest');
    origin.innerHTML = '';
    dest.innerHTML = '';
    
    const states = currentWorkflowData.states;
    states.forEach(s => {
        const opt1 = document.createElement('option');
        opt1.value = s.id; opt1.innerText = s.label;
        origin.appendChild(opt1);
        
        const opt2 = document.createElement('option');
        opt2.value = s.id; opt2.innerText = s.label;
        dest.appendChild(opt2);
    });
    
    origin.value = originId;
    origin.disabled = true;
    dest.value = destId;
    dest.disabled = true;
    
    document.getElementById('trans-label').value = '';
    document.getElementById('trans-action-code').value = '';
    document.getElementById('trans-condition-key').value = '';
    document.getElementById('trans-condition-value').value = '';
    document.getElementById('trans-priority').value = 0;
    document.getElementById('trans-default').checked = false;
    document.getElementById('trans-roles').value = '';
    document.getElementById('modal-transition').classList.add('active');
}

function cancelTransition() {
    document.getElementById('modal-transition').classList.remove('active');
    if(pendingTransitionData && editor) {
        // Find the connection and remove it since user cancelled
        const outId = nodeStateMap[pendingTransitionData.originId];
        const inId = nodeStateMap[pendingTransitionData.destId];
        
        isRendering = true;
        editor.removeSingleConnection(outId, inId, 'output_1', 'input_1');
        isRendering = false;
        pendingTransitionData = null;
    }
}

// Intercepting form submit inside modal-transition:
async function saveTransition() {
    const originId = document.getElementById('trans-origin').value;
    const destId = document.getElementById('trans-dest').value;
    const label = document.getElementById('trans-label').value;
    const action_code = document.getElementById('trans-action-code').value.trim() || null;
    const condition_key = document.getElementById('trans-condition-key').value.trim() || null;
    const condition_value = document.getElementById('trans-condition-value').value.trim() || null;
    const priority = Number.parseInt(document.getElementById('trans-priority').value, 10) || 0;
    const is_default = document.getElementById('trans-default').checked;
    const roles = document.getElementById('trans-roles').value;
    
    try {
        const resp = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/transitions`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ origin_state_id: originId, destination_state_id: destId, label, action_code, condition_key, condition_value, priority, is_default, allowed_roles: roles || null })
        });
        
        if(resp.ok) {
            document.getElementById('modal-transition').classList.remove('active');
            pendingTransitionData = null;
            
            // Reload workflow
            const wRes = await fetch(WORKFLOWS_API, { headers: getAuthHeaders() });
            const wData = await wRes.json();
            const workflows = wData.items ? wData.items : wData;
            const updated = workflows.find(w => w.id === currentWorkflowId);
            if(updated) selectWorkflow(updated);
        } else {
            alert('Erro ao salvar transição');
            cancelTransition();
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
        cancelTransition();
    }
}

// Override transition close button behavior
document.addEventListener('DOMContentLoaded', () => {
    // Escutar se o menu Templates foi clicado para carregar dados
    const menus = document.querySelectorAll('.sidebar-nav li, .menu-item');
    menus.forEach(menu => {
        menu.addEventListener('click', () => {
            if (menu.innerText.includes('Workflows')) {
                loadWorkflows();
            }
        });
    });
    
    // Bind close transition
    const transCloseBtn = document.querySelector('#modal-transition .btn-close');
    if(transCloseBtn) {
        transCloseBtn.onclick = cancelTransition;
    }
});

// --- BPMN Drag & Drop ---
let dragType = null;

document.addEventListener('DOMContentLoaded', () => {
    const items = document.querySelectorAll('.bpmn-drag-item');
    items.forEach(item => {
        item.addEventListener('dragstart', (e) => {
            dragType = item.getAttribute('data-type');
            e.dataTransfer.setData('text/plain', dragType);
        });
        item.addEventListener('click', () => {
            const canvas = document.getElementById('drawflow');
            const rect = canvas.getBoundingClientRect();
            createNodeAt(item.getAttribute('data-type'), rect.left + rect.width / 2, rect.top + rect.height / 2);
        });
    });
});

function allowDrop(ev) {
    ev.preventDefault();
}

async function drop(ev) {
    ev.preventDefault();
    if(!dragType || !currentWorkflowId) return;
    
    await createNodeAt(dragType, ev.clientX, ev.clientY);
    dragType = null;
}

async function createNodeAt(type, clientX, clientY) {
    if (!type || !currentWorkflowId) return;

    // Calculate drop position relative to drawflow container
    const rect = document.getElementById('drawflow').getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    
    // Zoom and pan adjustments (Drawflow specific)
    const posX = Math.max(20, Math.round(x / Math.max(editor.zoom, 0.1)));
    const posY = Math.max(20, Math.round(y / Math.max(editor.zoom, 0.1)));
    
    // Defaults based on type
    let label = 'Nova Tarefa';
    let is_initial = false;
    let is_completion = false;
    
    if(type === 'event_start') { label = 'Início'; is_initial = true; }
    if(type === 'event_end') { label = 'Fim'; is_completion = true; }
    if(type === 'event_message') { label = 'Recebe Mensagem'; }
    if(type === 'gateway_exclusive') { label = 'Decisão Exclusiva'; }
    if(type === 'gateway_parallel') { label = 'Divisão Paralela'; }
    if(type === 'task_service') { label = 'Serviço Automático'; }
    
    try {
        const resp = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/states`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                label, 
                is_initial, 
                is_completion, 
                ui_pos_x: Math.round(posX), 
                ui_pos_y: Math.round(posY),
                node_type: type
            })
        });
        
        if(resp.ok) {
            const newState = await resp.json();
            if(!currentWorkflowData.states) currentWorkflowData.states = [];
            currentWorkflowData.states.push(newState);
            isRendering = true;
            renderSingleNode(newState, Object.keys(nodeStateMap).length);
            isRendering = false;
        } else {
            const error = await resp.json().catch(() => ({}));
            alert(`Erro ao criar nó BPMN: ${error.detail || `HTTP ${resp.status}`}`);
        }
    } catch(e) { console.error(e); }
    
}
