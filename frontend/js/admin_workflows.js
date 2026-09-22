// JS para gestão de Workflows (Inspirado no Mayan EDMS / Alfresco)
const WORKFLOWS_API = `${API_URL}/workflows`;
let currentWorkflowId = null;
let currentWorkflowData = null;
let editor = null;
let workflowDirty = false;

function setWorkflowDirty(dirty = true) {
    workflowDirty = dirty;
    const indicator = document.getElementById('workflow-dirty-indicator');
    if (!indicator) return;
    indicator.hidden = !dirty;
    indicator.textContent = dirty ? 'Há alterações não salvas' : 'Nenhuma alteração pendente';
}

function applyPoolLayout(states, transitions) {
    const levels = new Map();
    const initial = states.find(state => state.is_initial) || states[0];
    if (initial) {
        levels.set(initial.id, 0);
        const queue = [initial.id];
        while (queue.length) {
            const origin = queue.shift();
            const nextLevel = (levels.get(origin) || 0) + 1;
            transitions
                .filter(transition => transition.origin_state_id === origin)
                .forEach(transition => {
                    if (!levels.has(transition.destination_state_id)
                        || levels.get(transition.destination_state_id) > nextLevel) {
                        levels.set(transition.destination_state_id, nextLevel);
                        queue.push(transition.destination_state_id);
                    }
                });
        }
    }

    const poolOrder = [];
    states.forEach(state => {
        const poolName = getPoolData(state).poolName;
        if (!poolOrder.includes(poolName)) poolOrder.push(poolName);
    });

    const grouped = new Map(poolOrder.map(poolName => [poolName, []]));
    states.forEach((state, index) => {
        grouped.get(getPoolData(state).poolName).push({ state, index });
    });

    grouped.forEach((items, poolName) => {
        items.sort((left, right) =>
            (levels.get(left.state.id) ?? 999) - (levels.get(right.state.id) ?? 999)
            || left.index - right.index
        );
        const rowIndex = poolOrder.indexOf(poolName);
        items.forEach(({ state }, columnIndex) => {
            state.ui_pos_x = 90 + columnIndex * 235;
            state.ui_pos_y = 90 + rowIndex * 235;
        });
    });
}

function resetWorkflowDirty() {
    setWorkflowDirty(false);
}

function confirmWorkflowLeave(message = 'Há alterações não salvas neste workflow. Deseja sair sem salvar?') {
    if (!workflowDirty) return true;
    const shouldLeave = window.confirm(message);
    if (shouldLeave) {
        resetWorkflowDirty();
    }
    return shouldLeave;
}

function ensureWorkflowCanvasVisible() {
    const canvas = document.getElementById('drawflow');
    const panel = document.querySelector('.workflow-canvas-panel');
    if (!canvas) return;

    canvas.style.width = '100%';
    canvas.style.height = 'calc(100vh - 260px)';
    canvas.style.minHeight = '620px';
    if (panel) {
        panel.style.width = '100%';
        panel.style.height = '100%';
        panel.style.minHeight = '620px';
    }
}

function toggleWorkflowListPanel(forceState) {
    const panel = document.querySelector('.workflow-list-panel');
    const showListButton = document.getElementById('btn-show-workflow-list');
    if (!panel) return;

    const nextHidden = typeof forceState === 'boolean' ? forceState : !panel.classList.contains('is-hidden');
    panel.classList.toggle('is-hidden', nextHidden);
    panel.classList.remove('is-collapsed');
    panel.style.display = nextHidden ? 'none' : 'flex';
    panel.style.width = nextHidden ? '0' : '300px';
    panel.style.height = nextHidden ? '0' : 'auto';
    panel.style.opacity = nextHidden ? '0' : '1';
    panel.style.overflow = nextHidden ? 'hidden' : 'visible';
    panel.style.flex = nextHidden ? '0 0 0' : '0 0 300px';

    const btn = panel.querySelector('.workflow-list-collapse');
    if (btn) {
        btn.textContent = nextHidden ? '☰' : '⟨';
        btn.setAttribute('title', nextHidden ? 'Mostrar lista' : 'Ocultar lista');
    }
    if (showListButton) {
        showListButton.style.display = nextHidden ? 'inline-flex' : 'none';
    }
    ensureWorkflowCanvasVisible();
}

function toggleWorkflowFullscreen() {
    const body = document.body;
    const isFullscreen = body.classList.toggle('workflow-editor-fullscreen');
    const button = document.getElementById('btn-toggle-fullscreen');
    if (button) {
        button.textContent = isFullscreen ? 'Sair da tela cheia' : 'Tela cheia';
    }
    if (isFullscreen) {
        toggleWorkflowListPanel(true);
    }
}

window.addEventListener('beforeunload', (event) => {
    if (workflowDirty) {
        event.preventDefault();
        event.returnValue = '';
    }
});

window.addEventListener('resize', ensureWorkflowCanvasVisible);

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
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Nenhum workflow cadastrado.</td></tr>';
            return;
        }
        
        workflows.forEach(w => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            tr.innerHTML = `
                <td onclick="selectWorkflow('${w.id}')">${w.name}</td>
                <td onclick="selectWorkflow('${w.id}')"><span class="badge workflow-status-badge ${w.is_active ? 'is-active' : 'is-inactive'}">${w.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td>
                    <div class="workflow-row-actions">
                        <button class="icon-button" title="Editar em nova aba" aria-label="Editar em nova aba" onclick="editWorkflow('${w.id}'); event.stopPropagation();"><i class="fa-solid fa-pen"></i></button>
                        <button class="icon-button" title="${w.is_active ? 'Inativar' : 'Ativar'}" aria-label="${w.is_active ? 'Inativar' : 'Ativar'}" onclick="toggleWorkflowActive('${w.id}', ${!w.is_active}); event.stopPropagation();"><i class="fa-solid ${w.is_active ? 'fa-pause' : 'fa-play'}"></i></button>
                        <button class="icon-button" title="Ver versões" aria-label="Ver versões" onclick="openWorkflowVersions('${w.id}'); event.stopPropagation();"><i class="fa-solid fa-clock-rotate-left"></i></button>
                        <button class="icon-button danger" title="Excluir" aria-label="Excluir" onclick="deleteWorkflow('${w.id}'); event.stopPropagation();"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        const editorParam = new URLSearchParams(window.location.search).get('workflowEditor');
        if (editorParam && editorParam !== 'new') {
            const workflow = workflows.find(item => item.id === editorParam);
            if (workflow) selectWorkflow(workflow);
        }
    } catch (err) {
        console.error('Erro ao carregar workflows', err);
        const tbody = document.getElementById('table-workflows-body');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="3" style="text-align:center;color:#ef4444">Erro ao carregar: ${err.message}</td></tr>`;
        }
    }
}

function openWorkflowEditor(id = '') {
    const query = id ? `?workflowEditor=${encodeURIComponent(id)}` : '?workflowEditor=new';
    const editorWindow = window.open(`${window.location.pathname}${query}`, '_blank');
    if (!editorWindow) {
        alert('O navegador bloqueou a nova aba. Permita pop-ups para abrir o editor.');
    }
}

function selectWorkflow(idOrObj) {
    const workflow = typeof idOrObj === 'string' ? window.workflowsData.find(w => w.id === idOrObj) : idOrObj;
    if (!workflow) return;

    if (workflowDirty && currentWorkflowId && currentWorkflowId !== workflow.id && !confirmWorkflowLeave()) {
        return;
    }

    currentWorkflowId = workflow.id;
    currentWorkflowData = workflow;
    const editorColumn = document.getElementById('workflow-editor-column');
    if (editorColumn) editorColumn.classList.remove('workflow-editor-column-hidden');
    toggleWorkflowListPanel(true);
    ensureWorkflowCanvasVisible();
    resetWorkflowDirty();
    document.getElementById('current-workflow-name').innerText = workflow.name;
    document.getElementById('btn-add-state').disabled = false;
    document.getElementById('btn-organize-workflow').disabled = false;
    document.getElementById('btn-export-workflow').disabled = false;
    document.getElementById('btn-publish-workflow').disabled = false;
    document.getElementById('btn-versions-workflow').disabled = false;
    document.getElementById('bpmn-toolbox').style.display = 'flex';
    document.getElementById('editor-hint').innerText = 'Arraste ou clique em um elemento do painel superior para criar um nó';
    
    initDrawflow();
    renderDrawflow(workflow.states || [], workflow.transitions || []);
}

function installOrthogonalConnectionRenderer(instance) {
    if (!instance || instance.__orthogonalRendererInstalled) return;
    instance.__orthogonalRendererInstalled = true;

    instance.createCurvature = function(startX, startY, endX, endY, curvature = 0, type = 'openclose') {
        if (!Number.isFinite(startX) || !Number.isFinite(startY) || !Number.isFinite(endX) || !Number.isFinite(endY)) {
            return 'M 0 0';
        }

        const deltaX = endX - startX;
        const deltaY = endY - startY;
        const dxAbs = Math.abs(deltaX);
        const dyAbs = Math.abs(deltaY);

        if (dxAbs < 1 && dyAbs < 1) {
            return `M ${startX} ${startY} L ${endX} ${endY}`;
        }

        const useHorizontal = dxAbs >= dyAbs;
        const bend = Math.max(70, Math.min(useHorizontal ? dxAbs * 0.5 : dyAbs * 0.5, 240));

        if (useHorizontal) {
            const straightX = startX + Math.sign(deltaX || 1) * bend;
            return `M ${startX} ${startY} L ${straightX} ${startY} L ${straightX} ${endY} L ${endX} ${endY}`;
        }

        const straightY = startY + Math.sign(deltaY || 1) * bend;
        return `M ${startX} ${startY} L ${startX} ${straightY} L ${endX} ${straightY} L ${endX} ${endY}`;
    };

    instance.updateConnection = function(outputX, outputY) {
        if (!this.ele_selected || !this.connection_ele) return;

        const path = this.connection_ele.querySelector('.main-path') || this.connection_ele.children[0];
        if (!path) return;

        const canvasRect = this.precanvas.getBoundingClientRect();
        const nodeRect = this.ele_selected.getBoundingClientRect();
        const zoom = this.zoom || 1;
        const scaleX = this.precanvas.clientWidth / (this.precanvas.clientWidth * zoom);
        const scaleY = this.precanvas.clientHeight / (this.precanvas.clientHeight * zoom);

        const startX = this.ele_selected.offsetWidth / 2 + (nodeRect.x - canvasRect.x) * scaleX;
        const startY = this.ele_selected.offsetHeight / 2 + (nodeRect.y - canvasRect.y) * scaleY;
        const endX = outputX * (this.precanvas.clientWidth / (this.precanvas.clientWidth * zoom)) - canvasRect.x * (this.precanvas.clientWidth / (this.precanvas.clientWidth * zoom));
        const endY = outputY * (this.precanvas.clientHeight / (this.precanvas.clientHeight * zoom)) - canvasRect.y * (this.precanvas.clientHeight / (this.precanvas.clientHeight * zoom));

        path.setAttributeNS(null, 'd', this.createCurvature(startX, startY, endX, endY, this.curvature || 0, 'openclose'));
    };
}

function initDrawflow() {
    if (editor) return;
    const container = document.getElementById("drawflow");
    ensureWorkflowCanvasVisible();
    editor = new Drawflow(container);
    installOrthogonalConnectionRenderer(editor);
    editor.reroute = false;
    editor.curvature = 0;
    editor.reroute_curvature = 0;
    editor.reroute_fix_curvature = false;
    editor.draggable_inputs = false;
    editor.draggable_links = false;
    editor.start();
    
    // Events
    editor.on('nodeMoved', async (id) => {
        if(isRendering) return;
        setWorkflowDirty(true);
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
            resetWorkflowDirty();

            editor.on('nodeSelected', (id) => {
                if (isRendering) return;
                const stateId = nodeStateMap_inv[id];
                if (stateId) openStateEditor(stateId);
            });
        } catch(e) { console.error(e); }
    });
    
    editor.on('connectionCreated', (info) => {
        if(isRendering) return; // ignore events during render
        setWorkflowDirty(true);
        const originNode = editor.getNodeFromId(info.output_id);
        const destNode = editor.getNodeFromId(info.input_id);
        openTransitionVisualModal(originNode.data.stateId, destNode.data.stateId);
    });
    
    editor.on('connectionRemoved', async (info) => {
        if(isRendering) return;
        setWorkflowDirty(true);
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
                    resetWorkflowDirty();
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
        setWorkflowDirty(true);
        const stateId = nodeStateMap_inv[id];
        if(!stateId) return;
        
        try {
            const resp = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/states/${stateId}`, {
                method: 'DELETE',
                headers: getAuthHeaders()
            });
            if(resp.ok) {
                resetWorkflowDirty();
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

function getPoolData(state) {
    const config = state && state.config ? state.config : {};
    const poolName = config.pool || config.pool_name || 'Geral';
    const poolColor = config.color || '#cbd5e1';
    return { poolName, poolColor };
}

function renderWorkflowPools(states) {
    const canvas = document.getElementById('drawflow');
    if (!canvas) return;
    canvas.querySelectorAll('.workflow-pool-lane').forEach(node => node.remove());

    const pools = [...new Map(states.map(state => {
        const { poolName, poolColor } = getPoolData(state);
        return [poolName, { poolName, poolColor, states: [] }];
    })).values()];

    states.forEach(state => {
        const { poolName } = getPoolData(state);
        const pool = pools.find(item => item.poolName === poolName);
        if (pool) pool.states.push(state);
    });

    const poolRows = pools
        .map(({ poolName, poolColor, states: poolStates }) => {
            if (!poolStates.length) return null;
            const yValues = poolStates.map(state => Number(state.ui_pos_y) || 80);
            const minY = Math.min(...yValues) - 150;
            const maxY = Math.max(...yValues) + 150;
            return { poolName, poolColor, minY, maxY, height: Math.max(180, maxY - minY) };
        })
        .filter(Boolean)
        .sort((a, b) => a.minY - b.minY);

    let runningTop = 20;
    poolRows.forEach(({ poolName, poolColor, height }) => {
        const lane = document.createElement('div');
        lane.className = 'workflow-pool-lane';
        lane.style.left = '8px';
        lane.style.top = `${Math.max(20, runningTop)}px`;
        lane.style.width = 'calc(100% - 16px)';
        lane.style.height = `${Math.max(180, height)}px`;
        lane.style.borderColor = poolColor;
        lane.style.background = `${poolColor}18`;

        const label = document.createElement('div');
        label.className = 'workflow-pool-label';
        label.textContent = poolName;
        label.style.background = poolColor;
        label.style.borderColor = poolColor;
        label.style.top = '12px';
        label.style.left = '18px';
        lane.appendChild(label);
        canvas.appendChild(lane);

        runningTop += Math.max(180, height) + 26;
    });
}

function renderSingleNode(s, fallbackIndex = 0) {
    let nType = s.node_type || 'task_user';
    let html_content = '';
    const poolInfo = getPoolData(s);
    const workflowIcon = (body, color) => `
        <svg viewBox="0 0 32 32" style="width:30px;height:30px;color:${color};fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;">
            ${body}
        </svg>`;
    
    if (nType.startsWith('event_')) {
        let color = '#3b82f6';
        let icon = '<path d="M8 5l10 7-10 7z" fill="currentColor" stroke="none"></path>';
        if(nType === 'event_start') { color = '#16a34a'; icon = '<path d="M8 5l10 7-10 7z" fill="currentColor" stroke="none"></path>'; }
        if(nType === 'event_end') { color = '#dc2626'; icon = '<rect x="7" y="7" width="10" height="10" rx="1" fill="currentColor" stroke="none"></rect>'; }
        if(nType === 'event_message') { icon = '<path d="M4 6h16v12H4z"></path><path d="m4 7 8 6 8-6"></path>'; }
        
        html_content = `
        <div style="display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:4px;">
            <span style="display:inline-block; min-width:14px; height:14px; border-radius:50%; background:${poolInfo.poolColor}; border:2px solid rgba(15,23,42,.2);"></span>
            <small style="font-size:10px; color:#475569; font-weight:700;">${poolInfo.poolName}</small>
        </div>
        <div class="workflow-node-icon-anchor" style="border-radius:50%; width:64px; height:64px; border:4px solid ${color}; display:flex; align-items:center; justify-content:center; background:#fff; flex-direction:column; margin:0 auto; user-select:none; pointer-events:none; box-shadow:0 3px 8px rgba(15,23,42,.16);">
            ${workflowIcon(icon, color)}
        </div>
        <div style="text-align:center; font-size:10px; margin-top:5px; color:#333; user-select:none;"><strong>${s.label}</strong></div>`;
    } else if (nType.startsWith('gateway_')) {
        let icon = nType === 'gateway_exclusive'
            ? '<path d="M7 7l10 10M17 7 7 17"></path>'
            : '<path d="M12 6v12M6 12h12"></path>';
        html_content = `
        <div style="display:flex; align-items:center; justify-content:center; gap:6px; margin-bottom:4px;">
            <span style="display:inline-block; min-width:14px; height:14px; border-radius:50%; background:${poolInfo.poolColor}; border:2px solid rgba(15,23,42,.2);"></span>
            <small style="font-size:10px; color:#475569; font-weight:700;">${poolInfo.poolName}</small>
        </div>
        <div class="workflow-node-icon-anchor" style="width:58px; height:58px; border:3px solid #eab308; background:#fef3c7; transform: rotate(45deg); display:flex; align-items:center; justify-content:center; margin:10px auto; user-select:none; pointer-events:none; box-shadow:0 3px 8px rgba(15,23,42,.14);">
            <span style="transform:rotate(-45deg);">${workflowIcon(icon, '#ca8a04')}</span>
        </div>
        <div style="text-align:center; font-size:10px; margin-top:15px; color:#333; user-select:none;"><strong>${s.label}</strong></div>`;
    } else {
        let icon = '<circle cx="10" cy="9" r="4"></circle><path d="M3 25c1-5 3-7 7-7s6 2 7 7"></path><path d="m19 21 3 3 6-7"></path>';
        let color = '#2563eb';
        if(nType === 'task_service') {
            icon = '<circle cx="11" cy="16" r="6"></circle><path d="M11 6v4M11 22v4M1 16h4M17 16h4M4 9l3 3M15 20l3 3M18 9l-3 3M7 20l-3 3"></path><circle cx="11" cy="16" r="2"></circle>';
            color = '#0f766e';
        }
        if(nType === 'task_script') {
            icon = '<path d="M5 5h22v22H5z"></path><path d="m10 12-4 4 4 4M22 12l4 4-4 4M18 9l-4 14"></path>';
            color = '#7c3aed';
        }
        if ((s.config || {}).action_code === 'SEND_EMAIL') {
            icon = '<rect x="3" y="7" width="26" height="18" rx="2"></rect><path d="m4 9 12 9L28 9"></path>';
            color = '#dc2626';
        }
        if ((s.config || {}).action_code === 'REQUEST_SIGNATURE') {
            icon = '<path d="M6 4h15l5 5v19H6z"></path><path d="M21 4v6h5M10 20h10M10 15h7"></path><path d="m20 25 3-3 3 3"></path>';
            color = '#b91c1c';
        }
        
        html_content = `
        <div class="workflow-task-card" style="border:2px solid ${color}; border-radius:10px; background:#fff; min-width:170px; max-width:210px; padding:11px; box-shadow:0 3px 9px rgba(15,23,42,.14); user-select:none;">
            <div style="display:flex; align-items:center; margin-bottom:5px; pointer-events:none;">
                <span class="workflow-node-icon-anchor" style="display:inline-flex; margin-right:6px;">${workflowIcon(icon, color)}</span>
                <strong style="font-size:11px; color:${color};">${nType === 'task_user' ? 'Tarefa de usuário' : (nType === 'task_service' ? 'Serviço automático' : 'Script')}</strong>
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
    
    const nodeId = editor.addNode('state', in_con, out_con, posX, posY, `state state-${nType}`, { stateId: s.id }, html_content);
    nodeStateMap[s.id] = nodeId;
    nodeStateMap_inv[nodeId] = s.id;
}

function renderDrawflow(states, transitions) {
    if(!editor) return;
    ensureWorkflowCanvasVisible();
    isRendering = true;
    applyPoolLayout(states, transitions);
    editor.clear();
    editor.clearModuleSelected();
    nodeStateMap = {};
    nodeStateMap_inv = {};
    renderWorkflowPools(states);

    states.forEach((s, index) => {
        renderSingleNode(s, index);
    });

    transitions.forEach(t => {
        const originNodeId = nodeStateMap[t.origin_state_id];
        const destNodeId = nodeStateMap[t.destination_state_id];
        if(originNodeId && destNodeId) {
            editor.addConnection(originNodeId, destNodeId, 'output_1', 'input_1');
        }

    });

    isRendering = false;
}

function organizeCurrentWorkflow() {
    if (!currentWorkflowData || !currentWorkflowData.states) return;
    const states = currentWorkflowData.states;
    const transitions = currentWorkflowData.transitions || [];
    const initial = states.find(state => state.is_initial) || states[0];
    if (!initial) return;

    const levels = new Map([[initial.id, 0]]);
    const queue = [initial.id];
    while (queue.length) {
        const origin = queue.shift();
        const next = transitions
            .filter(transition => transition.origin_state_id === origin)
            .map(transition => transition.destination_state_id);
        next.forEach(destination => {
            if (!levels.has(destination)) {
                levels.set(destination, levels.get(origin) + 1);
                queue.push(destination);
            }
        });
    }

    const columns = new Map();
    states.forEach((state, index) => {
        const level = levels.has(state.id) ? levels.get(state.id) : Math.floor(index / 2);
        if (!columns.has(level)) columns.set(level, []);
        columns.get(level).push(state);
    });

    const updates = [];
    [...columns.entries()].sort((a, b) => a[0] - b[0]).forEach(([level, column]) => {
        column.forEach((state, index) => {
            state.ui_pos_x = 60 + level * 235;
            state.ui_pos_y = 90 + index * 150;
            updates.push(fetch(`${WORKFLOWS_API}/${currentWorkflowId}/states/${state.id}`, {
                method: 'PUT',
                headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ ui_pos_x: state.ui_pos_x, ui_pos_y: state.ui_pos_y })
            }));
        });
    });

    Promise.all(updates).then(() => renderDrawflow(states, transitions))
        .catch(error => {
            console.error('Erro ao organizar workflow', error);
            alert('Não foi possível salvar a organização do fluxo.');
        });
}

function openWorkflowModal() {
    if (!confirmWorkflowLeave('Há alterações não salvas no workflow atual. Deseja continuar e criar um novo workflow?')) {
        return;
    }
    document.getElementById('wf-id').value = '';
    document.getElementById('wf-name').value = '';
    document.getElementById('wf-internal').value = '';
    document.getElementById('wf-active').checked = true;
    document.getElementById('workflow-modal-title').textContent = 'Novo Workflow';
    document.getElementById('modal-workflow').classList.add('active');
}

async function exportCurrentWorkflow() {
    if (!currentWorkflowId) return;
    const response = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/export`, { headers: getAuthHeaders() });
    if (!response.ok) {
        alert('Não foi possível baixar o workflow.');
        return;
    }
    const blob = await response.blob();
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${currentWorkflowData.internal_name || 'workflow'}.json`;
    link.click();
    URL.revokeObjectURL(link.href);
}

async function importWorkflowFile(file) {
    if (!file) return;
    const form = new FormData();
    form.append('file', file);
    const response = await fetch(`${WORKFLOWS_API}/import`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: form
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        alert(error.detail || 'Não foi possível importar o workflow.');
        return;
    }
    document.getElementById('workflow-import-file').value = '';
    await loadWorkflows();
    alert('Workflow importado como rascunho. Selecione-o e publique a versão quando estiver pronto.');
}

async function publishCurrentWorkflow() {
    if (!currentWorkflowId) return;
    if (!confirm('Publicar a configuração atual como uma nova versão?')) return;
    const response = await fetch(`${WORKFLOWS_API}/${currentWorkflowId}/versions/publish`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        alert(error.detail || 'Não foi possível publicar a versão.');
        return;
    }
    await loadWorkflows();
    alert('Nova versão publicada. As versões anteriores foram preservadas.');
}

async function restoreWorkflowVersion() {
    if (!currentWorkflowId) return;
    return openWorkflowVersions(currentWorkflowId);
}

async function openWorkflowVersions(workflowId) {
    const workflow = (window.workflowsData || []).find(item => item.id === workflowId);
    const list = document.getElementById('workflow-versions-list');
    if (!list) return;
    document.getElementById('modal-workflow-versions').classList.add('active');
    list.innerHTML = '<p class="workflow-empty-state">Carregando versões...</p>';
    const response = await fetch(`${WORKFLOWS_API}/${workflowId}/versions`, { headers: getAuthHeaders() });
    if (!response.ok) {
        list.innerHTML = '<p class="workflow-empty-state error">Não foi possível consultar as versões.</p>';
        return;
    }
    const versions = await response.json();
    if (!versions.length) {
        list.innerHTML = '<p class="workflow-empty-state">Este workflow ainda não possui versões publicadas.</p>';
        return;
    }
    list.innerHTML = versions.map(version => `
        <div class="workflow-version-row">
            <div>
                <strong>Versão ${version.version_number}</strong>
                <span>${version.status === 'PUBLISHED' ? 'Publicada' : 'Arquivada'} · ${version.published_at ? new Date(version.published_at).toLocaleString('pt-BR') : 'sem data'}</span>
            </div>
            <button class="btn-secondary btn-small" onclick="restoreWorkflowVersionNumber('${workflowId}', ${version.version_number})"><i class="fa-solid fa-rotate-left"></i> Restaurar</button>
        </div>
    `).join('');
}

function closeWorkflowVersions() {
    document.getElementById('modal-workflow-versions')?.classList.remove('active');
}

async function restoreWorkflowVersionNumber(workflowId, versionNumber) {
    if (!confirm(`Restaurar a versão ${versionNumber} e publicar como uma nova versão?`)) return;
    const restoreResponse = await fetch(`${WORKFLOWS_API}/${workflowId}/versions/${versionNumber}/restore`, {
        method: 'POST',
        headers: getAuthHeaders()
    });
    if (!restoreResponse.ok) {
        const error = await restoreResponse.json().catch(() => ({}));
        alert(error.detail || 'Não foi possível restaurar a versão.');
        return;
    }
    closeWorkflowVersions();
    await loadWorkflows();
    const updated = window.workflowsData.find(item => item.id === workflowId);
    if (updated && currentWorkflowId === workflowId) selectWorkflow(updated);
    alert('Versão restaurada e publicada como uma nova versão.');
}

async function saveWorkflow() {
    const wfId = document.getElementById('wf-id').value;
    const payload = {
        name: document.getElementById('wf-name').value,
        internal_name: document.getElementById('wf-internal').value,
        is_active: document.getElementById('wf-active').checked
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
            resetWorkflowDirty();
            const saved = await resp.json();
            currentWorkflowId = saved.id;
            currentWorkflowData = saved;
            await loadWorkflows();
            if (new URLSearchParams(window.location.search).get('workflowEditor')) {
                selectWorkflow(saved);
            }
        } else {
            const err = await resp.json().catch(() => ({}));
            alert("Erro ao salvar: " + (err.detail || `HTTP ${resp.status}`));
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

function editWorkflow(idOrObj) {
    const wkf = typeof idOrObj === 'string' ? window.workflowsData.find(w => w.id === idOrObj) : idOrObj;
    if (!wkf) return;
    openWorkflowEditor(wkf.id);
}

async function toggleWorkflowActive(id, isActive) {
    const workflow = (window.workflowsData || []).find(item => item.id === id);
    if (!workflow) return;
    const response = await fetch(`${WORKFLOWS_API}/${id}`, {
        method: 'PUT',
        headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: workflow.name, internal_name: workflow.internal_name, is_active: isActive })
    });
    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        alert(error.detail || 'Não foi possível alterar o status do workflow.');
        return;
    }
    await loadWorkflows();
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
                document.getElementById('btn-organize-workflow').disabled = true;
                document.getElementById('btn-export-workflow').disabled = true;
                document.getElementById('btn-publish-workflow').disabled = true;
                document.getElementById('btn-versions-workflow').disabled = true;
                const showListButton = document.getElementById('btn-show-workflow-list');
                if (showListButton) showListButton.style.display = 'none';
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
    document.getElementById('state-id').value = '';
    document.getElementById('state-modal-title').textContent = 'Novo Estado';
    document.getElementById('state-label').value = '';
    document.getElementById('state-initial').checked = false;
    document.getElementById('state-completion').checked = false;
    document.getElementById('state-action-code').value = '';
    document.getElementById('state-recipients').value = '';
    document.getElementById('state-execution-details').value = '';
    document.getElementById('modal-state').classList.add('active');
}

async function openStateEditor(stateId) {
    const state = (currentWorkflowData.states || []).find(item => item.id === stateId);
    if (!state) return;
    document.getElementById('state-id').value = state.id;
    document.getElementById('state-modal-title').textContent = 'Editar elemento';
    document.getElementById('state-label').value = state.label || '';
    document.getElementById('state-initial').checked = Boolean(state.is_initial);
    document.getElementById('state-completion').checked = Boolean(state.is_completion);
    const config = state.config || {};
    document.getElementById('state-action-code').value = config.action_code || '';
    document.getElementById('state-recipients').value = config.recipients || '';
    document.getElementById('state-execution-details').value = config.execution_details || '';
    document.getElementById('modal-state').classList.add('active');
}

async function saveState() {
    const stateId = document.getElementById('state-id').value;
    const label = document.getElementById('state-label').value;
    const is_initial = document.getElementById('state-initial').checked;
    const is_completion = document.getElementById('state-completion').checked;
    const config = {
        action_code: document.getElementById('state-action-code').value.trim() || null,
        recipients: document.getElementById('state-recipients').value.trim() || null,
        execution_details: document.getElementById('state-execution-details').value.trim() || null
    };
    
    try {
        const resp = await fetch(stateId
            ? `${WORKFLOWS_API}/${currentWorkflowId}/states/${stateId}`
            : `${WORKFLOWS_API}/${currentWorkflowId}/states`, {
            method: stateId ? 'PUT' : 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ label, is_initial, is_completion, ui_pos_x: 100, ui_pos_y: 100, config })
        });
        
        if(resp.ok) {
            document.getElementById('modal-state').classList.remove('active');
            resetWorkflowDirty();
            
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
            resetWorkflowDirty();
            
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
    const editorParam = new URLSearchParams(window.location.search).get('workflowEditor');
    if (editorParam) {
        document.body.classList.add('workflow-editor-fullscreen');
        document.getElementById('workflow-editor-column')?.classList.remove('workflow-editor-column-hidden');
        toggleWorkflowListPanel(true);
        if (editorParam === 'new') {
            openWorkflowModal();
        }
    }

    // Escutar se o menu Templates foi clicado para carregar dados
    const menus = document.querySelectorAll('.sidebar-nav li, .menu-item');
    menus.forEach(menu => {
        menu.addEventListener('click', (event) => {
            const target = menu.getAttribute('data-target');
            if (menu.innerText.includes('Workflows') && target !== 'workflows') {
                loadWorkflows();
            }

            if (workflowDirty && currentWorkflowId && target !== 'workflows') {
                event.preventDefault();
                event.stopPropagation();
                const shouldLeave = window.confirm('Há alterações não salvas no workflow. Deseja sair sem salvar?');
                if (!shouldLeave) return;
                resetWorkflowDirty();
                menu.click();
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
