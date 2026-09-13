// JS para gestão de Templates RVDD (Baseado no fluxo dinâmico)
const TEMPLATES_API = `${API_URL}/templates`;

async function loadTemplates() {
    try {
        const response = await fetch(TEMPLATES_API, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        const rawData = await response.json();
        const templates = rawData.items ? rawData.items : rawData;
        
        const tbody = document.getElementById('table-templates-body');
        tbody.innerHTML = '';
        
        if (templates.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center">Nenhum template cadastrado.</td></tr>';
            return;
        }
        
        templates.forEach(t => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${t.name}</td>
                <td><span class="badge" style="background: ${t.is_active ? '#4ade80' : '#ef4444'}">${t.is_active ? 'Ativo' : 'Inativo'}</span></td>
                <td>
                    <button class="btn-secondary btn-small" onclick="editTemplate('${t.id}', '${t.name}', \`${btoa(t.html_content)}\`)">Editar</button>
                    <button class="btn-secondary btn-small" onclick="deleteTemplate('${t.id}')" style="background:#ef4444;border-color:#ef4444;">Excluir</button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error('Erro ao carregar templates', err);
    }
}

function openTemplateModal() {
    document.getElementById('tpl-name').value = '';
    document.getElementById('tpl-html').value = '<html>\n<body>\n  <h1>Diploma de {{ nome_aluno }}</h1>\n</body>\n</html>';
    // Clear ID for new
    document.getElementById('modal-template').dataset.id = '';
    document.getElementById('modal-template').classList.add('active');
}

function editTemplate(id, name, htmlBase64) {
    document.getElementById('tpl-name').value = name;
    document.getElementById('tpl-html').value = atob(htmlBase64);
    document.getElementById('modal-template').dataset.id = id;
    document.getElementById('modal-template').classList.add('active');
}

async function saveTemplate() {
    const name = document.getElementById('tpl-name').value;
    const html_content = document.getElementById('tpl-html').value;
    const id = document.getElementById('modal-template').dataset.id;
    
    if (!name || !html_content) {
        alert('Preencha o nome e o código HTML.');
        return;
    }
    
    const payload = { name, html_content, is_active: true };
    const method = id ? 'PUT' : 'POST';
    const url = id ? `${TEMPLATES_API}/${id}` : TEMPLATES_API;
    
    try {
        const response = await fetch(url, {
            method: method,
            headers: { 
                'Authorization': `Bearer ${localStorage.getItem('ged_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            document.getElementById('modal-template').classList.remove('active');
            loadTemplates();
        } else {
            alert('Erro ao salvar template.');
        }
    } catch (err) {
        alert('Erro de conexão.');
    }
}

async function deleteTemplate(id) {
    if(!confirm("Tem certeza que deseja excluir este template?")) return;
    try {
        const response = await fetch(`${TEMPLATES_API}/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('ged_token')}` }
        });
        
        if (response.ok || response.status === 204) {
            loadTemplates();
        } else {
            const err = await response.json();
            alert("Erro ao excluir template: " + (err.detail || ""));
        }
    } catch (err) {
        alert("Erro de conexão.");
    }
}

// Inicializar carregamento quando a view é mostrada
document.addEventListener('DOMContentLoaded', () => {
    // Escutar se o menu Templates foi clicado para carregar dados
    const menus = document.querySelectorAll('.sidebar-nav li');
    menus.forEach(menu => {
        menu.addEventListener('click', () => {
            if (menu.innerText.includes('Templates')) {
                loadTemplates();
            }
        });
    });
});
