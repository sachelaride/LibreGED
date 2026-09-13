// admin_signers.js
async function loadSigners() {
    try {
        const res = await fetch(`${API_URL}/signers`, { headers: getAuthHeaders() });
        if(!res.ok) throw new Error('Falha ao carregar signatários');
        const signers = await res.json();
        
        const tbody = document.getElementById('table-signers-body');
        tbody.innerHTML = '';
        
        if (signers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Nenhum signatário cadastrado.</td></tr>';
            return;
        }
        
        signers.forEach(sig => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-size:12px; font-family:monospace;">${sig.id.substring(0,8)}</td>
                <td><strong>${sig.name}</strong></td>
                <td>${sig.role}</td>
                <td>${sig.cpf}</td>
                <td>
                    <button class="btn-danger btn-small" style="background:#ef4444; border:none; padding:5px; border-radius:4px; color:white; cursor:pointer;" onclick="deleteSigner('${sig.id}')">Inativar</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch(e) {
        console.error(e);
        alert('Erro ao carregar cofre de assinaturas');
    }
}

function openSignerModal() {
    document.getElementById('sig-name').value = '';
    document.getElementById('sig-role').value = '';
    document.getElementById('sig-cpf').value = '';
    document.getElementById('sig-p12').value = '';
    document.getElementById('modal-signer').classList.add('active');
}

async function saveSigner() {
    const name = document.getElementById('sig-name').value;
    const role = document.getElementById('sig-role').value;
    const cpf = document.getElementById('sig-cpf').value;
    const fileInput = document.getElementById('sig-p12');
    
    if(!name || !role || !cpf || fileInput.files.length === 0) {
        alert("Preencha todos os campos e anexe o certificado .p12");
        return;
    }
    
    const formData = new FormData();
    formData.append('name', name);
    formData.append('role', role);
    formData.append('cpf', cpf);
    formData.append('p12_file', fileInput.files[0]);
    
    try {
        // Exibir loading
        document.getElementById('btn-save-signer').disabled = true;
        document.getElementById('btn-save-signer').innerText = 'Enviando ao Cofre...';
        
        const res = await fetch(`${API_URL}/signers`, {
            method: 'POST',
            headers: {
                'Authorization': getAuthHeaders()['Authorization']
            },
            body: formData
        });
        
        if(!res.ok) throw new Error('Erro ao salvar no cofre');
        
        document.getElementById('modal-signer').classList.remove('active');
        loadSigners();
    } catch(e) {
        alert(e);
    } finally {
        document.getElementById('btn-save-signer').disabled = false;
        document.getElementById('btn-save-signer').innerText = 'Salvar e Guardar no Cofre Seguro';
    }
}

function deleteSigner(id) {
    alert("Inativação será implementada futuramente. ID: " + id);
}

// Hook into the main view switcher
const originalSwitchView = window.switchView;
window.switchView = function(target) {
    if (originalSwitchView) {
        originalSwitchView(target);
    }
    if (target === 'signers') {
        loadSigners();
    }
};
