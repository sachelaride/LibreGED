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
    
    // Coletar indices
    const indices = [];
    document.querySelectorAll('.dynamic-index-input').forEach(input => {
        indices.push({
            index_id: input.dataset.indexId,
            value: input.value
        });
    });
    
    const formData = new FormData();
    formData.append("title", title);
    formData.append("document_type_id", typeId);
    formData.append("indices_json", JSON.stringify(indices));
    formData.append("file", fileInput.files[0]);
    
    try {
        const response = await fetch(`${DOCS_API}/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` },
            body: formData
        });
        
        if(response.ok) {
            alert('Documento enviado e inserido no Workflow com sucesso!');
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
        // Para simplificar, vou bater na rota de upload existente na API antiga
        // Em um cenario ideal, criaremos um GET /api/documents na nova esteira
        const response = await fetch(`${API_URL}/ged/documents`, {
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
            tr.innerHTML = `
                <td>${doc.title}</td>
                <td>--</td>
                <td><span class="badge" style="background:#f59e0b">${doc.status}</span></td>
                <td>${new Date(doc.created_at).toLocaleDateString()}</td>
                <td>
                    <button class="btn-secondary btn-small">Ver</button>
                    <button class="btn-primary btn-small">Avançar Fluxo</button>
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
