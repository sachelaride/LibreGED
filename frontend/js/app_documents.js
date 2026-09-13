// Logica para Upload de Documentos e Listagem do Workflow
const DOC_TYPES_API = `${API_URL}/ged-config/document-types`;
const DOCS_API = `${API_URL}/documents`;
const PERMISSIONS_API = `${API_URL}/users/me/document-permissions`;
let currentDocTypes = [];
let myPermissions = { is_admin_global: false, vinculos: [] };

async function loadDocumentTypesForUpload() {
    try {
        const response = await fetch(DOC_TYPES_API, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        currentDocTypes = await response.json();
        const select = document.getElementById('doc-type-select');
        select.innerHTML = '<option value="">-- Selecione o Tipo --</option>';
        currentDocTypes.forEach(t => {
            if(t.is_active && hasPermission(t.id, 'cadastrar')) {
                const opt = document.createElement('option');
                opt.value = t.id;
                opt.innerText = t.name;
                select.appendChild(opt);
            }
        });
    } catch (err) {
        console.error('Erro ao carregar tipos de documento', err);
    }
}

async function loadMyPermissions() {
    try {
        const response = await fetch(PERMISSIONS_API, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        if (response.ok) {
            myPermissions = await response.json();
        }
    } catch (err) {
        console.error('Erro ao carregar permissões', err);
    }
}

function hasPermission(typeId, action) {
    if (myPermissions.is_admin_global) return true;
    const vinculo = myPermissions.vinculos.find(v => v.document_type_id === typeId);
    return vinculo && vinculo.permissions.includes(action);
}

function loadIndicesForType() {
    const typeId = document.getElementById('doc-type-select').value;
    const container = document.getElementById('dynamic-indices-container');
    container.innerHTML = '<h4>Índices Requeridos</h4>';
    
    if(!typeId) {
        container.innerHTML = '<h4 style="color:#aaa;">Selecione um Tipo para ver os Índices</h4>';
        return;
    }
    
    const docType = currentDocTypes.find(t => t.id === typeId);
    if(docType && docType.indices) {
        docType.indices.forEach(idx => {
            const index = idx.index;
            const requiredAttr = idx.is_required ? 'required' : '';
            const requiredLabel = idx.is_required ? ' *' : '';
            const maskPattern = index.mask ? `pattern="${index.mask}"` : '';
            const readOnlyAttr = index.auto_increment ? 'readonly placeholder="Gerado automaticamente"' : 'placeholder="Preencha o valor"';
            
            let inputHtml = '';
            
            if (index.type.toLowerCase() === 'lista' || index.type.toLowerCase() === 'list') {
                let optionsHtml = '<option value="">-- Selecione --</option>';
                if (index.options && Array.isArray(index.options)) {
                    index.options.forEach(opt => {
                        optionsHtml += `<option value="${opt}">${opt}</option>`;
                    });
                }
                inputHtml = `<select class="dynamic-index-input form-control" data-index-id="${index.id}" data-type="lista" ${requiredAttr}>${optionsHtml}</select>`;
            } else if (index.type.toLowerCase() === 'booleano' || index.type.toLowerCase() === 'boolean') {
                inputHtml = `<input type="checkbox" class="dynamic-index-input" data-index-id="${index.id}" data-type="booleano" style="width:auto;"> <small>Sim/Não</small>`;
            } else if (index.type.toLowerCase() === 'data' || index.type.toLowerCase() === 'date') {
                inputHtml = `<input type="date" class="dynamic-index-input form-control" data-index-id="${index.id}" data-type="data" ${requiredAttr} ${readOnlyAttr}>`;
            } else if (index.type.toLowerCase() === 'número' || index.type.toLowerCase() === 'numero' || index.type.toLowerCase() === 'number') {
                inputHtml = `<input type="number" step="any" class="dynamic-index-input form-control" data-index-id="${index.id}" data-type="numero" ${requiredAttr} ${readOnlyAttr}>`;
            } else {
                inputHtml = `<input type="text" class="dynamic-index-input form-control" data-index-id="${index.id}" data-type="texto" ${maskPattern} ${requiredAttr} ${readOnlyAttr} title="Máscara: ${index.mask || ''}">`;
            }
            
            container.innerHTML += `
                <div class="form-group" style="margin-bottom:10px;">
                    <label>${index.name} (${index.type})${requiredLabel}</label>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        ${inputHtml}
                    </div>
                </div>
            `;
        });
    }
}

async function uploadDocument() {
    const title = document.getElementById('doc-title').value;
    const typeId = document.getElementById('doc-type-select').value;
    const fileInput = document.getElementById('doc-file');
    
    if(!title || !typeId || !fileInput.files[0]) {
        alert("Preencha título, tipo e selecione um arquivo.");
        return;
    }
    
    // Coletar propriedades para o ECM
    const properties = {};
    let hasValidationError = false;

    document.querySelectorAll('.dynamic-index-input').forEach(input => {
        let value = input.value;
        if (input.dataset.type === 'booleano') {
            value = input.checked ? 'true' : 'false';
        }
        
        if (input.hasAttribute('required') && !value && !input.readOnly) {
            hasValidationError = true;
            input.style.borderColor = 'red';
        } else {
            input.style.borderColor = '';
        }

        properties[input.dataset.indexId] = value;
    });

    if (hasValidationError) {
        alert("Preencha todos os campos obrigatórios (*).");
        return;
    }
    
    // Buscar o node_type correspondente (para manter o nome do tipo)
    const docType = currentDocTypes.find(t => t.id === typeId);
    const nodeTypeName = docType ? docType.name : "ies:documento";

    const formData = new FormData();
    formData.append("name", title);
    formData.append("node_type", nodeTypeName);
    formData.append("properties", JSON.stringify(properties));
    formData.append("file", fileInput.files[0]);
    
    try {
        const response = await fetch(`${API_URL}/ecm/nodes/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` },
            body: formData
        });
        
        if(response.ok) {
            alert('Documento enviado ao ECM com sucesso!');
            // Reset
            document.getElementById('doc-title').value = '';
            document.getElementById('doc-file').value = '';
            document.getElementById('dynamic-indices-container').innerHTML = '';
            document.getElementById('doc-type-select').value = '';
            
            // Recarregar a lista
            loadUserDocuments();
        } else {
            alert('Erro ao enviar documento.');
        }
    } catch(err) {
        console.error(err);
        alert('Erro de conexão ao fazer upload.');
    }
}

async function loadUserDocuments() {
    try {
        const response = await fetch(`${API_URL}/ecm/nodes`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        const docs = await response.json();
        
        const tbody = document.getElementById('table-documents-body');
        tbody.innerHTML = '';
        
        if (docs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Nenhum documento no workflow.</td></tr>';
            return;
        }
        
        docs.forEach(doc => {
            const tr = document.createElement('tr');
            const created = new Date(doc.created_at).toLocaleDateString();
            const phase = doc.properties['ies:codigo_serie'] || doc.node_type;
            
            // Descobrir o ID do tipo documental pelo nome
            const docType = currentDocTypes.find(t => t.name === doc.node_type || t.id === doc.node_type);
            const typeId = docType ? docType.id : null;
            
            const podeVer = typeId ? hasPermission(typeId, 'consultar') : true;
            const podeExecutarFluxo = typeId ? hasPermission(typeId, 'executar_fluxo') : true;
            
            let btnVer = podeVer ? `<button class="btn-secondary btn-small">Ver</button>` : '';
            let btnFluxo = podeExecutarFluxo ? `<button class="btn-primary btn-small" onclick="alert('Funcionalidade sendo adaptada para o Workflow Engine!')">Avançar Fluxo</button>` : '';
            
            tr.innerHTML = `
                <td>${doc.name}</td>
                <td>${phase}</td>
                <td><span class="badge" style="background:#3b82f6">ECM Node</span></td>
                <td>${created}</td>
                <td>
                    ${btnVer}
                    ${btnFluxo}
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro', err);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadMyPermissions();
    await loadDocumentTypesForUpload();
    loadUserDocuments();
});
