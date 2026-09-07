// Logica para Upload de Documentos e Listagem do Workflow
const DOC_TYPES_API = `${API_URL}/ged-config/document-types`;
const DOCS_API = `${API_URL}/documents`;
let currentDocTypes = [];

async function loadDocumentTypesForUpload() {
    try {
        const response = await fetch(DOC_TYPES_API, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        currentDocTypes = await response.json();
        const select = document.getElementById('doc-type-select');
        select.innerHTML = '<option value="">-- Selecione o Tipo --</option>';
        currentDocTypes.forEach(t => {
            if(t.is_active) {
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
            container.innerHTML += `
                <div class="form-group" style="margin-bottom:10px;">
                    <label>${idx.index.name} (${idx.index.type})</label>
                    <input type="text" class="dynamic-index-input" data-index-id="${idx.index.id}" placeholder="Preencha o valor">
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
    document.querySelectorAll('.dynamic-index-input').forEach(input => {
        properties[input.dataset.indexId] = input.value;
    });
    
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
            
            tr.innerHTML = `
                <td>${doc.name}</td>
                <td>${phase}</td>
                <td><span class="badge" style="background:#3b82f6">ECM Node</span></td>
                <td>${created}</td>
                <td>
                    <button class="btn-secondary btn-small">Ver</button>
                    <button class="btn-primary btn-small" onclick="alert('Funcionalidade sendo adaptada para o Workflow Engine!')">Avançar Fluxo</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro', err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadDocumentTypesForUpload();
    loadUserDocuments();
});
