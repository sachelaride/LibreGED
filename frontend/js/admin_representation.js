const REPRESENTATION_API = `${API_URL}/representation-services`;
let selectedRepresentationService = null;

function representationEscape(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
    }[char]));
}

function representationStatus(status) {
    const colors = { PUBLISHED: '#4ade80', DRAFT: '#facc15', ARCHIVED: '#94a3b8' };
    return `<span class="badge" style="background:${colors[status] || '#94a3b8'}">${representationEscape(status)}</span>`;
}

async function loadRepresentationServices() {
    const tbody = document.getElementById('table-representation-services-body');
    try {
        const response = await fetch(REPRESENTATION_API, { headers: getAuthHeaders() });
        if (!response.ok) throw new Error((await response.json()).detail || `HTTP ${response.status}`);
        const services = await response.json();
        tbody.innerHTML = services.length ? services.map(service => `
            <tr style="cursor:pointer" onclick="selectRepresentationService('${service.id}')">
                <td>${representationEscape(service.name)}<br><small>${representationEscape(service.code)}</small></td>
                <td>${representationEscape(service.document_type)}</td>
                <td>${service.is_active ? representationStatus('ATIVO') : representationStatus('INATIVO')}</td>
            </tr>`).join('') :
            '<tr><td colspan="3" style="text-align:center">Nenhum serviço cadastrado.</td></tr>';
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="3" style="color:#ef4444;text-align:center">${representationEscape(error.message)}</td></tr>`;
    }
}

async function selectRepresentationService(serviceId) {
    const services = await (await fetch(REPRESENTATION_API, { headers: getAuthHeaders() })).json();
    selectedRepresentationService = services.find(service => service.id === serviceId);
    if (!selectedRepresentationService) return;
    document.getElementById('representation-selected-name').textContent = selectedRepresentationService.name;
    document.getElementById('btn-new-representation-version').disabled = false;
    loadRepresentationVersions();
}

async function loadRepresentationVersions() {
    const tbody = document.getElementById('table-representation-versions-body');
    if (!selectedRepresentationService) return;
    const response = await fetch(`${REPRESENTATION_API}/${selectedRepresentationService.id}/versions`, { headers: getAuthHeaders() });
    if (!response.ok) {
        tbody.innerHTML = '<tr><td colspan="5" style="color:#ef4444;text-align:center">Erro ao carregar versões.</td></tr>';
        return;
    }
    const versions = await response.json();
    tbody.innerHTML = versions.length ? versions.map(version => `
        <tr>
            <td>${representationEscape(version.version_label)}</td>
            <td>r${version.revision}</td>
            <td title="${representationEscape(version.content_hash)}">${representationEscape(version.content_hash.slice(0, 12))}...</td>
            <td>${representationStatus(version.status)}</td>
            <td>${version.status !== 'PUBLISHED' ? `<button class="btn-secondary btn-small" onclick="publishRepresentationVersion('${version.id}')">Publicar</button>` : 'Em uso'}</td>
        </tr>`).join('') :
        '<tr><td colspan="5" style="text-align:center">Nenhuma versão cadastrada.</td></tr>';
}

function openRepresentationServiceModal() {
    ['representation-code', 'representation-name'].forEach(id => document.getElementById(id).value = '');
    document.getElementById('representation-document-type').value = 'diploma';
    document.getElementById('modal-representation-service').classList.add('active');
}

function openRepresentationVersionModal() {
    if (!selectedRepresentationService) return;
    document.getElementById('representation-version-label').value = '';
    document.getElementById('representation-xslt-content').value = '';
    document.getElementById('representation-xslt-file').value = '';
    document.getElementById('modal-representation-version').classList.add('active');
}

function closeRepresentationModal(id) {
    document.getElementById(id).classList.remove('active');
}

async function saveRepresentationService() {
    const payload = {
        code: document.getElementById('representation-code').value.trim(),
        name: document.getElementById('representation-name').value.trim(),
        document_type: document.getElementById('representation-document-type').value
    };
    if (!payload.code || !payload.name) return alert('Informe o código e o nome do serviço.');
    const response = await fetch(REPRESENTATION_API, {
        method: 'POST', headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    if (!response.ok) return alert((await response.json()).detail || 'Erro ao criar serviço.');
    closeRepresentationModal('modal-representation-service');
    await loadRepresentationServices();
}

async function saveRepresentationVersion() {
    if (!selectedRepresentationService) return;
    const label = document.getElementById('representation-version-label').value.trim();
    const file = document.getElementById('representation-xslt-file').files[0];
    const content = document.getElementById('representation-xslt-content').value;
    if (!label || (!file && !content)) return alert('Informe a versão e o XSLT.');
    let response;
    if (file) {
        const form = new FormData();
        form.append('file', file);
        response = await fetch(`${REPRESENTATION_API}/${selectedRepresentationService.id}/versions/upload?version_label=${encodeURIComponent(label)}`, {
            method: 'POST', headers: getAuthHeaders(), body: form
        });
    } else {
        response = await fetch(`${REPRESENTATION_API}/${selectedRepresentationService.id}/versions`, {
            method: 'POST', headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ version_label: label, xslt_content: content })
        });
    }
    if (!response.ok) return alert((await response.json()).detail || 'Erro ao salvar versão.');
    closeRepresentationModal('modal-representation-version');
    await loadRepresentationVersions();
}

async function publishRepresentationVersion(versionId) {
    if (!confirm('Publicar esta versão? A versão atualmente publicada será arquivada.')) return;
    const response = await fetch(`${REPRESENTATION_API}/${selectedRepresentationService.id}/versions/${versionId}/publish`, {
        method: 'POST', headers: getAuthHeaders()
    });
    if (!response.ok) return alert((await response.json()).detail || 'Erro ao publicar versão.');
    await loadRepresentationVersions();
}
