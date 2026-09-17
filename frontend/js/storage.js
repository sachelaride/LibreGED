async function loadStorageRules() {
    const tbody = document.getElementById('table-rules-body');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/storage-rules`, {
            headers: getAuthHeaders()
        });
        if(!response.ok) throw new Error("Erro ao carregar regras de armazenamento");
        
        const rawData = await response.json();
        const rules = rawData.items ? rawData.items : rawData;
        window.storageRulesData = rules;
        tbody.innerHTML = '';
        
        if(!rules || rules.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">Nenhuma regra cadastrada</td></tr>';
            return;
        }

        rules.forEach(rule => {
            const tr = document.createElement('tr');
            const isActive = rule.is_active ? '<span class="badge success">ATIVA</span>' : '<span class="badge warning">INATIVA</span>';
            const dupText = rule.enable_duplication ? `<span style="color:#10b981;">Sim (${rule.secondary_storage_type})</span>` : '<span style="color:#ef4444;">Não</span>';
            const docTypeText = rule.document_type_id ? "Vinculado" : "Geral"; // We can fetch actual names later
            
            tr.innerHTML = `
                <td><strong>${rule.name}</strong></td>
                <td>${docTypeText}</td>
                <td>${rule.storage_type}</td>
                <td>${rule.base_path}</td>
                <td>${dupText}</td>
                <td>${isActive}</td>
                <td>
                    <button class="btn-secondary btn-small" onclick="editStorageRule('${rule.id}')">Editar</button>
                    <button class="btn-secondary btn-small" onclick="deleteStorageRule('${rule.id}')" style="background:#ef4444;border-color:#ef4444;">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="7" style="color:#fbbf24">${error.message}</td></tr>`;
    }
}

async function openStorageRuleModal() {
    document.getElementById('rule-id').value = '';
    document.getElementById('rule-name').value = '';
    document.getElementById('rule-document-type').value = '';
    document.getElementById('rule-storage-type').value = 'Local';
    document.getElementById('rule-base-path').value = '';
    
    // Clear credentials
    document.getElementById('rule-network-domain').value = '';
    document.getElementById('rule-network-user').value = '';
    document.getElementById('rule-network-password').value = '';
    
    document.getElementById('rule-enable-duplication').checked = false;
    document.getElementById('rule-secondary-type').value = 'S3';
    document.getElementById('rule-secondary-path').value = '';
    document.getElementById('rule-max-files').value = '10000';
    document.getElementById('rule-max-gb').value = '100.0';
    
    toggleDuplicationFields();
    toggleCredentialFields();
    
    // Carregar tipos de documento para o datalist
    try {
        const response = await fetch(`${API_URL}/document-types`, { headers: getAuthHeaders() });
        if (response.ok) {
            const rawData = await response.json();
            const types = rawData.items ? rawData.items : rawData;
            const datalist = document.getElementById('doc-types-list');
            datalist.innerHTML = ''; // Limpar datalist
            window.availableDocTypes = types; // Armazenar para recuperar ID depois
            types.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.name;
                opt.dataset.id = t.id;
                datalist.appendChild(opt);
            });
        }
    } catch(e) {
        console.error("Erro ao carregar tipos de documento:", e);
    }
    
    document.getElementById('modal-storage-rule').classList.add('active');
}

function toggleCredentialFields() {
    const type = document.getElementById('rule-storage-type').value;
    const credBox = document.getElementById('credential-fields');
    const groupDomain = document.getElementById('group-domain');
    const lblDomain = document.getElementById('lbl-domain');
    const lblUser = document.getElementById('lbl-user');
    const lblPass = document.getElementById('lbl-pass');
    
    credBox.style.display = 'block';
    groupDomain.style.display = 'none';
    
    if (type === 'S3' || type === 'Glacier') {
        groupDomain.style.display = 'block';
        lblDomain.innerText = 'Região (ex: us-east-1)';
        lblUser.innerText = 'Access Key ID';
        lblPass.innerText = 'Secret Access Key';
    } else if (type === 'Google') {
        lblUser.innerText = 'Service Account Email';
        lblPass.innerText = 'JSON Key Content';
    } else if (type === 'Azure') {
        lblUser.innerText = 'Account Name';
        lblPass.innerText = 'Account Key / SAS Token';
    } else if (type === 'SharePoint') {
        groupDomain.style.display = 'block';
        lblDomain.innerText = 'Tenant ID';
        lblUser.innerText = 'Client ID';
        lblPass.innerText = 'Client Secret';
    } else if (type === 'FTP' || type === 'SMB' || type === 'NFS') {
        if (type === 'SMB') {
            groupDomain.style.display = 'block';
            lblDomain.innerText = 'Domínio (opcional)';
        }
        lblUser.innerText = 'Usuário';
        lblPass.innerText = 'Senha';
    } else {
        credBox.style.display = 'none';
    }
}

function toggleDuplicationFields() {
    const isChecked = document.getElementById('rule-enable-duplication').checked;
    document.getElementById('duplication-fields').style.display = isChecked ? 'block' : 'none';
}

function suggestPathBasedOnType() {
    const input = document.getElementById('rule-document-type');
    const selectedText = input.value;
    const pathInput = document.getElementById('rule-base-path');
    const nameInput = document.getElementById('rule-name');
    
    if (selectedText) {
        if (!nameInput.value) {
            nameInput.value = `Regra - ${selectedText}`;
        }
        
        const cleanName = selectedText.toLowerCase().replace(/[^a-z0-9]/g, '_');
        
        // Suggest a base path if empty or if we want to overwrite
        if (!pathInput.value || pathInput.value.includes('/var/lib/ged/')) {
            const storageType = document.getElementById('rule-storage-type').value;
            if (storageType === 'Local') {
                pathInput.value = `/var/lib/ged/docs/${cleanName}`;
            } else if (storageType === 'S3') {
                pathInput.value = `s3://meubucket/${cleanName}`;
            }
        }
    }
}

// Add event listener to storage type to auto-update suggested path prefix
document.addEventListener('DOMContentLoaded', () => {
    const typeSelect = document.getElementById('rule-storage-type');
    if(typeSelect) {
        typeSelect.addEventListener('change', suggestPathBasedOnType);
    }
});

async function saveStorageRule() {
    const name = document.getElementById('rule-name').value;
    const document_type_input = document.getElementById('rule-document-type').value;
    
    // Find ID if it exists in the datalist
    let document_type_id = null;
    let document_type_name = document_type_input || null;
    
    if(window.availableDocTypes && document_type_input) {
        const found = window.availableDocTypes.find(t => t.name === document_type_input);
        if(found) {
            document_type_id = found.id;
            document_type_name = null; // already exists, send ID
        }
    }

    const storage_type = document.getElementById('rule-storage-type').value;
    const base_path = document.getElementById('rule-base-path').value;
    
    // Credentials
    const network_domain = document.getElementById('rule-network-domain').value || null;
    const network_user = document.getElementById('rule-network-user').value || null;
    const network_password = document.getElementById('rule-network-password').value || null;

    const enable_duplication = document.getElementById('rule-enable-duplication').checked;
    const secondary_storage_type = enable_duplication ? document.getElementById('rule-secondary-type').value : null;
    const secondary_base_path = enable_duplication ? document.getElementById('rule-secondary-path').value : null;
    const max_files_per_folder = parseInt(document.getElementById('rule-max-files').value) || 10000;
    const max_gb_per_folder = parseFloat(document.getElementById('rule-max-gb').value) || 100.0;
    
    if(!name || !base_path) {
        return alert("Preencha o nome e o caminho base.");
    }
    
    if (enable_duplication && !secondary_base_path) {
        return alert("Preencha o caminho secundário (backup).");
    }
    
    const rule_id = document.getElementById('rule-id').value;
    const method = rule_id ? 'PUT' : 'POST';
    const url = rule_id ? `${API_URL}/storage-rules/${rule_id}` : `${API_URL}/storage-rules`;
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                document_type_id,
                document_type_name,
                storage_type,
                base_path,
                network_domain,
                network_user,
                network_password,
                enable_duplication,
                secondary_storage_type,
                secondary_base_path,
                max_files_per_folder,
                max_gb_per_folder,
                is_active: true
            })
        });
        
        if(response.ok) {
            document.getElementById('modal-storage-rule').classList.remove('active');
            loadStorageRules();
        } else {
            const err = await response.json();
            alert("Erro ao salvar regra: " + (err.detail || ""));
        }
    } catch(e) {
        alert(e.message);
    }
}

async function editStorageRule(idOrObj) {
    const rule = typeof idOrObj === 'string' ? window.storageRulesData.find(r => r.id === idOrObj) : idOrObj;
    if(!rule) return;
    await openStorageRuleModal();
    
    document.getElementById('rule-id').value = rule.id;
    document.getElementById('rule-name').value = rule.name;
    document.getElementById('rule-storage-type').value = rule.storage_type;
    document.getElementById('rule-base-path').value = rule.base_path;
    
    document.getElementById('rule-network-domain').value = rule.network_domain || '';
    document.getElementById('rule-network-user').value = rule.network_user || '';
    // do not populate password for security
    
    document.getElementById('rule-enable-duplication').checked = rule.enable_duplication;
    if(rule.enable_duplication) {
        document.getElementById('rule-secondary-type').value = rule.secondary_storage_type;
        document.getElementById('rule-secondary-path').value = rule.secondary_base_path;
    }
    document.getElementById('rule-max-files').value = rule.max_files_per_folder || 10000;
    document.getElementById('rule-max-gb').value = rule.max_gb_per_folder || 100.0;
    
    toggleDuplicationFields();
    toggleCredentialFields();
}

async function deleteStorageRule(id) {
    if(!confirm("Tem certeza que deseja excluir esta regra de armazenamento? Ela não poderá ser excluída se já houver documentos salvos nela.")) return;
    
    try {
        const response = await fetch(`${API_URL}/storage-rules/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        
        if(response.ok || response.status === 204) {
            alert('Regra excluída com sucesso.');
            loadStorageRules();
        } else {
            const err = await response.json();
            alert("Erro ao excluir regra: " + (err.detail || ""));
        }
    } catch(e) {
        alert("Erro de conexão.");
    }
}
