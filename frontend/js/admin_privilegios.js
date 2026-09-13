// Cadastros e privilégios documentais do administrador.
const escaparAdmin = valor => String(valor ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const adminGlobal = () => JSON.parse(localStorage.getItem('user') || '{}').role === 'admin_global';
async function requisicaoAdmin(caminho, metodo = 'GET', dados) {
    const resposta = await fetch(`${API_URL}${caminho}`, {
        method: metodo, headers: {...getAuthHeaders(), 'Content-Type': 'application/json'},
        ...(dados === undefined ? {} : {body: JSON.stringify(dados)})
    });
    if (!resposta.ok) {
        const erro = await resposta.json().catch(() => ({}));
        throw new Error(typeof erro.detail === 'string' ? erro.detail : 'Confira os dados e suas permissões.');
    }
    return resposta.status === 204 ? null : resposta.json();
}
async function todasPaginasAdmin(caminho) {
    let itens = [], pagina = 1, dados;
    do {
        dados = await requisicaoAdmin(`${caminho}?page=${pagina}&size=100`);
        itens.push(...dados.items); pagina++;
    } while (pagina <= dados.pages);
    return itens;
}
function modalAdmin(titulo) {
    document.getElementById('modal-cadastro-admin')?.remove();
    const camada = document.createElement('div');
    camada.id = 'modal-cadastro-admin'; camada.className = 'modal-overlay active';
    camada.innerHTML = `<div class="modal-content glass-panel" style="width:min(950px,95vw);max-height:90vh;overflow:auto;padding:24px">
        <h2>${escaparAdmin(titulo)}</h2><div class="conteudo-admin"></div>
        <p class="erro-admin" role="alert" style="color:#d33"></p>
        <button type="button" class="btn-secondary fechar-admin">Cancelar</button></div>`;
    camada.querySelector('.fechar-admin').onclick = () => camada.remove();
    document.body.appendChild(camada);
    return camada;
}
function botaoAdmin(texto, acao) {
    const botao = document.createElement('button');
    botao.type = 'button'; botao.className = 'btn-secondary btn-small'; botao.textContent = texto;
    botao.onclick = acao; return botao;
}
async function editarCadastroAdmin(caminho, registro, indice, atualizar) {
    const modal = modalAdmin(indice ? 'Editar Índice' : 'Editar tipo documental');
    const conteudo = modal.querySelector('.conteudo-admin');
    conteudo.innerHTML = `<form><label>Nome<input name="name" required maxlength="200" value="${escaparAdmin(registro.name)}"></label>
        ${indice ? `<label>Tipo de dado<select name="type" required>
            ${['Texto','Data','Número','Booleano','Lista'].map(tipo => `<option ${registro.type === tipo ? 'selected' : ''}>${tipo}</option>`).join('')}
            </select></label>
            <label>Opções da lista (uma por linha)<textarea name="options" rows="5">${escaparAdmin((registro.options || []).join('\n'))}</textarea></label>
            <label>Máscara (expressão regular)<input name="mask" value="${escaparAdmin(registro.mask || '')}"></label>
            <label><input name="auto_increment" type="checkbox" ${registro.auto_increment ? 'checked' : ''}> Autonumeração</label>` : `
            <label>Grupo<input name="group_id" value="${escaparAdmin(registro.group_id || '')}"></label>
            <label>Anos de retenção<input name="retention_years" type="number" min="0" max="1000" value="${registro.retention_years}"></label>
            <label>ID do fluxo<input name="workflow_id" value="${escaparAdmin(registro.workflow_id || '')}"></label>
            <label>Área de armazenamento<input name="storage_area_id" value="${escaparAdmin(registro.storage_area_id || '')}"></label>
            <label>Partição<input name="storage_partition_id" value="${escaparAdmin(registro.storage_partition_id || '')}"></label>
            <label><input name="legal_hold" type="checkbox" ${registro.legal_hold ? 'checked' : ''}> Preservação legal</label>`}
        <label><input name="is_active" type="checkbox" ${registro.is_active ? 'checked' : ''}> Ativo</label>
        <button class="btn-primary" type="submit">Salvar</button></form>`;
    conteudo.querySelector('form').onsubmit = async evento => {
        evento.preventDefault(); const formulario = evento.target;
        const dados = {name: formulario.elements.name.value, is_active: formulario.elements.is_active.checked};
        if (indice) {
            dados.type = formulario.elements.type.value;
            dados.options = formulario.elements.options.value.split('\n').map(v => v.trim()).filter(Boolean);
            dados.mask = formulario.elements.mask.value.trim() || null;
            dados.auto_increment = formulario.elements.auto_increment.checked;
        } else {
            dados.group_id = formulario.elements.group_id.value.trim() || null;
            dados.retention_years = Number(formulario.elements.retention_years.value);
            dados.workflow_id = formulario.elements.workflow_id.value.trim() || null;
            dados.storage_area_id = formulario.elements.storage_area_id.value.trim() || null;
            dados.storage_partition_id = formulario.elements.storage_partition_id.value.trim() || null;
            dados.legal_hold = formulario.elements.legal_hold.checked;
            dados.access_policy = registro.access_policy || {};
            dados.signature_rule = registro.signature_rule || {};
        }
        try { await requisicaoAdmin(caminho, 'PUT', dados); modal.remove(); await atualizar(); }
        catch (erro) { modal.querySelector('.erro-admin').textContent = erro.message; }
    };
}
async function excluirCadastroAdmin(caminho, nome, atualizar) {
    if (!confirm(`Excluir "${nome}"? Registros em uso serão bloqueados.`)) return;
    try { await requisicaoAdmin(caminho, 'DELETE'); await atualizar(); }
    catch (erro) { alert(erro.message); }
}
loadIndices = async function() {
    const corpo = document.getElementById('table-indices-body');
    corpo.textContent = '';
    try {
        for (const indice of await todasPaginasAdmin('/indices')) {
            const linha = document.createElement('tr');
            linha.innerHTML = `<td>${escaparAdmin(indice.name)}</td><td>${escaparAdmin(indice.type)}</td><td>${indice.is_active ? 'Ativo' : 'Inativo'}</td>`;
            if (adminGlobal()) {
                const celula = linha.lastElementChild;
                celula.append(botaoAdmin('Editar', () => editarCadastroAdmin(`/indices/${indice.id}`, indice, true, loadIndices)));
                celula.append(botaoAdmin('Excluir', () => excluirCadastroAdmin(`/indices/${indice.id}`, indice.name, loadIndices)));
            }
            corpo.append(linha);
        }
    } catch (erro) { corpo.textContent = erro.message; }
};
loadDocTypes = async function() {
    const corpo = document.getElementById('table-doctypes-body'); corpo.textContent = '';
    try {
        for (const tipo of await todasPaginasAdmin('/document-types')) {
            const linha = document.createElement('tr');
            linha.innerHTML = `<td>${escaparAdmin(tipo.name)}<br><small>${tipo.is_active ? 'Ativo' : 'Inativo'}</small></td><td>${tipo.retention_years} anos${tipo.legal_hold ? ' · Legal hold' : ''}</td><td></td>`;
            const celula = linha.lastElementChild;
            celula.append(botaoAdmin('Índices / detalhes', () => selectDocType(tipo.id, tipo.name)));
            if (adminGlobal()) {
                celula.append(botaoAdmin('Editar', () => editarCadastroAdmin(`/document-types/${tipo.id}`, tipo, false, loadDocTypes)));
                celula.append(botaoAdmin('Excluir', () => excluirCadastroAdmin(`/document-types/${tipo.id}`, tipo.name, loadDocTypes)));
            }
            corpo.append(linha);
        }
    } catch (erro) { corpo.textContent = erro.message; }
};
const selecionarTipoAnterior = selectDocType;
selectDocType = function(id, nome) {
    selecionarTipoAnterior(id, nome);
    document.getElementById('btn-add-index').disabled = !adminGlobal();
    carregarIndicesVinculados(id);
};
async function carregarIndicesVinculados(tipoId) {
    let painel = document.getElementById('indices-vinculados-admin');
    if (!painel) {
        painel = document.createElement('div'); painel.id = 'indices-vinculados-admin';
        document.getElementById('current-doctype-name').closest('.glass-panel').append(painel);
    }
    painel.innerHTML = '<h4>Índices vinculados</h4>';
    try {
        const vinculos = await requisicaoAdmin(`/document-types/${tipoId}/indices`);
        for (const vinculo of vinculos) {
            const linha = document.createElement('div');
            linha.style.cssText = 'display:flex;gap:12px;align-items:center;margin:10px 0';
            linha.innerHTML = `<span>${escaparAdmin(vinculo.index.name)} (${escaparAdmin(vinculo.index.type)})</span>
                <label><input type="checkbox" data-campo="is_required" ${vinculo.is_required ? 'checked' : ''}> Obrigatório</label>
                <label><input type="checkbox" data-campo="is_unique" ${vinculo.is_unique ? 'checked' : ''}> Único</label>`;
            linha.querySelectorAll('input').forEach(campo => campo.disabled = !adminGlobal());
            if (adminGlobal()) {
                linha.append(botaoAdmin('Salvar', async () => {
                    try {
                        await requisicaoAdmin(`/document-types/${tipoId}/indices/${vinculo.id}`, 'PUT', {
                            index_id: vinculo.index_id,
                            is_required: linha.querySelector('[data-campo="is_required"]').checked,
                            is_unique: linha.querySelector('[data-campo="is_unique"]').checked
                        });
                        await carregarIndicesVinculados(tipoId);
                    } catch (erro) { alert(erro.message); }
                }));
                linha.append(botaoAdmin('Remover', () => excluirCadastroAdmin(`/document-types/${tipoId}/indices/${vinculo.id}`, vinculo.index.name, () => carregarIndicesVinculados(tipoId))));
            }
            painel.append(linha);
        }
        if (!vinculos.length) painel.append('Nenhum Índice vinculado.');
    } catch (erro) { painel.append(erro.message); }
}
async function abrirPermissoesDocumentais(usuario) {
    const modal = modalAdmin(`Tipos documentais e privilégios: ${usuario.username}`);
    const conteudo = modal.querySelector('.conteudo-admin'); conteudo.textContent = 'Carregando...';
    try {
        const dados = await requisicaoAdmin(`/users/${usuario.id}/document-permissions`);
        const vinculos = new Map(dados.vinculos.map(v => [v.document_type_id, new Set(v.permissions)]));
        conteudo.innerHTML = `<p>Vincule um tipo e marque as ações permitidas. Sem marcação, a operação fica bloqueada.</p>
            <label>Buscar tipo documental<input type="search" class="buscar-tipo"></label>
            <div style="overflow:auto;max-height:55vh"><table class="data-table"><thead><tr><th>Vinculado</th><th>Tipo documental</th>
            ${Object.values(dados.acoes).map(nome => `<th>${escaparAdmin(nome)}</th>`).join('')}</tr></thead><tbody></tbody></table></div>
            <button class="btn-primary salvar-permissoes">Salvar permissões</button>`;
        const corpo = conteudo.querySelector('tbody');
        for (const tipo of dados.tipos) {
            const linha = document.createElement('tr'); linha.dataset.nome = tipo.name.toLocaleLowerCase();
            const vinculado = document.createElement('input'); vinculado.type = 'checkbox'; vinculado.checked = vinculos.has(tipo.id);
            vinculado.setAttribute('aria-label', `Vincular ${tipo.name}`);
            const primeira = document.createElement('td'); primeira.append(vinculado); linha.append(primeira);
            const nome = document.createElement('td'); nome.textContent = tipo.name + (tipo.is_active ? '' : ' (inativo)'); linha.append(nome);
            vinculado.onchange = () => {
                if (vinculado.checked) vinculos.set(tipo.id, new Set()); else vinculos.delete(tipo.id);
                linha.querySelectorAll('[data-acao]').forEach(campo => { campo.checked = false; campo.disabled = !vinculado.checked; });
            };
            for (const [acao, rotulo] of Object.entries(dados.acoes)) {
                const celula = document.createElement('td'), campo = document.createElement('input');
                campo.type = 'checkbox'; campo.dataset.acao = acao; campo.checked = vinculos.get(tipo.id)?.has(acao) || false;
                campo.disabled = !vinculado.checked; campo.setAttribute('aria-label', `${rotulo}: ${tipo.name}`);
                campo.onchange = () => campo.checked ? vinculos.get(tipo.id).add(acao) : vinculos.get(tipo.id).delete(acao);
                celula.append(campo); linha.append(celula);
            }
            corpo.append(linha);
        }
        conteudo.querySelector('.buscar-tipo').oninput = evento => {
            const busca = evento.target.value.toLocaleLowerCase();
            corpo.querySelectorAll('tr').forEach(linha => linha.hidden = !linha.dataset.nome.includes(busca));
        };
        conteudo.querySelector('.salvar-permissoes').onclick = async evento => {
            evento.target.disabled = true;
            try {
                await requisicaoAdmin(`/users/${usuario.id}/document-permissions`, 'PUT', {
                    vinculos: [...vinculos].map(([document_type_id, acoes]) => ({document_type_id, permissions: [...acoes]}))
                }); modal.remove();
            } catch (erro) { modal.querySelector('.erro-admin').textContent = erro.message; }
            finally { evento.target.disabled = false; }
        };
        if (usuario.role === 'admin_global') {
            conteudo.querySelectorAll('input,button').forEach(elemento => elemento.disabled = true);
            modal.querySelector('.erro-admin').textContent = 'O administrador global possui acesso integral.';
        }
    } catch (erro) { conteudo.textContent = erro.message; }
}

const salvarVinculoAnterior = saveDocTypeIndex;
saveDocTypeIndex = async function() {
    await salvarVinculoAnterior();
    if (currentDocTypeId) await carregarIndicesVinculados(currentDocTypeId);
};
document.addEventListener('DOMContentLoaded', () => {
    if (!adminGlobal()) {
        document.querySelectorAll('[onclick="openDocTypeModal()"], [onclick="openIndexModal()"], [onclick="openDocTypeIndexModal()"]')
            .forEach(botao => { botao.disabled = true; botao.title = 'Cadastro compartilhado: requer administrador global.'; });
    }
});
