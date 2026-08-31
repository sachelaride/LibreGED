const API_URL = 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', () => {
    // Check Authentication state on load
    checkAuth();

    // Login Form Submit
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const user = document.getElementById('login-username').value;
        const pass = document.getElementById('login-password').value;
        const btn = document.getElementById('btn-login');
        const errorMsg = document.getElementById('login-error');
        
        btn.innerText = 'Autenticando...';
        btn.disabled = true;
        errorMsg.innerText = '';
        
        try {
            const formData = new URLSearchParams();
            formData.append('username', user);
            formData.append('password', pass);
            
            const response = await fetch(`${API_URL}/auth/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error("Usuário ou senha incorretos");
            }
            
            const data = await response.json();
            localStorage.setItem('ged_token', data.access_token);
            
            // Login Success
            checkAuth();
            
        } catch (error) {
            errorMsg.innerText = error.message;
            const card = document.querySelector('.login-card');
            card.classList.remove('shake');
            void card.offsetWidth; // trigger reflow
            card.classList.add('shake');
        } finally {
            btn.innerText = 'Entrar no Sistema';
            btn.disabled = false;
        }
    });

    // Logout
    document.getElementById('btn-logout').addEventListener('click', () => {
        localStorage.removeItem('ged_token');
        checkAuth();
    });

    // Navigational Logic
    const menuItems = document.querySelectorAll('.menu-item');
    const views = document.querySelectorAll('.view:not(.login-view)');

    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            
            menuItems.forEach(m => m.classList.remove('active'));
            views.forEach(v => v.classList.remove('active'));
            
            item.classList.add('active');
            
            const target = item.getAttribute('data-target');
            document.getElementById(`view-${target}`).classList.add('active');
            document.getElementById('page-title').innerText = item.innerText;
            
            if(target === 'documentos') {
                loadDocuments();
            }
        });
    });

    document.getElementById('btn-load-docs').addEventListener('click', loadDocuments);
    const filterModality = document.getElementById('filter-modality');
    if (filterModality) {
        filterModality.addEventListener('change', renderDocumentsTable);
    }

    document.getElementById('btn-close-modal').addEventListener('click', () => {
        document.getElementById('modal-rvdd').classList.remove('active');
        document.getElementById('rvdd-frame').src = '';
    });
});

function getAuthHeaders() {
    const token = localStorage.getItem('ged_token');
    return {
        'Authorization': `Bearer ${token}`
    };
}

function parseJwt(token) {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch(e) {
        return null;
    }
}

function checkAuth() {
    const token = localStorage.getItem('ged_token');
    if (!token) {
        // Not logged in
        document.getElementById('view-login').style.display = 'flex';
        document.getElementById('main-sidebar').style.display = 'none';
        document.getElementById('main-content').style.display = 'none';
    } else {
        // Logged in
        const payload = parseJwt(token);
        if (payload) {
            // Update UI with user data
            const userLabel = document.getElementById('sidebar-username') || createSidebarUserLabel();
            userLabel.innerHTML = `<span>Olá, ${payload.sub}</span><small style="display:block; font-size:10px; color:#a0aec0;">${payload.role}</small>`;
            
            // Hide admin options if not admin_global
            const cfgMenu = document.querySelector('[data-target="configuracoes"]');
            if (cfgMenu) {
                if (payload.role !== "admin_global") {
                    cfgMenu.style.display = "none";
                } else {
                    cfgMenu.style.display = "flex";
                }
            }
        }
        
        document.getElementById('view-login').style.display = 'none';
        document.getElementById('main-sidebar').style.display = 'flex';
        document.getElementById('main-content').style.display = 'flex';
    }
}

function createSidebarUserLabel() {
    const label = document.createElement('div');
    label.id = 'sidebar-username';
    label.style.padding = '10px 20px';
    label.style.color = 'white';
    label.style.fontWeight = '500';
    label.style.borderBottom = '1px solid rgba(255,255,255,0.1)';
    const sidebarLogo = document.querySelector('.sidebar .logo');
    if (sidebarLogo) {
        sidebarLogo.parentNode.insertBefore(label, sidebarLogo.nextSibling);
    }
    return label;
}

let allDocuments = []; // Store globally for client-side filtering

async function loadDocuments() {
    const tbody = document.getElementById('table-docs-body');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/ged/documents`, {
            headers: getAuthHeaders()
        });
        
        if(response.status === 401) {
            localStorage.removeItem('ged_token');
            checkAuth();
            throw new Error("Sessão Expirada.");
        }
        
        if(!response.ok) throw new Error("Erro ao buscar documentos");
        
        allDocuments = await response.json();
        renderDocumentsTable();

    } catch (error) {
        console.error(error);
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: #fbbf24;">${error.message}</td></tr>`;
    }
}

function renderDocumentsTable() {
    const tbody = document.getElementById('table-docs-body');
    const filter = document.getElementById('filter-modality') ? document.getElementById('filter-modality').value : 'ALL';
    
    const filteredDocs = allDocuments.filter(doc => {
        if (filter === 'ALL') return true;
        // Compare case insensitive if modality is set
        return doc.modality && doc.modality.toUpperCase() === filter.toUpperCase();
    });

    if (filteredDocs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Nenhum documento encontrado para este filtro.</td></tr>';
        return;
    }

    tbody.innerHTML = '';
    filteredDocs.forEach(doc => {
        const tr = document.createElement('tr');
        let statusClass = 'badge';
        if (doc.status === 'VALIDO') statusClass += ' success';
        else if (doc.status === 'RASCUNHO') statusClass += ' warning';
        
        const modalityBadge = doc.modality ? `<span class="badge" style="background: rgba(160, 174, 192, 0.2); color: #a0aec0;">${doc.modality}</span>` : '-';
        
        tr.innerHTML = `
            <td>${doc.id.substring(0,8)}...</td>
            <td><strong>${doc.title}</strong></td>
            <td>${modalityBadge}</td>
            <td><span class="${statusClass}">${doc.status}</span></td>
            <td>
                <button class="btn-small" onclick="viewRVDD('${doc.id}')">👁️ RVDD</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function viewRVDD(documentId) {
    const modal = document.getElementById('modal-rvdd');
    const frame = document.getElementById('rvdd-frame');
    
    try {
        // To view HTML with auth header, we can't just use iframe.src directly unless it's a cookie based auth.
        // Since we use Bearer Token, we must fetch the HTML and write it into the iframe.
        const response = await fetch(`${API_URL}/documents/${documentId}/rvdd`, {
            headers: getAuthHeaders()
        });
        if(response.status === 401) {
            localStorage.removeItem('ged_token');
            checkAuth();
            return;
        }
        
        const html = await response.text();
        const doc = frame.contentWindow.document;
        doc.open();
        doc.write(html);
        doc.close();
        
        modal.classList.add('active');
    } catch(err) {
        alert("Erro ao carregar RVDD");
    }
}
