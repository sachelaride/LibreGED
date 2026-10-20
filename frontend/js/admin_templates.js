// JS para gestão de Templates RVDD (Baseado no trânsito dinâmico)
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

const DEFAULT_RVDD_TEMPLATE = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Representação Visual do Diploma Digital (RVDD)</title>
    <style>
        @page { size: A4 landscape; margin: 0; }
        * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        body {
            font-family: 'Cinzel', 'Georgia', 'Times New Roman', serif;
            margin: 0; padding: 20px; background-color: #e2e8f0;
            display: flex; justify-content: center; align-items: center; min-height: 100vh;
        }
        .diploma-card {
            width: 1050px; min-height: 740px; background: #ffffff;
            padding: 45px 50px; box-shadow: 0 15px 35px rgba(0,0,0,0.15);
            border: 14px solid #1e3a8a; outline: 3px solid #d97706; outline-offset: -8px;
            position: relative; display: flex; flex-direction: column; justify-content: space-between;
        }
        .diploma-card::before {
            content: ""; position: absolute; top: 14px; left: 14px; right: 14px; bottom: 14px;
            border: 1px dashed #d97706; pointer-events: none;
        }
        .header { text-align: center; margin-bottom: 20px; }
        .header .emblem { font-size: 38px; color: #d97706; margin-bottom: 5px; }
        .header h1 { font-size: 22px; text-transform: uppercase; letter-spacing: 3px; color: #1e3a8a; margin: 0; font-weight: 700; }
        .header h2 { font-size: 15px; text-transform: uppercase; letter-spacing: 2px; color: #475569; margin: 4px 0 0 0; font-weight: 600; }
        .header h3 { font-size: 16px; color: #0f172a; margin: 6px 0 0 0; font-weight: 700; font-style: italic; }
        .title-badge {
            display: inline-block; margin: 15px auto 10px; padding: 4px 24px;
            background: linear-gradient(135deg, #1e3a8a, #1e40af); color: #ffffff;
            font-size: 20px; letter-spacing: 6px; text-transform: uppercase; border-radius: 4px; font-weight: 700;
        }
        .content { text-align: center; font-size: 15px; line-height: 1.8; color: #1e293b; padding: 0 40px; }
        .student-name {
            font-size: 28px; font-weight: 700; color: #1e3a8a; letter-spacing: 1px;
            margin: 12px 0 8px; text-transform: uppercase; border-bottom: 2px solid #d97706;
            display: inline-block; padding: 0 20px 4px;
        }
        .course-name { font-size: 24px; font-weight: 700; color: #b45309; margin: 8px 0; text-transform: uppercase; }
        .footer {
            margin-top: 25px; display: flex; justify-content: space-between; align-items: flex-end;
            padding-top: 15px; border-top: 1px solid #e2e8f0;
        }
        .signatures-container { display: flex; gap: 40px; }
        .sig-block { text-align: center; width: 200px; }
        .sig-line { border-top: 1px solid #334155; margin-bottom: 6px; }
        .sig-title { font-size: 12px; font-weight: 700; color: #0f172a; text-transform: uppercase; }
        .sig-sub { font-size: 10px; color: #64748b; }
        .security-box {
            display: flex; align-items: center; gap: 15px; background: #f8fafc;
            border: 1px solid #cbd5e1; padding: 8px 14px; border-radius: 6px; max-width: 440px;
        }
        .security-box img { width: 90px; height: 90px; border: 1px solid #e2e8f0; background: #ffffff; padding: 2px; }
        .security-text { text-align: left; font-size: 10px; color: #334155; line-height: 1.4; }
        .security-text strong { color: #0f172a; }
        .security-text a { color: #2563eb; text-decoration: none; word-break: break-all; }
    </style>
</head>
<body>
<div class="diploma-card">
    <div class="header">
        <div class="emblem">🏛️</div>
        <h1>República Federativa do Brasil</h1>
        <h2>Ministério da Educação</h2>
        <h3>Instituto de Ensino Superior EduGED Libre</h3>
        <div><span class="title-badge">DIPLOMA</span></div>
    </div>
    <div class="content">
        <p style="margin: 0;">O Reitor da Instituição, no uso de suas atribuições legais e estatutárias, confere a</p>
        <div class="student-name">{{ nome_aluno }}</div>
        <p style="margin: 4px 0;">de nacionalidade brasileira, portador(a) do documento de identidade CPF sob nº <strong>{{ cpf_aluno }}</strong>,</p>
        <p style="margin: 4px 0;">tendo concluído a graduação em <strong>{{ data_conclusao }}</strong>, o título e grau de</p>
        <div class="course-name">Bacharel em {{ curso }}</div>
        <p style="margin: 0; font-size: 13px; color: #475569;">com todas as prerrogativas, direitos e deveres que as leis do País outorgam.</p>
    </div>
    <div class="footer">
        <div class="signatures-container">
            <div class="sig-block">
                <div class="sig-line"></div>
                <div class="sig-title">Reitor(a)</div>
                <div class="sig-sub">Assinatura Digital ICP-Brasil</div>
            </div>
            <div class="sig-block">
                <div class="sig-line"></div>
                <div class="sig-title">Secretário(a) Geral</div>
                <div class="sig-sub">Assinatura Digital ICP-Brasil</div>
            </div>
        </div>
        <div class="security-box">
            <img src="data:image/png;base64,{{ qrcode_base64 }}" alt="QR Code RVDD">
            <div class="security-text">
                <strong>REPRESENTAÇÃO VISUAL DO DIPLOMA DIGITAL (RVDD)</strong><br>
                Em conformidade com a Portaria MEC nº 330/2018 e nº 554/2019.<br>
                Cód. Validação: <strong>{{ codigo_validacao }}</strong><br>
                Consulte a autenticidade pelo QR-Code ou em:<br>
                <a href="{{ url_validacao }}" target="_blank">{{ url_validacao }}</a>
            </div>
        </div>
    </div>
</div>
</body>
</html>`;

function loadOfficialRvddPreset() {
    document.getElementById('tpl-name').value = 'Modelo Oficial RVDD - MEC (Portaria 554/2019)';
    document.getElementById('tpl-html').value = DEFAULT_RVDD_TEMPLATE.trim();
}

function insertTag(tag) {
    const textarea = document.getElementById('tpl-html');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = textarea.value;
    textarea.value = text.substring(0, start) + tag + text.substring(end);
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = start + tag.length;
}

function previewCurrentTemplate() {
    let rawHtml = document.getElementById('tpl-html').value;
    // Mock values for preview
    const sampleQr = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
    let previewHtml = rawHtml
        .replace(/\{\{\s*nome_aluno\s*\}\}/g, 'CARLOS EDUARDO DA SILVA SANTOS')
        .replace(/\{\{\s*cpf_aluno\s*\}\}/g, '123.456.789-00')
        .replace(/\{\{\s*curso\s*\}\}/g, 'MEDICINA')
        .replace(/\{\{\s*data_conclusao\s*\}\}/g, '15 de Dezembro de 2025')
        .replace(/\{\{\s*codigo_validacao\s*\}\}/g, 'MEC-RVDD-7789-2026')
        .replace(/\{\{\s*url_validacao\s*\}\}/g, 'https://eduged.edu.br/validar/MEC-RVDD-7789-2026')
        .replace(/\{\{\s*qrcode_base64\s*\}\}/g, sampleQr);

    const iframe = document.getElementById('template-preview-frame');
    iframe.srcdoc = previewHtml;
    document.getElementById('modal-template-preview').classList.add('active');
}

function openTemplateModal() {
    document.getElementById('tpl-name').value = 'Modelo Oficial RVDD - MEC (Portaria 554/2019)';
    document.getElementById('tpl-html').value = DEFAULT_RVDD_TEMPLATE.trim();
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
