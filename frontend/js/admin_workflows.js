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
    panel.style.display = nextHidden ? 'none' : '';
    panel.style.width = nextHidden ? '0' : '';
    panel.style.height = nextHidden ? '0' : '';
    panel.style.opacity = nextHidden ? '0' : '';
    panel.style.overflow = nextHidden ? 'hidden' : '';
    panel.style.flex = nextHidden ? '0 0 0' : '';

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
                    <div class="workflow-row-actions" style="display: flex; gap: 5px; flex-wrap: wrap;">
                        <button class="icon-button" style="padding: 4px 8px; font-size: 0.85em; width: auto; height: auto;" title="Editar em nova aba" aria-label="Editar em nova aba" onclick="editWorkflow('${w.id}'); event.stopPropagation();"><i class="fa-solid fa-pen"></i> Editar</button>
                        <button class="icon-button" style="padding: 4px 8px; font-size: 0.85em; width: auto; height: auto;" title="${w.is_active ? 'Inativar' : 'Ativar'}" aria-label="${w.is_active ? 'Inativar' : 'Ativar'}" onclick="toggleWorkflowActive('${w.id}', ${!w.is_active}); event.stopPropagation();"><i class="fa-solid ${w.is_active ? 'fa-pause' : 'fa-play'}"></i> ${w.is_active ? 'Inativar' : 'Ativar'}</button>
                        <button class="icon-button" style="padding: 4px 8px; font-size: 0.85em; width: auto; height: auto;" title="Ver versões" aria-label="Ver versões" onclick="openWorkflowVersions('${w.id}'); event.stopPropagation();"><i class="fa-solid fa-clock-rotate-left"></i> Versões</button>
                        <button class="icon-button danger" style="padding: 4px 8px; font-size: 0.85em; width: auto; height: auto;" title="Excluir" aria-label="Excluir" onclick="deleteWorkflow('${w.id}'); event.stopPropagation();"><i class="fa-solid fa-trash"></i> Excluir</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        const editorParam = new URLSearchParams(window.location.search).get('workflowEditor');
        if (editorParam && editorParam !== 'new') {
            const workflow = workflows.find(item => item.id === editorParam);
            if (workflow) selectWorkflow(workflow);
        } else if (!currentWorkflowId && workflows.length > 0) {
            selectWorkflow(workflows[0]);
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
    ['btn-add-state', 'btn-organize-workflow', 'btn-export-workflow', 'btn-publish-workflow', 'btn-versions-workflow'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.disabled = false;
    });
    const bpmnToolbox = document.getElementById('bpmn-toolbox');
    if (bpmnToolbox) bpmnToolbox.style.display = 'flex';
    const editorHint = document.getElementById('editor-hint');
    if (editorHint) editorHint.innerText = 'Arraste ou clique em um elemento do painel superior para criar um nó';
    
    initDrawflow();
    const states = workflow.states || [];
    const transitions = workflow.transitions || [];
    renderDrawflow(states, transitions);
    // Auto-organize layout ONLY if no states have any positions at all
    const hasAnyCustomPositions = states.some(s => s.ui_pos_x && s.ui_pos_x > 0);
    if (!hasAnyCustomPositions && states.length > 0) {
        setTimeout(() => organizeCurrentWorkflow(), 300);
    }
}

function ensureArrowheadMarkers(container) {
    if (!container) return;
    let svgDefs = container.querySelector('svg defs');
    if (!svgDefs) {
        let svg = container.querySelector('svg');
        if (!svg) {
            svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.style.position = 'absolute';
            svg.style.width = '0';
            svg.style.height = '0';
            svg.style.pointerEvents = 'none';
            container.prepend(svg);
        }
        svgDefs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        svg.prepend(svgDefs);
    }
    if (!container.querySelector('#arrow-marker')) {
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'arrow-marker');
        marker.setAttribute('viewBox', '0 0 10 10');
        marker.setAttribute('refX', '8');
        marker.setAttribute('refY', '5');
        marker.setAttribute('markerWidth', '6');
        marker.setAttribute('markerHeight', '6');
        marker.setAttribute('orient', 'auto-start-reverse');
        marker.innerHTML = '<path d="M 0 1 L 9 5 L 0 9 z" fill="#2563eb" />';
        svgDefs.appendChild(marker);
    }
    if (!container.querySelector('#arrow-marker-hover')) {
        const markerHover = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        markerHover.setAttribute('id', 'arrow-marker-hover');
        markerHover.setAttribute('viewBox', '0 0 10 10');
        markerHover.setAttribute('refX', '8');
        markerHover.setAttribute('refY', '5');
        markerHover.setAttribute('markerWidth', '7');
        markerHover.setAttribute('markerHeight', '7');
        markerHover.setAttribute('orient', 'auto-start-reverse');
        markerHover.innerHTML = '<path d="M 0 1 L 9 5 L 0 9 z" fill="#1d4ed8" />';
        svgDefs.appendChild(markerHover);
    }
}

function installOrthogonalConnectionRenderer(instance) {
    if (!instance || instance.__orthogonalRendererInstalled) return;
    instance.__orthogonalRendererInstalled = true;

    // Customiza o cálculo de conexões do Drawflow para gerar rotas ortogonais inteligentes
    instance.createCurvature = function(start_pos_x, start_pos_y, end_pos_x, end_pos_y, curvature_value, type) {
        let x1 = Math.round(start_pos_x);
        let y1 = Math.round(start_pos_y);
        let x2 = Math.round(end_pos_x);
        let y2 = Math.round(end_pos_y);

        const dx = x2 - x1;
        const dy = y2 - y1;
        const absDy = Math.abs(dy);

        // 1. Linha praticamente reta horizontal ou vertical (I)
        if (absDy < 4) {
            return ` M ${x1} ${y1} L ${x2} ${y2}`;
        }
        if (Math.abs(dx) < 4) {
            return ` M ${x1} ${y1} L ${x2} ${y2}`;
        }

        // 2. Destino à frente (fluxo natural para a direita com desnível vertical)
        if (dx >= 40) {
            const midX = Math.round((x1 + x2) / 2);
            return ` M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`;
        }

        // 3. Conexão para nós abaixo ou acima (mesma coluna ou voltando para trás)
        // Dá uma pequena folga lateral à direita do nó de origem (ex: 24px) para não cortar o card,
        // desce/sobe verticalmente até o nível desejado ou um canal desobstruído, e entra no destino.
        const exitMargin = 22;
        const entryMargin = 22;
        const channelX = Math.max(x1 + exitMargin, x2 + exitMargin);
        const midY = y1 + Math.round(dy / 2);

        if (x2 <= x1) {
            // Volta para a esquerda ou nó abaixo na mesma coluna
            return ` M ${x1} ${y1} L ${x1 + exitMargin} ${y1} L ${x1 + exitMargin} ${midY} L ${x2 - entryMargin} ${midY} L ${x2 - entryMargin} ${y2} L ${x2} ${y2}`;
        } else {
            // Destino levemente à frente mas com pouca folga lateral
            return ` M ${x1} ${y1} L ${channelX} ${y1} L ${channelX} ${y2} L ${x2} ${y2}`;
        }
    };
}

function initDrawflow() {
    if (editor) return;
    const container = document.getElementById("drawflow");
    ensureWorkflowCanvasVisible();
    editor = new Drawflow(container);
    installOrthogonalConnectionRenderer(editor);
    ensureArrowheadMarkers(container);
    editor.reroute = false;
    editor.curvature = 0;
    editor.reroute_curvature = 0;
    editor.draggable_inputs = false;
    editor.draggable_links = false;
    editor.start();
    
    // Events
    editor.on('nodeMoved', async (id) => {
        if(isRendering) return;
        const node = editor.getNodeFromId(id);
        if(!node || !node.data) return;
        const stateId = node.data.stateId;
        const posX = Math.round(node.pos_x);
        const posY = Math.round(node.pos_y);
        
        // Atualiza imediatamente na memória local para não resetar se alternar
        if (currentWorkflowData && currentWorkflowData.states) {
            const st = currentWorkflowData.states.find(s => s.id === stateId);
            if (st) {
                st.ui_pos_x = posX;
                st.ui_pos_y = posY;
            }
        }
        if (window.workflowsData) {
            const wf = window.workflowsData.find(w => w.id === currentWorkflowId);
            if (wf && wf.states) {
                const st = wf.states.find(s => s.id === stateId);
                if (st) {
                    st.ui_pos_x = posX;
                    st.ui_pos_y = posY;
                }
            }
        }

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
        } catch(e) {
            console.error('Erro ao salvar nova posição do nó:', e);
        }
    });

    // Abrir edição SOMENTE com DUPLO CLIQUE (dblclick)
    container.addEventListener('dblclick', (e) => {
        const nodeEl = e.target.closest('.drawflow-node');
        if (!nodeEl) return;
        const nodeIdStr = nodeEl.id.replace('node-', '');
        const stateId = nodeStateMap_inv[nodeIdStr];
        if (stateId) {
            openStateEditor(stateId);
        }
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
    let poolName = config.pool || config.pool_name || state.swimlane;
    let poolColor = config.color;

    // Se a raia não tiver sido configurada manualmente (está vazia ou 'Geral'), deduz de forma inteligente pelo tipo/ação
    if (!poolName || poolName === 'Geral') {
        const label = (state.label || '').toLowerCase();
        const action = ((config.action_code || '') + ' ' + (config.execution_details || '')).toLowerCase();
        const nType = state.node_type || '';

        if (nType === 'task_service' || nType === 'task_script' || action.includes('xml') || action.includes('gen_') || label.includes('gerar') || label.includes('geração') || label.includes('xml') || label.includes('automátic')) {
            poolName = 'Serviços Automáticos (XML / Geração)';
            if (!poolColor) poolColor = '#8b5cf6'; // Roxo
        } else if (action.includes('sign') || label.includes('assin') || label.includes('subscrit')) {
            poolName = 'Assinatura Digital';
            if (!poolColor) poolColor = '#f59e0b'; // Âmbar
        } else if (label.includes('valid') || label.includes('verific') || label.includes('confer') || label.includes('analis')) {
            poolName = 'Validação de Documentos';
            if (!poolColor) poolColor = '#10b981'; // Verde esmeralda
        } else if (label.includes('solicit') || label.includes('anex') || label.includes('document') || nType === 'task_user' || nType.startsWith('event')) {
            poolName = 'Interação do Usuário / Documentação';
            if (!poolColor) poolColor = '#3b82f6'; // Azul
        } else {
            poolName = 'Secretaria Geral';
            if (!poolColor) poolColor = '#64748b'; // Ardósia
        }
    }

    if (!poolColor) poolColor = '#3b82f6';
    return { poolName, poolColor };
}

function renderWorkflowPools(states) {
    const canvas = document.getElementById('drawflow');
    if (!canvas) return;
    const drawflowInner = canvas.querySelector('.drawflow') || canvas;
    drawflowInner.querySelectorAll('.workflow-pool-lane').forEach(node => node.remove());

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
            const xValues = poolStates.map(state => Number(state.ui_pos_x) || 80);
            const minY = Math.min(...yValues) - 35;
            const maxY = Math.max(...yValues) + 160;
            const maxX = Math.max(...xValues) + 380;
            return { poolName, poolColor, minY, maxY, maxX, height: Math.max(200, maxY - minY) };
        })
        .filter(Boolean)
        .sort((a, b) => a.minY - b.minY);

    const maxCanvasWidth = Math.max(1600, ...poolRows.map(r => r.maxX || 1600));

    poolRows.forEach(({ poolName, poolColor, minY, height }) => {
        const lane = document.createElement('div');
        lane.className = 'workflow-pool-lane';
        lane.style.left = '16px';
        lane.style.top = `${Math.max(20, minY)}px`;
        lane.style.width = `${maxCanvasWidth}px`;
        lane.style.height = `${height}px`;
        lane.style.borderColor = poolColor;
        lane.style.background = `${poolColor}14`;

        const label = document.createElement('div');
        label.className = 'workflow-pool-label';
        label.textContent = poolName;
        label.style.background = poolColor;
        label.style.borderColor = poolColor;
        label.style.top = '10px';
        label.style.left = '14px';
        lane.appendChild(label);
        drawflowInner.appendChild(lane);
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
        let icon = 'fa-regular fa-envelope';
        let typeLabel = 'EVENTO';
        
        if(nType === 'event_start') { color = '#10b981'; icon = 'fa-solid fa-play'; typeLabel = 'INÍCIO'; }
        if(nType === 'event_end') { color = '#ef4444'; icon = 'fa-solid fa-stop'; typeLabel = 'TÉRMINO'; }
        if(nType === 'event_message') { typeLabel = 'MENSAGEM'; }
        
        html_content = `
        <div class="node-modern type-event" style="min-width: 180px;">
            <div class="node-header" style="color: ${color};">
                <i class="${icon}"></i> ${typeLabel}
                ${s.is_initial ? '<span class="badge-status">Inicial</span>' : ''}
                ${s.is_completion ? '<span class="badge-status" style="background:#fef2f2;color:#dc2626;">Final</span>' : ''}
            </div>
            <div class="node-body">
                ${s.label}
            </div>
            <div class="node-footer">
                <span><span class="swimlane-label" style="font-weight:600;color:#0f172a;">${poolInfo.poolName}</span></span>
            </div>
        </div>`;
    } else if (nType.startsWith('gateway_')) {
        let icon = nType === 'gateway_exclusive' ? 'fa-solid fa-xmark' : 'fa-solid fa-plus';
        
        html_content = `
        <div class="node-modern type-gateway" style="min-width: 180px;">
            <div class="node-header" style="color: #f59e0b;">
                <i class="${icon}"></i> DECISÃO
            </div>
            <div class="node-body">
                ${s.label}
            </div>
            <div class="node-footer">
                <span><span class="swimlane-label" style="font-weight:600;color:#0f172a;">${poolInfo.poolName}</span></span>
            </div>
        </div>`;
    } else {
        let icon = 'fa-regular fa-user';
        let color = '#3b82f6';
        let typeLabel = 'TAREFA DE USUÁRIO';
        
        if(nType === 'task_service') {
            icon = 'fa-solid fa-gear';
            color = '#14b8a6';
            typeLabel = 'SERVIÇO';
        }
        if(nType === 'task_script') {
            icon = 'fa-solid fa-code';
            color = '#8b5cf6';
            typeLabel = 'SCRIPT';
        }
        
        html_content = `
        <div class="node-modern type-task" style="min-width: 210px;">
            <div class="node-header" style="color: ${color};">
                <i class="${icon}"></i> ${typeLabel}
            </div>
            <div class="node-body">
                ${s.label}
            </div>
            <div class="node-footer">
                <span>Resp: <span class="swimlane-label" style="font-weight:600;color:#0f172a;">${poolInfo.poolName}</span></span>
                <span>${(s.config || {}).action_code || ''}</span>
            </div>
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
    ensureArrowheadMarkers(document.getElementById('drawflow'));
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
    // 1. Encontrar o estado inicial
    const initial = states.find(s => s.is_initial) || states[0];
    if (!initial) return;

    // 2. Mapeamento de adjacência (apenas transições que vão para a frente ou que não formam ciclos imediatos)
    const forwardAdj = new Map();
    const inDegree = new Map();
    states.forEach(s => {
        forwardAdj.set(s.id, []);
        inDegree.set(s.id, 0);
    });

    transitions.forEach(t => {
        if (forwardAdj.has(t.origin_state_id) && inDegree.has(t.destination_state_id)) {
            forwardAdj.get(t.origin_state_id).push(t.destination_state_id);
        }
    });

    // 3. Atribuição de Colunas (Níveis Sequenciais) pelo Caminho Mais Longo (Longest Path DAG)
    // Isso garante que se A -> B -> C e A -> C, C ficará obrigatoriamente depois de B (à direita)
    const levels = new Map([[initial.id, 0]]);
    const queue = [initial.id];

    // BFS / Relaxamento de arestas para fluxo sequencial crescente
    const visitedEdges = new Set();
    while (queue.length > 0) {
        const u = queue.shift();
        const uLevel = levels.get(u) || 0;
        const neighbors = forwardAdj.get(u) || [];

        neighbors.forEach(v => {
            const edgeKey = `${u}->${v}`;
            // Evita loops infinitos em ciclos de retorno
            if (visitedEdges.has(edgeKey)) return;
            visitedEdges.add(edgeKey);

            const vLevel = levels.get(v);
            const candidateLevel = uLevel + 1;

            if (vLevel === undefined || candidateLevel > vLevel) {
                levels.set(v, candidateLevel);
                queue.push(v);
            }
        });
    }

    // Para nós desconectados, coloca no final
    let maxAssignedLevel = Math.max(0, ...levels.values());
    states.forEach(s => {
        if (!levels.has(s.id)) {
            maxAssignedLevel++;
            levels.set(s.id, maxAssignedLevel);
        }
    });

    // 4. Agrupamento por Raias (Pools)
    const poolOrder = [];
    states.forEach(s => {
        const { poolName } = getPoolData(s);
        if (!poolOrder.includes(poolName)) poolOrder.push(poolName);
    });

    const poolGroups = {};
    poolOrder.forEach(p => { poolGroups[p] = []; });
    states.forEach(s => {
        const { poolName } = getPoolData(s);
        poolGroups[poolName].push(s);
    });

    // 5. Posicionamento espacial sem colisão:
    // NODE_W: distância horizontal entre passos sucessivos
    // ROW_H: distância vertical entre ramificações/bifurcações dentro da mesma raia
    const NODE_W = 340;   // Largura generosa com espaço para setas e visualização clara
    const ROW_H = 170;    // Altura suficiente para os cards não se tocarem verticalmente
    const PADDING_X = 80;
    const PADDING_Y = 60;

    // Calcula o espaçamento vertical e offset de cada pool
    const poolYOffset = {};
    let currentY = PADDING_Y;

    poolOrder.forEach(poolName => {
        const pStates = poolGroups[poolName] || [];
        // Conta quantos nós estão no mesmo level dentro desta raia (bifurcações)
        const levelCount = {};
        pStates.forEach(s => {
            const lvl = levels.get(s.id) || 0;
            levelCount[lvl] = (levelCount[lvl] || 0) + 1;
        });
        const maxBranches = Math.max(1, ...Object.values(levelCount));
        poolYOffset[poolName] = currentY;
        currentY += Math.max(220, maxBranches * ROW_H + 80);
    });

    // 6. Atribui coordenadas limpas e salva
    const levelOccupancy = {}; // "pool_level" -> subRow
    const updates = [];

    // Ordenar estados: nós iniciais primeiro, depois por level crescente
    const sortedStates = [...states].sort((a, b) => {
        const la = levels.get(a.id) || 0;
        const lb = levels.get(b.id) || 0;
        if (la !== lb) return la - lb;
        return (a.label || '').localeCompare(b.label || '');
    });

    sortedStates.forEach(state => {
        const level = levels.get(state.id) || 0;
        const { poolName } = getPoolData(state);
        const poolBaseY = poolYOffset[poolName] ?? PADDING_Y;

        const key = `${poolName}_${level}`;
        const subRow = levelOccupancy[key] || 0;
        levelOccupancy[key] = subRow + 1;

        state.ui_pos_x = PADDING_X + level * NODE_W;
        state.ui_pos_y = poolBaseY + 45 + subRow * ROW_H;

        // Atualiza na memória local
        if (currentWorkflowData && currentWorkflowData.states) {
            const st = currentWorkflowData.states.find(s => s.id === state.id);
            if (st) {
                st.ui_pos_x = state.ui_pos_x;
                st.ui_pos_y = state.ui_pos_y;
            }
        }
        if (window.workflowsData) {
            const wf = window.workflowsData.find(w => w.id === currentWorkflowId);
            if (wf && wf.states) {
                const st = wf.states.find(s => s.id === state.id);
                if (st) {
                    st.ui_pos_x = state.ui_pos_x;
                    st.ui_pos_y = state.ui_pos_y;
                }
            }
        }

        updates.push(fetch(`${WORKFLOWS_API}/${currentWorkflowId}/states/${state.id}`, {
            method: 'PUT',
            headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ ui_pos_x: state.ui_pos_x, ui_pos_y: state.ui_pos_y })
        }));
    });

    Promise.all(updates)
        .then(() => {
            renderDrawflow(states, transitions);
            resetWorkflowDirty();
        })
        .catch(error => {
            console.error('Erro ao organizar workflow', error);
            alert('Não foi possível salvar a organização do layout.');
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
    closePropertiesSheet();
    // Default open on double click of empty canvas? Not needed, nodes are dragged.
}

async function openStateEditor(stateId) {
    const state = (currentWorkflowData.states || []).find(item => item.id === stateId);
    if (!state) return;
    
    // Configura o cabeçalho
    let typeName = "Elemento";
    let iconClass = "fa-solid fa-gear";
    if (state.node_type) {
        if (state.node_type.startsWith('task')) { typeName = "TAREFA"; iconClass = "fa-regular fa-user"; }
        if (state.node_type.startsWith('event')) { typeName = "EVENTO"; iconClass = "fa-regular fa-circle-play"; }
        if (state.node_type.startsWith('gateway')) { typeName = "DECISÃO"; iconClass = "fa-solid fa-xmark"; }
    }
    document.getElementById('sheet-node-type').innerHTML = `${typeName} <span class="text-muted fw-normal ms-2">#${stateId}</span>`;
    document.getElementById('sheet-node-title').textContent = state.label || 'Editar Estado';
    document.getElementById('sheet-icon').innerHTML = `<i class="${iconClass}"></i>`;
    
    // Campos
    document.getElementById('state-id').value = state.id;
    document.getElementById('state-label').value = state.label || '';
    document.getElementById('state-initial').checked = Boolean(state.is_initial);
    document.getElementById('state-completion').checked = Boolean(state.is_completion);
    
    const config = state.config || {};
    document.getElementById('state-action-code').value = config.action_code || '';
    document.getElementById('state-recipients').value = config.recipients || '';
    document.getElementById('state-execution-details').value = config.execution_details || '';
    
    const poolEl = document.getElementById('state-pool');
    if (poolEl) poolEl.value = config.pool_name || config.pool || '';
    
    const poolColorEl = document.getElementById('state-pool-color');
    if (poolColorEl) poolColorEl.value = config.color || '#cbd5e1';
    
    const taskFormEl = document.getElementById('state-task-form');
    if (taskFormEl) taskFormEl.value = config.task_form || '';
    
    document.getElementById('properties-sheet').classList.add('open');
}

function closePropertiesSheet() {
    const sheet = document.getElementById('properties-sheet');
    if(sheet) sheet.classList.remove('open');
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
    
    const poolEl = document.getElementById('state-pool');
    if (poolEl && poolEl.value.trim()) config.pool_name = poolEl.value.trim();
    
    const poolColorEl = document.getElementById('state-pool-color');
    if (poolColorEl && poolColorEl.value) config.color = poolColorEl.value;
    
    const taskFormEl = document.getElementById('state-task-form');
    if (taskFormEl && taskFormEl.value.trim()) config.task_form = taskFormEl.value.trim();
    
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
            closePropertiesSheet();
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
        item.addEventListener('click', (e) => {
            const canvas = document.getElementById('drawflow');
            const rect = canvas.getBoundingClientRect();
            // Drop it near the center or near the top
            createNodeAt(item.getAttribute('data-type'), rect.left + rect.width / 2, rect.top + 100);
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
    const zoom = (editor && editor.zoom) ? editor.zoom : 1;
    const posX = Math.max(20, Math.round(x / Math.max(zoom, 0.1)));
    const posY = Math.max(20, Math.round(y / Math.max(zoom, 0.1)));
    
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

/* -------------------------------------------------------------
   MODELOS PRONTOS DE WORKFLOW (TEMPLATES BPMN COM RAIAS)
------------------------------------------------------------- */
function openWorkflowTemplatesModal() {
    const modal = document.getElementById('modal-workflow-templates');
    if (modal) modal.classList.add('active');
}

function closeWorkflowTemplatesModal() {
    const modal = document.getElementById('modal-workflow-templates');
    if (modal) modal.classList.remove('active');
}

const WORKFLOW_PRESETS = {
    diploma_digital: {
        name: "Emissão de Diploma Digital",
        internal_name: "emissao_diploma_digital",
        states: [
            // Raia 1: Interação do Usuário / Documentação
            { key: "inicio", label: "Início", node_type: "event_start", is_initial: true, is_completion: false, config: { pool: "Interação do Usuário / Documentação", color: "#3b82f6" } },
            { key: "anexar_docs", label: "Anexar Documentos de Conclusão", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Interação do Usuário / Documentação", color: "#3b82f6", action_code: "UPLOAD_DOCS" } },
            
            // Raia 2: Validação de Documentos
            { key: "conferir_academico", label: "Conferir Histórico e Carga Horária", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Validação de Documentos", color: "#10b981", action_code: "VALIDATE_ACADEMIC" } },
            { key: "decisao_docs", label: "Documentação Completa?", node_type: "gateway_exclusive", is_initial: false, is_completion: false, config: { pool: "Validação de Documentos", color: "#10b981" } },
            { key: "solicitar_pendencias", label: "Solicitar Documentos Pendentes", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Interação do Usuário / Documentação", color: "#3b82f6", action_code: "REQUEST_DOCS" } },

            // Raia 3: Assinatura Digital
            { key: "selecionar_signatarios", label: "Selecionar Signatários Institucionais", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Assinatura Digital", color: "#f59e0b", action_code: "SELECT_SIGNERS" } },
            { key: "coletar_assinaturas", label: "Assinar Diploma (Reitor / Diretor)", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Assinatura Digital", color: "#f59e0b", action_code: "SIGN_DOCUMENT" } },

            // Raia 4: Serviços Automáticos
            { key: "gerar_xml", label: "Gerar XML do Diploma (Portaria MEC)", node_type: "task_service", is_initial: false, is_completion: false, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6", action_code: "GENERATE_XML" } },
            { key: "gerar_rvdd", label: "Emitir Representação Visual (RVDD)", node_type: "task_service", is_initial: false, is_completion: false, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6", action_code: "RENDER_RVDD" } },
            { key: "fim", label: "Diploma Emitido e Registrado", node_type: "event_end", is_initial: false, is_completion: true, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6" } }
        ],
        transitions: [
            { from: "inicio", to: "anexar_docs", label: "Iniciar Processo" },
            { from: "anexar_docs", to: "conferir_academico", label: "Enviar para Secretaria" },
            { from: "conferir_academico", to: "decisao_docs", label: "Avaliar" },
            { from: "decisao_docs", to: "solicitar_pendencias", label: "Pendência" },
            { from: "solicitar_pendencias", to: "conferir_academico", label: "Reenviar Documento" },
            { from: "decisao_docs", to: "selecionar_signatarios", label: "Aprovado" },
            { from: "selecionar_signatarios", to: "coletar_assinaturas", label: "Despachar Assinaturas" },
            { from: "coletar_assinaturas", to: "gerar_xml", label: "Assinado com Sucesso" },
            { from: "gerar_xml", to: "gerar_rvdd", label: "XML Validado" },
            { from: "gerar_rvdd", to: "fim", label: "Concluir" }
        ]
    },

    matricula: {
        name: "Validação de Matrícula e Ingresso",
        internal_name: "validacao_matricula",
        states: [
            { key: "inicio", label: "Início da Inscrição", node_type: "event_start", is_initial: true, is_completion: false, config: { pool: "Interação do Usuário / Documentação", color: "#3b82f6" } },
            { key: "upload_identificacao", label: "Envio de RG, CPF e Histórico", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Interação do Usuário / Documentação", color: "#3b82f6", action_code: "UPLOAD_IDENTITY" } },
            { key: "analise_secretaria", label: "Análise da Secretaria Geral", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Validação de Documentos", color: "#10b981", action_code: "VALIDATE_IDENTITY" } },
            { key: "decisao_conforme", label: "Documentos Válidos?", node_type: "gateway_exclusive", is_initial: false, is_completion: false, config: { pool: "Validação de Documentos", color: "#10b981" } },
            { key: "pedir_revisao", label: "Notificar Candidato para Correção", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Interação do Usuário / Documentação", color: "#3b82f6", action_code: "REQUEST_CORRECTION" } },
            { key: "gerar_registro", label: "Criar RA e Prontuário no Sistema", node_type: "task_service", is_initial: false, is_completion: false, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6", action_code: "GENERATE_STUDENT_RECORD" } },
            { key: "fim_matricula", label: "Matrícula Efetivada", node_type: "event_end", is_initial: false, is_completion: true, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6" } }
        ],
        transitions: [
            { from: "inicio", to: "upload_identificacao", label: "Iniciar" },
            { from: "upload_identificacao", to: "analise_secretaria", label: "Submeter Documentos" },
            { from: "analise_secretaria", to: "decisao_conforme", label: "Verificar" },
            { from: "decisao_conforme", to: "pedir_revisao", label: "Incompleto" },
            { from: "pedir_revisao", to: "analise_secretaria", label: "Documento Retificado" },
            { from: "decisao_conforme", to: "gerar_registro", label: "Documentação Aprovada" },
            { from: "gerar_registro", to: "fim_matricula", label: "Finalizar Inscrição" }
        ]
    },

    contrato: {
        name: "Contrato de Prestação de Serviços Educacionais",
        internal_name: "contrato_educacional",
        states: [
            { key: "inicio", label: "Solicitação de Contrato", node_type: "event_start", is_initial: true, is_completion: false, config: { pool: "Interação do Usuário / Documentação", color: "#3b82f6" } },
            { key: "gerar_minuta", label: "Gerar Minuta do Contrato com Dados do Aluno", node_type: "task_service", is_initial: false, is_completion: false, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6", action_code: "GENERATE_CONTRACT_DRAFT" } },
            { key: "conferir_financeiro", label: "Conferir Plano de Pagamento e Bolsas", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Validação de Documentos", color: "#10b981", action_code: "VALIDATE_FINANCES" } },
            { key: "assinatura_aluno", label: "Assinatura do Aluno / Responsável", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Assinatura Digital", color: "#f59e0b", action_code: "STUDENT_SIGNATURE" } },
            { key: "assinatura_instituicao", label: "Assinatura Digital da Diretoria (A1)", node_type: "task_user", is_initial: false, is_completion: false, config: { pool: "Assinatura Digital", color: "#f59e0b", action_code: "DIRECTOR_SIGNATURE" } },
            { key: "arquivar_contrato", label: "Carimbar Data/Hora e Arquivar no Acervo", node_type: "task_service", is_initial: false, is_completion: false, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6", action_code: "ARCHIVE_CONTRACT" } },
            { key: "fim_contrato", label: "Contrato Registrado e Válido", node_type: "event_end", is_initial: false, is_completion: true, config: { pool: "Serviços Automáticos (XML / Visual / Integração)", color: "#8b5cf6" } }
        ],
        transitions: [
            { from: "inicio", to: "gerar_minuta", label: "Emitir" },
            { from: "gerar_minuta", to: "conferir_financeiro", label: "Enviar para Financeiro" },
            { from: "conferir_financeiro", to: "assinatura_aluno", label: "Liberar Assinatura" },
            { from: "assinatura_aluno", to: "assinatura_instituicao", label: "Aluno Assinou" },
            { from: "assinatura_instituicao", to: "arquivar_contrato", label: "Ambas as Partes Assinaram" },
            { from: "arquivar_contrato", to: "fim_contrato", label: "Concluir" }
        ]
    }
};

async function applyWorkflowPreset(presetKey) {
    const preset = WORKFLOW_PRESETS[presetKey];
    if (!preset) return;

    if (!confirm(`Deseja carregar o modelo "${preset.name}"? As alterações não salvas no canvas atual serão substituídas.`)) {
        return;
    }

    closeWorkflowTemplatesModal();

    try {
        let targetWorkflowId = currentWorkflowId;

        // Se nenhum workflow estiver aberto, cria um novo workflow no servidor com o nome do modelo
        if (!targetWorkflowId) {
            const respWf = await fetch(WORKFLOWS_API, {
                method: 'POST',
                headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: preset.name,
                    internal_name: `${preset.internal_name}_${Date.now()}`,
                    is_active: true
                })
            });
            if (!respWf.ok) throw new Error("Erro ao criar o workflow.");
            const newWf = await respWf.json();
            targetWorkflowId = newWf.id;
            currentWorkflowId = newWf.id;
            currentWorkflowData = newWf;
            await loadWorkflows();
        }

        // Se já tinha estados, remove os antigos para aplicar o modelo limpo
        if (currentWorkflowData && currentWorkflowData.states && currentWorkflowData.states.length > 0) {
            for (const s of currentWorkflowData.states) {
                await fetch(`${WORKFLOWS_API}/${targetWorkflowId}/states/${s.id}`, {
                    method: 'DELETE',
                    headers: getAuthHeaders()
                }).catch(() => {});
            }
        }

        // 1. Criar os estados do preset
        const createdStatesMap = {}; // key -> stateObj
        for (const st of preset.states) {
            const respSt = await fetch(`${WORKFLOWS_API}/${targetWorkflowId}/states`, {
                method: 'POST',
                headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    label: st.label,
                    node_type: st.node_type,
                    is_initial: st.is_initial,
                    is_completion: st.is_completion,
                    ui_pos_x: 50,
                    ui_pos_y: 50,
                    config: st.config
                })
            });
            if (respSt.ok) {
                const created = await respSt.json();
                createdStatesMap[st.key] = created;
            }
        }

        // 2. Criar as transições
        for (const tr of preset.transitions) {
            const origin = createdStatesMap[tr.from];
            const dest = createdStatesMap[tr.to];
            if (origin && dest) {
                await fetch(`${WORKFLOWS_API}/${targetWorkflowId}/transitions`, {
                    method: 'POST',
                    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        origin_state_id: origin.id,
                        destination_state_id: dest.id,
                        label: tr.label
                    })
                });
            }
        }

        // 3. Recarregar e organizar automaticamente o novo modelo com raias e setas
        const wRes = await fetch(WORKFLOWS_API, { headers: getAuthHeaders() });
        const wData = await wRes.json();
        const workflows = wData.items ? wData.items : wData;
        const updated = workflows.find(w => w.id === targetWorkflowId);
        if (updated) {
            selectWorkflow(updated);
            setTimeout(() => organizeCurrentWorkflow(), 350);
        }

    } catch(err) {
        console.error("Erro ao aplicar modelo de workflow:", err);
        alert("Erro ao aplicar o modelo: " + err.message);
    }
}
