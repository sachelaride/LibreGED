document.addEventListener('DOMContentLoaded', () => {
    var id = document.getElementById("drawflow");
    var editor = new Drawflow(id);
    editor.reroute = true;
    editor.reroute_fix_curvature = true;
    editor.start();

    // Register Nodes with new modern HTML
    const getNodeHtml = (type, title, subtitle, icon, iconColor) => `
        <div class="node-modern type-${type}">
            <div class="node-header" style="color: ${iconColor};">
                <i class="${icon}"></i> ${subtitle}
                <span class="badge-status">Ativa</span>
            </div>
            <div class="node-body">
                ${title}
            </div>
            <div class="node-footer">
                <span>Resp: <span class="swimlane-label">Secretaria</span></span>
                <span>48h</span>
            </div>
        </div>
    `;

    editor.registerNode('start', getNodeHtml('start', 'Início do Fluxo', 'EVENTO DE INÍCIO', 'fa-regular fa-circle-play', '#10b981'));
    editor.registerNode('end', getNodeHtml('end', 'Fim do Fluxo', 'EVENTO DE TÉRMINO', 'fa-regular fa-circle-stop', '#ef4444'));
    editor.registerNode('user_task', getNodeHtml('user', 'Nova Tarefa de Usuário', 'TAREFA DE USUÁRIO', 'fa-regular fa-user', '#3b82f6'));
    editor.registerNode('service_task', getNodeHtml('service', 'Integração Automática', 'SERVIÇO', 'fa-solid fa-gear', '#14b8a6'));
    editor.registerNode('gateway', getNodeHtml('gateway', 'Decisão / Aprovação', 'DECISÃO EXCLUSIVA', 'fa-solid fa-xmark', '#f59e0b'));

    window.editor = editor;

    // Events
    editor.on('nodeSelected', function(id) {
        showProperties(id);
    });

    editor.on('nodeUnselected', function() {
        closePropertiesSheet();
    });
});

// Drag and Drop Logic
function allowDrop(ev) {
    ev.preventDefault();
}

function drag(ev) {
    // Determine which node is being dragged from the data-node attribute
    let nodeType = ev.target.getAttribute('data-node');
    // If user clicked the icon inside the drag tool, find the closest drag-tool parent
    if (!nodeType && ev.target.closest('.drag-tool')) {
        nodeType = ev.target.closest('.drag-tool').getAttribute('data-node');
    }
    if (nodeType) {
        ev.dataTransfer.setData("node", nodeType);
    }
}

function drop(ev) {
    ev.preventDefault();
    var nodeType = ev.dataTransfer.getData("node");
    if(nodeType) {
        addNodeToDrawFlow(nodeType, ev.clientX, ev.clientY);
    }
}

function addNodeToDrawFlow(name, pos_x, pos_y) {
    if(window.editor.editor_mode === 'edit') {
        pos_x = pos_x * (window.editor.precanvas.clientWidth / (window.editor.precanvas.clientWidth * window.editor.zoom)) - (window.editor.precanvas.getBoundingClientRect().x * (window.editor.precanvas.clientWidth / (window.editor.precanvas.clientWidth * window.editor.zoom)));
        pos_y = pos_y * (window.editor.precanvas.clientHeight / (window.editor.precanvas.clientHeight * window.editor.zoom)) - (window.editor.precanvas.getBoundingClientRect().y * (window.editor.precanvas.clientHeight / (window.editor.precanvas.clientHeight * window.editor.zoom)));
        
        // Add nodes. Drawflow syntax: addNode(name, num_inputs, num_outputs, posx, posy, class, data, html_template, vue_component)
        switch (name) {
            case 'start':
                window.editor.addNode('start', 0, 1, pos_x, pos_y, 'start', { name: 'Início', type: 'start' }, name, 'vue');
                break;
            case 'end':
                window.editor.addNode('end', 1, 0, pos_x, pos_y, 'end', { name: 'Fim', type: 'end' }, name, 'vue');
                break;
            case 'user_task':
                window.editor.addNode('user_task', 1, 1, pos_x, pos_y, 'user_task', { name: 'Validação de Documentos', type: 'user', swimlane: 'secretaria' }, name, 'vue');
                break;
            case 'service_task':
                window.editor.addNode('service_task', 1, 1, pos_x, pos_y, 'service_task', { name: 'Chamada de API', type: 'service' }, name, 'vue');
                break;
            case 'gateway':
                window.editor.addNode('gateway', 1, 2, pos_x, pos_y, 'gateway', { name: 'Aprovado?', type: 'gateway' }, name, 'vue');
                break;
        }
    }
}

// ----------------------------------------------------
// BOTTOM SHEET (Drawer) LOGIC
// ----------------------------------------------------
let _selectedNodeId = null;

function showProperties(id) {
    _selectedNodeId = id;
    var nodeInfo = window.editor.getNodeFromId(id);
    var data = nodeInfo.data;

    // Map node type to title/icon
    let iconClass = 'fa-regular fa-user';
    let typeName = 'TAREFA DE USUÁRIO';
    
    if (data.type === 'start') { iconClass = 'fa-regular fa-circle-play'; typeName = 'EVENTO DE INÍCIO'; }
    if (data.type === 'end') { iconClass = 'fa-regular fa-circle-stop'; typeName = 'EVENTO DE TÉRMINO'; }
    if (data.type === 'service') { iconClass = 'fa-solid fa-gear'; typeName = 'SERVIÇO (SISTEMA)'; }
    if (data.type === 'gateway') { iconClass = 'fa-solid fa-xmark'; typeName = 'DECISÃO EXCLUSIVA'; }

    // Update Header
    document.getElementById('sheet-icon').innerHTML = `<i class="${iconClass}"></i>`;
    document.getElementById('sheet-node-type').innerHTML = `${typeName} <span class="text-muted fw-normal ms-2">#NODE-${id}</span>`;
    document.getElementById('sheet-node-title').textContent = data.name || 'Nova Tarefa';

    // Update Form Fields
    document.getElementById('prop-name').value = data.name || '';
    if (document.getElementById('prop-swimlane')) {
        document.getElementById('prop-swimlane').value = data.swimlane || 'secretaria';
    }
    if (document.getElementById('prop-config')) {
        document.getElementById('prop-config').value = data.config || '';
    }

    // Open sheet
    document.getElementById('properties-sheet').classList.add('open');
    switchSheetTab('config');
}

function closePropertiesSheet() {
    document.getElementById('properties-sheet').classList.remove('open');
    _selectedNodeId = null;
}

function switchSheetTab(tabId) {
    // Update tabs
    document.querySelectorAll('.sheet-tab').forEach(t => t.classList.remove('active'));
    event.currentTarget.classList.add('active');

    // Update content panes
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
}

function updateSelectedNodeData(key, value) {
    if (!_selectedNodeId) return;
    
    // Update internal drawflow data object
    var nodeInfo = window.editor.getNodeFromId(_selectedNodeId);
    nodeInfo.data[key] = value;
    window.editor.updateNodeDataFromId(_selectedNodeId, nodeInfo.data);
    
    // Visually update the node html if name was changed
    if (key === 'name') {
        document.getElementById('sheet-node-title').textContent = value;
        // In drawflow we would ideally re-render the HTML content of the node here,
        // but for this mock we just update the DOM directly if possible.
        const nodeElement = document.getElementById('node-'+_selectedNodeId);
        if(nodeElement) {
            const titleEl = nodeElement.querySelector('.node-body');
            if(titleEl) titleEl.textContent = value;
        }
    }
    if (key === 'swimlane') {
        const nodeElement = document.getElementById('node-'+_selectedNodeId);
        if(nodeElement) {
            const slEl = nodeElement.querySelector('.swimlane-label');
            if(slEl) slEl.textContent = value;
        }
    }
}

function copyTag(el) {
    const text = el.innerText;
    navigator.clipboard.writeText(text).then(() => {
        let originalText = text;
        el.innerText = "Copiado!";
        setTimeout(() => { el.innerText = originalText; }, 1000);
    });
}

function saveWorkflow() {
    var exportData = window.editor.export();
    console.log("Fluxo a ser salvo no backend:", exportData);
    alert("Dados do workflow exportados para o console no formato JSON!");
}
