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
        
        if(results.length === 0) {
            resultsContainer.innerHTML = '<p class="text-muted" style="text-align:center;">Nenhum documento encontrado.</p>';
            return;
        }

        let html = '<div style="display:grid; gap:15px;">';
        results.forEach(doc => {
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

// --- Dossiê Acadêmico ---
function createDossier() {
    const name = document.getElementById('student-name').value;
    const cpf = document.getElementById('student-cpf').value;
    
    if(!name || !cpf) {
        alert("Nome e CPF são obrigatórios para iniciar o Dossiê.");
        return;
    }

    // Libera a zona de upload
    const uploadZone = document.getElementById('upload-zone');
    uploadZone.style.opacity = '1';
    uploadZone.style.pointerEvents = 'auto';
    
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

function handleFiles(files) {
    if(files.length === 0) return;
    
    // Dummy handler for UI
    alert(`${files.length} arquivo(s) selecionado(s). Iniciando upload para o fluxo do Dossiê... (Em desenvolvimento)`);
    
    // Here we would use FormData to POST /api/documents/upload
}
