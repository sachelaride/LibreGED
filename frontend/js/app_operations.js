// app_operations.js - Lida com a busca e upload do app.html

async function performSearch() {
    const query = document.getElementById('search-query').value;
    const resultsContainer = document.getElementById('search-results');
    
    if(!query.trim()) {
        resultsContainer.innerHTML = '<p class="text-muted" style="text-align:center;">Digite um termo para começar a busca.</p>';
        return;
    }

    resultsContainer.innerHTML = '<p style="text-align:center;">Buscando...</p>';
    
    try {
        const response = await fetch(`${API_URL}/documents/search?q=${encodeURIComponent(query)}`, {
            headers: getAuthHeaders()
        });
        
        if(!response.ok) {
            resultsContainer.innerHTML = '<p style="color:red; text-align:center;">Erro ao realizar a busca.</p>';
            return;
        }

        const results = await response.json();
        
        const documentos = results.items || [];
        if(documentos.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted" style="text-align:center;">Nenhum documento encontrado.</p>';
            return;
        }

        let html = '<div style="display:grid; gap:15px;">';
        documentos.forEach(doc => {
            html += `
                <div class="glass-panel" style="padding: 20px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <h4 style="margin-bottom:5px; color:var(--primary);">${doc.file_name || 'Documento sem nome'}</h4>
                        <p style="font-size:13px; color:var(--text-muted);">
                            <strong>Tipo:</strong> ${doc.document_category_code || 'N/A'} | 
                            <strong>Data:</strong> ${new Date(doc.created_at).toLocaleDateString()}
                        </p>
                    </div>
                    <div>
                        <button class="btn-secondary btn-small" onclick="viewDocument('${doc.id}')">Visualizar</button>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        resultsContainer.innerHTML = html;

    } catch(e) {
        resultsContainer.innerHTML = `<p style="color:red; text-align:center;">Falha de comunicação: ${e.message}</p>`;
    }
}

function viewDocument(docId) {
    alert(`Redirecionando para visualizador do documento: ${docId}\n(Recurso em desenvolvimento)`);
}

let tiposDocumentaisUpload = [];

async function carregarTiposUpload() {
    const resposta = await fetch(`${API_URL}/document-types?page=1&size=100`, {headers: getAuthHeaders()});
    if (!resposta.ok) throw new Error('Não foi possível carregar os tipos documentais.');
    const dados = await resposta.json();
    tiposDocumentaisUpload = dados.items || [];
    const seletor = document.getElementById('upload-document-type');
    seletor.innerHTML = '<option value="">Selecione o tipo documental</option>';
    tiposDocumentaisUpload.filter(tipo => tipo.is_active).forEach(tipo => {
        const opcao = document.createElement('option');
        opcao.value = tipo.id;
        opcao.textContent = tipo.name;
        seletor.append(opcao);
    });
}

function carregarIndicesUpload() {
    const tipo = tiposDocumentaisUpload.find(item => item.id === document.getElementById('upload-document-type').value);
    const painel = document.getElementById('upload-indices');
    painel.replaceChildren();
    if (!tipo) return;
    (tipo.indices || []).forEach(vinculo => {
        const indice = vinculo.index;
        const grupo = document.createElement('div');
        grupo.className = 'form-group';
        const rotulo = document.createElement('label');
        rotulo.textContent = `${indice.name}${vinculo.is_required ? ' *' : ''}`;
        let campo;
        if (indice.auto_increment) {
            campo = document.createElement('input');
            campo.disabled = true;
            campo.placeholder = 'Gerado automaticamente';
        } else if (indice.type.toLocaleLowerCase() === 'lista') {
            campo = document.createElement('select');
            campo.append(new Option('Selecione', ''));
            (indice.options || []).forEach(valor => campo.append(new Option(valor, valor)));
        } else if (indice.type.toLocaleLowerCase() === 'booleano') {
            campo = document.createElement('select');
            campo.append(new Option('Selecione', ''), new Option('Sim', 'true'), new Option('Não', 'false'));
        } else {
            campo = document.createElement('input');
            campo.type = indice.type.toLocaleLowerCase() === 'data' ? 'date' :
                ['número', 'numero'].includes(indice.type.toLocaleLowerCase()) ? 'number' : 'text';
            if (indice.mask) campo.pattern = indice.mask;
        }
        campo.dataset.indexId = indice.id;
        campo.dataset.autoIncrement = indice.auto_increment ? 'true' : 'false';
        campo.required = vinculo.is_required && !indice.auto_increment;
        grupo.append(rotulo, campo);
        painel.append(grupo);
    });
}

let currentStudentId = null;
let currentInstitutionId = null;

async function createDossier() {
    const name = document.getElementById('student-name').value;
    const cpf = document.getElementById('student-cpf').value;
    
    if(!name || !cpf) {
        alert("Nome e CPF são obrigatórios para iniciar o Dossiê.");
        return;
    }

    try {
        // Obter instituição (pega a primeira disponível para simplificar o MVP)
        const instResp = await fetch(`${API_URL}/institutions`, { headers: getAuthHeaders() });
        const insts = await instResp.json();
        if(insts.length === 0) {
            alert("Nenhuma instituição encontrada no sistema.");
            return;
        }
        currentInstitutionId = insts[0].id;

        // Criar Aluno (Mockando email e data de nascimento se não existirem na UI)
        const studentResp = await fetch(`${API_URL}/students`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                institution_id: currentInstitutionId,
                full_name: name,
                cpf: cpf,
                birth_date: "2000-01-01", // MOCK
                email: `${cpf}@aluno.com` // MOCK
            })
        });
        
        if(!studentResp.ok) {
            const data = await studentResp.json();
            // Se já existe, tenta buscar a lista e achar ele
            if(studentResp.status === 409) {
                const listResp = await fetch(`${API_URL}/students?institution_id=${currentInstitutionId}`, { headers: getAuthHeaders() });
                const students = await listResp.json();
                const existing = students.find(s => s.cpf === cpf);
                if(existing) {
                    currentStudentId = existing.id;
                    alert("Aluno já existia. Dossiê aberto para o aluno existente.");
                }
            } else {
                alert("Erro ao criar aluno: " + (data.detail || ''));
                return;
            }
        } else {
            const newStudent = await studentResp.json();
            currentStudentId = newStudent.id;
            alert("Aluno cadastrado! Você já pode arrastar os documentos do aluno.");
        }

    } catch(e) {
        alert('Erro de rede: ' + e);
        return;
    }

    // Libera a zona de upload
    const uploadZone = document.getElementById('upload-zone');
    uploadZone.style.opacity = '1';
    uploadZone.style.pointerEvents = 'auto';
    try {
        await carregarTiposUpload();
    } catch (erro) {
        alert(erro.message);
        return;
    }
    
    // Adiciona listener pro clique na zona
    uploadZone.onclick = () => document.getElementById('file-input').click();
    
    // Configura os eventos de Drag & Drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--primary)';
        uploadZone.style.background = 'rgba(0, 210, 255, 0.1)';
    });

    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'rgba(255,255,255,0.2)';
        uploadZone.style.background = 'transparent';
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'rgba(255,255,255,0.2)';
        uploadZone.style.background = 'transparent';
        
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    // Quando clica no botão "Arraste documentos aqui" ele aciona o input escondido
    document.getElementById('file-input').addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    alert("Dossiê iniciado! Você já pode arrastar ou selecionar os documentos do aluno no painel ao lado.");
}

async function handleFiles(files) {
    if(files.length === 0) return;
    
    if(!currentStudentId) {
        alert("Nenhum aluno ativo no dossiê.");
        return;
    }

    const docTypeId = document.getElementById('upload-document-type').value;
    if (!docTypeId) {
        alert('Selecione o tipo documental antes de enviar.');
        return;
    }

    const formularioValido = [...document.querySelectorAll('#upload-indices [data-index-id]')]
        .every(campo => campo.disabled || campo.reportValidity());
    if (!formularioValido) return;
    const indices = [...document.querySelectorAll('#upload-indices [data-index-id]')]
        .filter(campo => campo.dataset.autoIncrement !== 'true' && campo.value !== '')
        .map(campo => ({index_id: campo.dataset.indexId, value: campo.value}));

    alert(`${files.length} arquivo(s) selecionado(s). Iniciando upload para o Dossiê...`);
    
    for(let i=0; i<files.length; i++) {
        const formData = new FormData();
        formData.append("title", files[i].name);
        formData.append("document_type_id", docTypeId);
        formData.append("indices_json", JSON.stringify(indices));
        formData.append("file", files[i]);
        
        try {
            const response = await fetch(`${API_URL}/documents/upload`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: formData
            });
            
            if(!response.ok) {
                const erro = await response.json().catch(() => ({}));
                alert(`Erro em ${files[i].name}: ${erro.detail || 'upload recusado'}`);
                return;
            }
        } catch(e) {
            console.error("Erro de rede no upload " + files[i].name);
        }
    }
    
    alert("Uploads concluídos! (Verifique o log de rede para detalhes)");
}

// --- Dashboard & Sites (ECM) ---
async function loadDashboard() {
    // 1. Carregar layout do Dashboard
    // 2. Carregar My Tasks para o dashlet
    
    try {
        const response = await fetch(`${API_URL}/workflows/tasks/my-tasks`, {
            headers: getAuthHeaders()
        });
        const dashlet = document.getElementById('dashlet-tasks');
        if(!response.ok) {
            dashlet.innerHTML = '<p style="color:red; text-align:center;">Erro ao carregar tarefas.</p>';
            return;
        }
        const tasks = await response.json();
        
        if(tasks.length === 0) {
            dashlet.innerHTML = '<p class="text-muted" style="text-align:center; padding-top:20px;">Você não tem tarefas pendentes. 🎉</p>';
            return;
        }
        
        let html = '';
        tasks.forEach(t => {
            html += `
                <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 6px; margin-bottom: 10px; border-left: 4px solid var(--primary);">
                    <div style="font-weight: 600; font-size:14px; margin-bottom:4px;">${t.name}</div>
                    <div style="font-size: 12px; color: var(--text-muted);">${t.description || ''}</div>
                    <div style="margin-top: 8px; text-align:right;">
                        <button class="btn-primary" style="padding: 4px 10px; font-size:12px;" onclick="completeTask('${t.id}')">Concluir</button>
                    </div>
                </div>
            `;
        });
        dashlet.innerHTML = html;
        
    } catch (e) {
        console.error(e);
    }
}

async function completeTask(taskId) {
    if(!confirm("Deseja realmente marcar esta tarefa como concluída?")) return;
    
    try {
        const response = await fetch(`${API_URL}/workflows/tasks/${taskId}/complete`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action: 'COMPLETE' })
        });
        
        if(response.ok) {
            alert('Tarefa concluída!');
            loadDashboard();
        } else {
            alert('Erro ao concluir tarefa');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

async function loadSites() {
    const grid = document.getElementById('sites-grid');
    grid.innerHTML = '<p class="text-muted">Carregando espaços...</p>';
    
    try {
        const response = await fetch(`${API_URL}/ecm/sites`, {
            headers: getAuthHeaders()
        });
        
        if(!response.ok) {
            grid.innerHTML = '<p style="color:red;">Erro ao buscar espaços colaborativos.</p>';
            return;
        }
        
        const sites = await response.json();
        if(sites.length === 0) {
            grid.innerHTML = '<p class="text-muted" style="grid-column: 1 / -1; text-align:center;">Nenhum Espaço Colaborativo encontrado.</p>';
            return;
        }
        
        let html = '';
        sites.forEach(site => {
            html += `
                <div class="glass-panel" style="padding: 20px; transition: transform 0.2s;">
                    <div style="font-size: 24px; color:var(--primary); margin-bottom:10px;"><i class="fa-solid fa-users-rectangle"></i></div>
                    <h3 style="margin-bottom: 5px;">${site.title}</h3>
                    <p style="font-size: 12px; color:var(--text-muted); margin-bottom:15px;">${site.name} • ${site.visibility}</p>
                    <p style="font-size: 14px; margin-bottom:20px; height: 40px; overflow:hidden;">${site.description || 'Sem descrição.'}</p>
                    <button class="btn-secondary w-100" onclick="alert('Entrando no site: ${site.id}')">Acessar Espaço</button>
                </div>
            `;
        });
        grid.innerHTML = html;
        
    } catch(e) {
        grid.innerHTML = '<p style="color:red;">Erro de comunicação.</p>';
    }
}

function openCreateSiteModal() {
    document.getElementById('create-site-form').style.display = 'block';
}

async function submitCreateSite() {
    const title = document.getElementById('site-title').value;
    const name = document.getElementById('site-name').value;
    const desc = document.getElementById('site-desc').value;
    
    if(!title || !name) {
        alert('Título e URL são obrigatórios');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/ecm/sites`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                name: name,
                description: desc,
                visibility: 'PUBLIC'
            })
        });
        
        if(response.ok) {
            document.getElementById('create-site-form').style.display = 'none';
            document.getElementById('site-title').value = '';
            document.getElementById('site-name').value = '';
            document.getElementById('site-desc').value = '';
            loadSites();
        } else {
            const data = await response.json();
            alert('Erro ao criar site: ' + (data.detail || ''));
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

// --- Biblioteca de Documentos ---
let currentFolderId = null;
let currentFolderPath = []; // Array de {id, name}
let loadedNodes = {}; // Cache de nós para o modal

function renderLibraryTree(nodes) {
    const tree = document.getElementById('library-tree');
    if(!tree) return;

    const folders = nodes.filter(node => node.node_type === 'cm:folder' || node.node_type === 'ies:pasta');
    const items = [{ id: null, name: 'Raiz', level: 0, active: currentFolderPath.length === 0 }];

    currentFolderPath.forEach((folder, index) => {
        items.push({
            id: folder.id,
            name: folder.name,
            level: Math.min(index + 1, 2),
            active: index === currentFolderPath.length - 1
        });
    });

    folders.forEach(folder => {
        items.push({ id: folder.id, name: folder.name, level: currentFolderPath.length ? 2 : 1, active: false });
    });

    tree.innerHTML = items.map(item => `
        <button class="tree-item level-${item.level} ${item.active ? 'active' : ''}" type="button" data-folder-id="${item.id || ''}">
            <i class="fa-solid ${item.active && item.id === null ? 'fa-house' : 'fa-folder'}" aria-hidden="true"></i>
            <span>${item.name}</span>
        </button>
    `).join('');

    tree.querySelectorAll('.tree-item').forEach(button => {
        button.addEventListener('click', () => {
            const folderId = button.dataset.folderId || null;
            if(!folderId) {
                currentFolderPath = [];
                loadLibrary(null);
                return;
            }

            const pathIndex = currentFolderPath.findIndex(folder => folder.id === folderId);
            if(pathIndex >= 0) {
                currentFolderPath = currentFolderPath.slice(0, pathIndex + 1);
            } else {
                const folder = folders.find(item => item.id === folderId);
                if(folder) currentFolderPath.push({ id: folder.id, name: folder.name });
            }
            loadLibrary(folderId);
        });
    });
}

async function loadLibrary(parentId = null) {
    currentFolderId = parentId;
    const grid = document.getElementById('library-grid');
    grid.innerHTML = '<p class="text-muted">Carregando arquivos...</p>';
    
    // Atualizar Breadcrumb
    const btnNavUp = document.getElementById('btn-nav-up');
    const breadcrumb = document.getElementById('breadcrumb');
    
    if(!parentId) {
        btnNavUp.style.display = 'none';
        breadcrumb.innerText = '/ Raiz';
        currentFolderPath = [];
    } else {
        btnNavUp.style.display = 'inline-block';
        let pathStr = '/ Raiz';
        currentFolderPath.forEach(f => {
            pathStr += ` / ${f.name}`;
        });
        breadcrumb.innerText = pathStr;
    }
    
    try {
        let url = `${API_URL}/ecm/nodes`;
        if(parentId) url += `?parent_id=${parentId}`;
        
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        
        if(!response.ok) throw new Error("Erro ao carregar");
        const nodes = await response.json();
        
        loadedNodes = {};
        renderLibraryTree(nodes);
        
        if(nodes.length === 0) {
            grid.innerHTML = '<p class="text-muted" style="grid-column: 1 / -1; text-align:center; margin-top:20px;">Pasta vazia.</p>';
            return;
        }
        
        let html = '';
        nodes.forEach(node => {
            loadedNodes[node.id] = node;
            const isFolder = node.node_type === 'cm:folder' || node.node_type === 'ies:pasta';
            const icon = isFolder ? '<i class="fa-solid fa-folder" style="color:#FFD166;"></i>' : '<i class="fa-solid fa-file-lines" style="color:var(--primary);"></i>';
            const onClick = isFolder ? `onclick="navigateDown('${node.id}', '${node.name}')"` : `onclick="openDocumentDetails('${node.id}')"`;
            
            html += `
                <div class="glass-panel" style="padding: 15px; text-align:center; cursor:pointer; transition: transform 0.2s; min-height: 120px; display:flex; flex-direction:column; justify-content:center;" ${onClick} title="${node.name}">
                    <div style="font-size: 32px; margin-bottom:10px;">${icon}</div>
                    <div style="font-size: 13px; font-weight: 500; word-wrap: break-word; overflow:hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                        ${node.name}
                    </div>
                </div>
            `;
        });
        grid.innerHTML = html;
        
    } catch(e) {
        grid.innerHTML = `<p style="color:red;">Falha: ${e.message}</p>`;
    }
}

function navigateDown(folderId, folderName) {
    currentFolderPath.push({id: folderId, name: folderName});
    loadLibrary(folderId);
}

function navigateUp() {
    if(currentFolderPath.length === 0) return;
    
    currentFolderPath.pop();
    if(currentFolderPath.length === 0) {
        loadLibrary(null);
    } else {
        const parent = currentFolderPath[currentFolderPath.length - 1];
        loadLibrary(parent.id);
    }
}

async function promptCreateFolder() {
    const folderName = prompt("Nome da nova pasta:");
    if(!folderName) return;
    
    try {
        const response = await fetch(`${API_URL}/ecm/nodes`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                node_type: 'cm:folder',
                name: folderName,
                parent_id: currentFolderId,
                properties: {}
            })
        });
        
        if(response.ok) {
            loadLibrary(currentFolderId);
        } else {
            alert('Erro ao criar pasta.');
        }
    } catch(e) {
        alert('Erro: ' + e);
    }
}

async function uploadToLibrary(files) {
    if(files.length === 0) return;
    
    const formData = new FormData();
    for(let i=0; i<files.length; i++) {
        formData.append("files", files[i]);
    }
    formData.append("node_type", "cm:content");
    if(currentFolderId) {
        formData.append("parent_id", currentFolderId);
    }
    
    document.getElementById('library-grid').innerHTML = '<p class="text-muted" style="grid-column: 1 / -1; text-align:center;">Fazendo upload...</p>';
    
    try {
        const response = await fetch(`${API_URL}/ecm/nodes/upload`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });
        
        if(response.ok) {
            loadLibrary(currentFolderId);
        } else {
            alert('Erro no upload.');
            loadLibrary(currentFolderId);
        }
    } catch(e) {
        alert('Erro: ' + e);
        loadLibrary(currentFolderId);
    }
    
    // Clear input
    document.getElementById('library-upload-input').value = "";
}

function setupLibraryDropzone() {
    const dropzone = document.getElementById('library-grid');
    if(!dropzone || dropzone.dataset.dropzoneReady) return;

    dropzone.dataset.dropzoneReady = 'true';
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add('is-dragging');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove('is-dragging');
        });
    });

    dropzone.addEventListener('drop', (event) => {
        if(event.dataTransfer.files.length > 0) {
            uploadToLibrary(event.dataTransfer.files);
        }
    });
}

document.addEventListener('DOMContentLoaded', setupLibraryDropzone);

// --- Document Details Modal (Metadata & Workflows) ---
function openDocumentDetails(nodeId) {
    const node = loadedNodes[nodeId];
    if(!node) return;
    
    document.getElementById('doc-modal-id').value = node.id;
    document.getElementById('doc-modal-title').innerText = node.name;
    document.getElementById('doc-modal-version').innerText = `${node.major_version}.${node.minor_version}`;
    
    // Formatar JSON de propriedades para exibição
    const propsJson = JSON.stringify(node.properties || {}, null, 2);
    document.getElementById('doc-modal-props').value = propsJson;
    renderDocumentTags(node.tags || []);
    
    // Abrir modal na aba meta
    switchModalTab('meta');
    
    // Obter Workflows disponíveis e popular select (Simplificado, fixaremos o ID 1 se for o único, mas o ideal é fazer GET /api/workflows)
    // Para simplificar, vamos assumir que o Workflow Padrão (Revisar & Aprovar) tem id = "1" ou "workflow_uuid".
    // Isso pode requerer um Fetch na API de workflows disponíveis
    
    document.getElementById('document-modal').style.display = 'flex';
}

function renderDocumentTags(tags) {
    const container = document.getElementById('doc-modal-tags');
    if(!container) return;

    container.innerHTML = '';
    if(!tags || tags.length === 0) {
        container.innerHTML = '<span class="text-muted">Nenhuma etiqueta.</span>';
        return;
    }

    tags.forEach(nodeTag => {
        const tag = nodeTag.tag || nodeTag;
        if(!tag || !tag.id) return;

        const tagElement = document.createElement('span');
        tagElement.className = 'document-tag';
        tagElement.append(document.createTextNode(tag.name));

        const removeButton = document.createElement('button');
        removeButton.className = 'document-tag-remove';
        removeButton.type = 'button';
        removeButton.title = `Remover etiqueta ${tag.name}`;
        removeButton.setAttribute('aria-label', `Remover etiqueta ${tag.name}`);
        removeButton.innerHTML = '<i class="fa-solid fa-xmark" aria-hidden="true"></i>';
        removeButton.addEventListener('click', () => removeDocumentTag(tag.id));

        tagElement.appendChild(removeButton);
        container.appendChild(tagElement);
    });
}

async function addDocumentTag() {
    const nodeId = document.getElementById('doc-modal-id').value;
    const input = document.getElementById('doc-modal-tag-input');
    const tagName = input.value.trim();
    if(!nodeId || !tagName) return;

    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/tags`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name: tagName })
        });

        if(!response.ok) throw new Error('Não foi possível adicionar a etiqueta.');
        const node = await response.json();
        loadedNodes[nodeId] = node;
        renderDocumentTags(node.tags || []);
        input.value = '';
    } catch(error) {
        alert(error.message);
    }
}

async function removeDocumentTag(tagId) {
    const nodeId = document.getElementById('doc-modal-id').value;
    if(!nodeId || !tagId) return;

    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/tags/${tagId}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });

        if(!response.ok) throw new Error('Não foi possível remover a etiqueta.');
        const node = loadedNodes[nodeId];
        if(node) {
            node.tags = (node.tags || []).filter(nodeTag => (nodeTag.tag || nodeTag).id !== tagId);
            renderDocumentTags(node.tags);
        }
    } catch(error) {
        alert(error.message);
    }
}

function switchModalTab(tab) {
    const btnMeta = document.getElementById('tab-btn-meta');
    const btnFlow = document.getElementById('tab-btn-flow');
    const divMeta = document.getElementById('tab-meta');
    const divFlow = document.getElementById('tab-flow');
    
    if(tab === 'meta') {
        btnMeta.style.borderBottom = '2px solid var(--primary)';
        btnMeta.style.color = '#fff';
        btnFlow.style.borderBottom = '2px solid transparent';
        btnFlow.style.color = 'var(--text-muted)';
        
        divMeta.style.display = 'block';
        divFlow.style.display = 'none';
    } else {
        btnFlow.style.borderBottom = '2px solid var(--primary)';
        btnFlow.style.color = '#fff';
        btnMeta.style.borderBottom = '2px solid transparent';
        btnMeta.style.color = 'var(--text-muted)';
        
        divFlow.style.display = 'block';
        divMeta.style.display = 'none';
    }
}

async function saveMetadata() {
    const nodeId = document.getElementById('doc-modal-id').value;
    const propsStr = document.getElementById('doc-modal-props').value;
    
    let propsObj;
    try {
        propsObj = JSON.parse(propsStr);
    } catch(e) {
        alert("O JSON de propriedades é inválido.");
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/properties`, {
            method: 'PUT',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ properties: propsObj })
        });
        
        if(response.ok) {
            alert('Metadados atualizados com sucesso!');
            // Atualizar o cache local
            if(loadedNodes[nodeId]) {
                loadedNodes[nodeId].properties = propsObj;
            }
        } else {
            alert('Erro ao atualizar metadados.');
        }
    } catch(e) {
        alert('Erro de rede: ' + e);
    }
}

async function uploadDocumentVersion(file) {
    const nodeId = document.getElementById('doc-modal-id').value;
    const versionType = document.getElementById('doc-modal-version-type').value;
    const input = document.getElementById('doc-version-input');
    if(!nodeId || !file) return;

    const formData = new FormData();
    formData.append('file', file);
    formData.append('version_type', versionType);

    try {
        const response = await fetch(`${API_URL}/ecm/nodes/${nodeId}/versions`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });

        const data = await response.json();
        if(!response.ok) throw new Error(data.detail || 'Não foi possível enviar a versão.');

        loadedNodes[nodeId] = data;
        document.getElementById('doc-modal-version').innerText = `${data.major_version}.${data.minor_version}`;
        alert(`Versão ${data.major_version}.${data.minor_version} enviada com sucesso.`);
    } catch(error) {
        alert(error.message);
    } finally {
        input.value = '';
    }
}

async function startWorkflowForDocument() {
    const nodeId = document.getElementById('doc-modal-id').value;
    
    // Obter o ID do primeiro workflow existente
    // Fazemos um GET rapido para pegar um ID de workflow válido
    try {
        const wfResp = await fetch(`${API_URL}/workflows`, { headers: getAuthHeaders() });
        if(!wfResp.ok) throw new Error("Não foi possível listar workflows");
        const wfs = await wfResp.json();
        
        if(wfs.length === 0) {
            alert('Nenhum modelo de Workflow foi criado pelo Administrador no sistema.');
            return;
        }
        
        const targetWf = wfs[0]; // Pega o primeiro (Revisar & Aprovar)
        
        const response = await fetch(`${API_URL}/workflows/instances`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_id: nodeId,
                workflow_id: targetWf.id
            })
        });
        
        if(response.ok) {
            alert(`Processo "${targetWf.name}" iniciado com sucesso! A primeira tarefa foi designada e aparecerá no Dashboard.`);
            document.getElementById('document-modal').style.display = 'none';
        } else {
            const data = await response.json();
            alert('Erro ao iniciar fluxo: ' + (data.detail || ''));
        }
    } catch(e) {
        alert('Erro: ' + e);
    }
}
