// app_signature.js

async function populateSignersDropdown() {
    try {
        const res = await fetch(`${API_URL}/signers`, { headers: getAuthHeaders() });
        if(res.ok) {
            const signers = await res.json();
            const select = document.getElementById('doc-modal-signer-select');
            select.innerHTML = '<option value="">-- Selecione o Signatário --</option>';
            signers.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.text = `${s.name} (${s.role} - CPF: ${s.cpf})`;
                select.appendChild(opt);
            });
        }
    } catch(e) {
        console.error("Erro ao carregar signatários no dropdown", e);
    }
}

async function loadSignatureLogs() {
    const docId = document.getElementById('doc-modal-id').value;
    if(!docId) return;
    
    try {
        const res = await fetch(`${API_URL}/documents/${docId}/signatures`, { headers: getAuthHeaders() });
        const tbody = document.getElementById('table-signature-logs');
        tbody.innerHTML = '';
        
        if(res.ok) {
            const logs = await res.json();
            if(logs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Nenhuma assinatura digital encontrada.</td></tr>';
                return;
            }
            
            logs.forEach(log => {
                const tr = document.createElement('tr');
                let statusBadge = log.status === 'SUCCESS' ? '<span style="color:#4ade80; font-weight:bold;">VÁLIDO</span>' : `<span style="color:#ef4444; font-weight:bold;">${log.status}</span>`;
                tr.innerHTML = `
                    <td style="font-size:11px;">${new Date(log.created_at).toLocaleString()}</td>
                    <td><strong>${log.signature_type}</strong></td>
                    <td style="font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width: 150px;" title="${log.certificate_subject}">${log.certificate_subject || '-'}</td>
                    <td>${statusBadge}</td>
                `;
                tbody.appendChild(tr);
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center">Erro ao carregar auditoria.</td></tr>';
        }
    } catch(e) {
        console.error(e);
    }
}

async function signDocument() {
    const docId = document.getElementById('doc-modal-id').value;
    const signerId = document.getElementById('doc-modal-signer-select').value;
    const password = document.getElementById('doc-modal-signer-pass').value;
    const comments = document.getElementById('doc-modal-signer-comments').value;
    
    if(!signerId || !password) {
        alert('Selecione um signatário e insira a senha do cofre.');
        return;
    }
    
    const btn = document.getElementById('btn-sign-document');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processando Criptografia...';
    
    try {
        const res = await fetch(`${API_URL}/documents/${docId}/sign`, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                signer_id: signerId,
                password: password,
                comments: comments || "Assinatura Digital ICP-Brasil"
            })
        });
        
        if(res.ok) {
            const data = await res.json();
            alert(`Sucesso! Documento assinado via ${data.type}`);
            document.getElementById('doc-modal-signer-pass').value = '';
            
            // Reload logs and UI
            loadSignatureLogs();
            if (typeof loadLibrary === 'function' && currentFolderId) {
                loadLibrary(currentFolderId);
            }
        } else {
            const err = await res.json();
            alert(`Falha na Assinatura: ${err.detail || 'Erro desconhecido.'}`);
        }
    } catch(e) {
        alert(`Erro de conexão: ${e.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-file-signature"></i> Assinar ICP-Brasil';
    }
}

// Hook into modal opening to fetch data
const originalOpenDocModal = window.openDocumentModal;
window.openDocumentModal = function(id, title, props, version, status) {
    if(originalOpenDocModal) originalOpenDocModal(id, title, props, version, status);
    
    // We populate the dropdown just once or on every open
    populateSignersDropdown();
    
    // We load the signature logs
    setTimeout(() => {
        loadSignatureLogs();
    }, 100);
}

// Hook into tab switching
const originalSwitchModalTab = window.switchModalTab;
window.switchModalTab = function(tabName) {
    if(originalSwitchModalTab) originalSwitchModalTab(tabName);
    
    // Custom tab handling
    document.getElementById('tab-btn-meta').style.borderColor = tabName === 'meta' ? 'var(--primary)' : 'transparent';
    document.getElementById('tab-btn-meta').style.color = tabName === 'meta' ? '#fff' : 'var(--text-muted)';
    
    document.getElementById('tab-btn-flow').style.borderColor = tabName === 'flow' ? 'var(--primary)' : 'transparent';
    document.getElementById('tab-btn-flow').style.color = tabName === 'flow' ? '#fff' : 'var(--text-muted)';
    
    const sigBtn = document.getElementById('tab-btn-sig');
    if(sigBtn) {
        sigBtn.style.borderColor = tabName === 'sig' ? 'var(--primary)' : 'transparent';
        sigBtn.style.color = tabName === 'sig' ? '#fff' : 'var(--text-muted)';
    }
    
    document.getElementById('tab-meta').style.display = tabName === 'meta' ? 'block' : 'none';
    document.getElementById('tab-flow').style.display = tabName === 'flow' ? 'block' : 'none';
    const tabSig = document.getElementById('tab-sig');
    if(tabSig) {
        tabSig.style.display = tabName === 'sig' ? 'block' : 'none';
    }
}
