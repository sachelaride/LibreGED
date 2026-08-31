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

function checkAuth() {
    const token = localStorage.getItem('ged_token');
    if (!token) {
        // Not logged in
        document.getElementById('view-login').style.display = 'flex';
        document.getElementById('main-sidebar').style.display = 'none';
        document.getElementById('main-content').style.display = 'none';
    } else {
        // Logged in
        document.getElementById('view-login').style.display = 'none';
        document.getElementById('main-sidebar').style.display = 'flex';
        document.getElementById('main-content').style.display = 'flex';
        // Auto load initial view (Dashboard)
        // You can trigger load dashboard data here
    }
}

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
        
        const docs = await response.json();
        
        if (docs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Nenhum documento encontrado no banco.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        docs.forEach(doc => {
            const tr = document.createElement('tr');
            let statusClass = 'badge';
            if (doc.status === 'VALIDO') statusClass += ' success';
            else if (doc.status === 'RASCUNHO') statusClass += ' warning';
            
            tr.innerHTML = `
                <td>${doc.id.substring(0,8)}...</td>
                <td><strong>${doc.title}</strong></td>
                <td>${doc.academic_phase}</td>
                <td><span class="${statusClass}">${doc.status}</span></td>
                <td>
                    <button class="btn-small" onclick="viewRVDD('${doc.id}')">👁️ RVDD</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (error) {
        console.error(error);
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color: #fbbf24;">${error.message}</td></tr>`;
    }
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
