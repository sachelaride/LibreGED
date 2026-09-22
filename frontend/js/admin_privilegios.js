// Cadastros e privilégios documentais do administrador.
const escaparAdmin = valor => String(valor ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const adminGlobal = () => {
    try {
        const token = localStorage.getItem('ged_token');
        const payload = token && typeof parseJwt === 'function' ? parseJwt(token) : null;
        return payload?.role === 'admin_global';
    } catch (erro) {
        console.error('Não foi possível verificar o papel administrativo.', erro);
        return false;
    }
};
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
function modalAdmin(titulo, id = 'modal-cadastro-admin') {
    document.getElementById(id)?.remove();
    const camada = document.createElement('div');
    camada.id = id; camada.className = 'modal-overlay active';
    camada.innerHTML = `<div class="modal-content glass-panel" style="width:min(950px,100%);max-height:none;overflow:visible;padding:24px">
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
    const modal = modalAdmin(`Tipos de documento: ${usuario.username}`);
    const conteudo = modal.querySelector('.conteudo-admin'); conteudo.textContent = 'Carregando...';
    try {
        const dados = await requisicaoAdmin(`/users/${usuario.id}/document-permissions`);
        const vinculos = new Map(dados.vinculos.map(v => [v.document_type_id, {
            allowed: new Set(v.permissions || []),
            denied: new Set(v.denied_permissions || [])
        }]));
        conteudo.innerHTML = `<p>Vincule os tipos documentais ao usuário. Em cada tipo vinculado, clique em <strong>Configurar permissões</strong> para escolher o que ele pode fazer.</p>
            <input type="search" class="buscar-tipo" placeholder="Pesquisar tipo documental">
            <div class="privilege-transfer" style="display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:stretch;min-height:360px">
                <section class="glass-panel" style="padding:12px"><h4>Disponíveis</h4><div class="tipos-disponiveis"></div></section>
                <div style="display:flex;flex-direction:column;justify-content:center;gap:8px">
                    <button type="button" class="btn-secondary btn-small mover-tipo-direita" title="Vincular selecionados">›</button>
                    <button type="button" class="btn-secondary btn-small mover-tipo-esquerda" title="Desvincular selecionados">‹</button>
                </div>
                <section class="glass-panel" style="padding:12px"><h4>Vinculados</h4><div class="tipos-vinculados"></div></section>
            </div>
            <button class="btn-primary salvar-permissoes">Salvar vínculos e permissões</button>`;
        const disponiveis = conteudo.querySelector('.tipos-disponiveis');
        const vinculados = conteudo.querySelector('.tipos-vinculados');
        const criarLinhaTipo = (tipo, ligado) => {
            const linha = document.createElement('div');
            linha.className = 'privilege-transfer-row';
            linha.dataset.nome = tipo.name.toLocaleLowerCase();
            linha.style.cssText = 'display:flex;gap:8px;align-items:center;padding:9px 6px;border-bottom:1px solid rgba(148,163,184,.25)';
            const estado = vinculos.get(tipo.id);
            const permitidas = estado ? estado.allowed.size : 0;
            const negadas = estado ? estado.denied.size : 0;
            linha.innerHTML = `<input type="checkbox" data-tipo-id="${tipo.id}">
                <span style="flex:1">${escaparAdmin(tipo.name)}${tipo.is_active ? '' : ' (inativo)'}
                    ${ligado ? `<small class="resumo-permissoes" style="display:block;color:#64748b">${permitidas} permitida(s) · ${negadas} negada(s)</small>` : ''}
                </span>`;
            if (ligado) {
                linha.title = 'Use o botão Configurar permissões para escolher as ações';
                const configurar = botaoAdmin('Configurar permissões', () => abrirAcoesTipo(tipo));
                configurar.classList.add('configurar-permissoes');
                linha.append(configurar);
            }
            return linha;
        };
        const renderTipos = () => {
            disponiveis.innerHTML = ''; vinculados.innerHTML = '';
            dados.tipos.forEach(tipo => {
                (vinculos.has(tipo.id) ? vinculados : disponiveis).append(criarLinhaTipo(tipo, vinculos.has(tipo.id)));
            });
        };
        renderTipos();
        conteudo.querySelector('.buscar-tipo').oninput = evento => {
            const busca = evento.target.value.toLocaleLowerCase();
            conteudo.querySelectorAll('.privilege-transfer-row').forEach(linha => {
                linha.hidden = !linha.dataset.nome.includes(busca);
            });
        };
        const moverTipos = (origem, destino) => {
            conteudo.querySelectorAll(`${origem} input[data-tipo-id]:checked`).forEach(campo => {
                const tipoId = campo.dataset.tipoId;
                if (destino === '.tipos-vinculados') {
                    if (!vinculos.has(tipoId)) vinculos.set(tipoId, {allowed: new Set(), denied: new Set()});
                } else {
                    vinculos.delete(tipoId);
                }
            });
            renderTipos();
        };
        conteudo.querySelector('.mover-tipo-direita').onclick = () => moverTipos('.tipos-disponiveis', '.tipos-vinculados');
        conteudo.querySelector('.mover-tipo-esquerda').onclick = () => moverTipos('.tipos-vinculados', '.tipos-disponiveis');
        const abrirAcoesTipo = tipo => {
            const acaoModal = modalAdmin(`Conceder privilégios: ${tipo.name}`, 'modal-privilegios-acoes');
            acaoModal.querySelector('.conteudo-admin').innerHTML = `
                <p>Vincule as ações permitidas ou negadas para este tipo documental.</p>
                <div class="privilege-actions" style="display:grid;grid-template-columns:1fr auto 1fr;gap:14px;align-items:stretch;min-height:360px">
                    <section class="glass-panel" style="padding:12px"><h4>Ações disponíveis</h4>
                        <div style="display:flex;gap:6px;margin-bottom:8px">
                            <button type="button" class="btn-secondary btn-small selecionar-acoes-disponiveis">Selecionar todas</button>
                            <button type="button" class="btn-secondary btn-small limpar-acoes-disponiveis">Limpar</button>
                        </div>
                        <div class="acoes-disponiveis"></div>
                    </section>
                    <div style="display:flex;flex-direction:column;justify-content:center;gap:8px">
                        <button type="button" class="btn-secondary btn-small mover-acao-direita" title="Vincular ações selecionadas">›</button>
                        <button type="button" class="btn-secondary btn-small mover-acao-esquerda" title="Desvincular ações selecionadas">‹</button>
                    </div>
                    <section class="glass-panel" style="padding:12px"><h4>Ações vinculadas</h4>
                        <div style="display:flex;gap:6px;margin-bottom:8px">
                            <button type="button" class="btn-secondary btn-small selecionar-acoes-vinculadas">Selecionar todas</button>
                            <button type="button" class="btn-secondary btn-small limpar-acoes-vinculadas">Limpar</button>
                        </div>
                        <div class="acoes-vinculadas"></div>
                    </section>
                </div>
                <button type="button" class="btn-primary salvar-acoes">Salvar ações</button>`;
            const estado = vinculos.get(tipo.id) || {allowed: new Set(), denied: new Set()};
            const disponiveisAcoes = acaoModal.querySelector('.acoes-disponiveis');
            const vinculadasAcoes = acaoModal.querySelector('.acoes-vinculadas');
            const acoesVinculadas = new Set([...estado.allowed, ...estado.denied]);
            const criarLinhaAcao = (acao, rotulo, ligado) => {
                const linha = document.createElement('div');
                linha.style.cssText = ligado
                    ? 'display:grid;grid-template-columns:20px 1fr 110px;gap:6px;align-items:center;padding:7px 0;border-bottom:1px solid rgba(148,163,184,.25)'
                    : 'display:flex;gap:8px;align-items:center;padding:9px 6px;border-bottom:1px solid rgba(148,163,184,.25)';
                const atual = estado.allowed.has(acao) ? 'allow' : 'deny';
                linha.innerHTML = `<input type="checkbox" data-acao="${escaparAdmin(acao)}"><span style="flex:1">${escaparAdmin(rotulo)}</span>
                    ${ligado ? '<select><option value="allow">Permitido</option><option value="deny">Negado</option></select>' : ''}`;
                if (ligado) linha.querySelector('select').value = atual;
                (ligado ? vinculadasAcoes : disponiveisAcoes).append(linha);
                linha.dataset.acao = acao;
                return linha;
            };
            const renderAcoes = () => {
                disponiveisAcoes.innerHTML = '';
                vinculadasAcoes.innerHTML = '';
                Object.entries(dados.acoes).forEach(([acao, rotulo]) => {
                    criarLinhaAcao(acao, rotulo, acoesVinculadas.has(acao));
                });
            };
            renderAcoes();
            const moverAcoes = (origem, destino) => {
                acaoModal.querySelectorAll(`${origem} input[data-acao]:checked`).forEach(campo => {
                    if (destino === '.acoes-vinculadas') {
                        acoesVinculadas.add(campo.dataset.acao);
                        if (!estado.allowed.has(campo.dataset.acao) && !estado.denied.has(campo.dataset.acao)) {
                            estado.allowed.add(campo.dataset.acao);
                        }
                    } else {
                        acoesVinculadas.delete(campo.dataset.acao);
                        estado.allowed.delete(campo.dataset.acao);
                        estado.denied.delete(campo.dataset.acao);
                    }
                });
                renderAcoes();
            };
            acaoModal.querySelector('.mover-acao-direita').onclick = () => moverAcoes('.acoes-disponiveis', '.acoes-vinculadas');
            acaoModal.querySelector('.mover-acao-esquerda').onclick = () => moverAcoes('.acoes-vinculadas', '.acoes-disponiveis');
            const selecionarAcoes = (painel, marcado) => {
                acaoModal.querySelectorAll(`${painel} input[data-acao]`).forEach(campo => campo.checked = marcado);
            };
            acaoModal.querySelector('.selecionar-acoes-disponiveis').onclick = () => selecionarAcoes('.acoes-disponiveis', true);
            acaoModal.querySelector('.limpar-acoes-disponiveis').onclick = () => selecionarAcoes('.acoes-disponiveis', false);
            acaoModal.querySelector('.selecionar-acoes-vinculadas').onclick = () => selecionarAcoes('.acoes-vinculadas', true);
            acaoModal.querySelector('.limpar-acoes-vinculadas').onclick = () => selecionarAcoes('.acoes-vinculadas', false);
            acaoModal.querySelector('.salvar-acoes').onclick = () => {
                estado.allowed.clear(); estado.denied.clear();
                acaoModal.querySelectorAll('.acoes-vinculadas input[data-acao]').forEach(campo => {
                    const linha = campo.parentElement;
                    const valor = linha.querySelector('select').value;
                    if (valor === 'allow') estado.allowed.add(linha.dataset.acao);
                    if (valor === 'deny') estado.denied.add(linha.dataset.acao);
                });
                vinculos.set(tipo.id, estado);
                acaoModal.remove();
                renderTipos();
            };
            if (usuario.role === 'admin_global') {
                acaoModal.querySelectorAll('input,select,button:not(.fechar-admin)').forEach(elemento => elemento.disabled = true);
            }
        };
        conteudo.querySelector('.salvar-permissoes').onclick = async evento => {
            evento.target.disabled = true;
            try {
                await requisicaoAdmin(`/users/${usuario.id}/document-permissions`, 'PUT', {
                    vinculos: [...vinculos].map(([document_type_id, estado]) => ({
                        document_type_id, permissions: [...estado.allowed], denied_permissions: [...estado.denied]
                    }))
                });
                modal.remove();
            } catch (erro) { modal.querySelector('.erro-admin').textContent = erro.message; }
            finally { evento.target.disabled = false; }
        };
        if (usuario.role === 'admin_global') {
            conteudo.querySelectorAll('.mover-tipo-direita,.mover-tipo-esquerda,.salvar-permissoes').forEach(elemento => elemento.disabled = true);
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
