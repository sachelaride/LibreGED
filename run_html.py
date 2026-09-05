with open(r'frontend\index.html', 'r', encoding='utf-8') as f:
    content = f.read()

menu_target = '''<a href="#" class="menu-item" data-target="documentos">
                    <i>📄</i> GED Documentos
                </a>'''
menu_insert = menu_target + '''
                <a href="#" class="menu-item admin-only" data-target="storage" style="display: none;">
                    <i>🗄️</i> Áreas de Armazenamento
                </a>'''

if menu_target in content:
    content = content.replace(menu_target, menu_insert)
else:
    print("menu target not found")

view_target = '<!-- View: GED Documentos -->'
view_insert = '''<!-- View: Storage (Admin) -->
        <section id="view-storage" class="view" style="display: none;">
            <header class="glass-panel" style="margin-bottom: 20px;">
                <div class="header-title">
                    <h1 id="page-title-storage">Áreas de Armazenamento</h1>
                </div>
            </header>

            <div style="display: flex; gap: 20px;">
                <!-- Áreas -->
                <div class="glass-panel" style="flex: 1; min-height: 400px; padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3>Áreas</h3>
                        <button class="btn-primary btn-small" onclick="openAreaModal()">+ Nova Área</button>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Nome da Área</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="table-areas-body">
                        </tbody>
                    </table>
                </div>

                <!-- Partições -->
                <div class="glass-panel" style="flex: 2; min-height: 400px; padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h3 id="lbl-partition-area">Partições da Área</h3>
                        <button class="btn-primary btn-small" onclick="openPartitionModal()" id="btn-new-partition" disabled>+ Nova Partição</button>
                    </div>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Nome</th>
                                <th>Caminho</th>
                                <th>Max Arq</th>
                                <th>Max GB</th>
                                <th>Ativa</th>
                            </tr>
                        </thead>
                        <tbody id="table-partitions-body">
                            <tr><td colspan="5" style="text-align:center;">Selecione uma área à esquerda</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
        
        <!-- Modal Nova Área -->
        <div class="modal" id="modal-area">
            <div class="modal-content glass-panel" style="width: 400px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Nova Área</h2>
                    <button class="btn-small btn-close" onclick="document.getElementById('modal-area').classList.remove('active')">✕</button>
                </div>
                <div class="form-group">
                    <label>Nome da Área de Armazenamento *</label>
                    <input type="text" id="area-name" required>
                </div>
                <button class="btn-primary w-100" onclick="saveArea()">Salvar Área</button>
            </div>
        </div>

        <!-- Modal Nova Partição -->
        <div class="modal" id="modal-partition">
            <div class="modal-content glass-panel" style="width: 500px; padding: 30px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h2>Nova Partição</h2>
                    <button class="btn-small btn-close" onclick="document.getElementById('modal-partition').classList.remove('active')">✕</button>
                </div>
                <div class="form-group">
                    <label>Área de Armazenamento *</label>
                    <select id="partition-area-id" disabled></select>
                </div>
                <div class="form-group">
                    <label>Nome da Partição (ex: APROVEITAMENTO DE ESTUDOS) *</label>
                    <input type="text" id="partition-name" required>
                </div>
                <div style="display: flex; gap: 15px;">
                    <div class="form-group" style="flex:1">
                        <label>Máximo Arquivos *</label>
                        <input type="number" id="partition-max-files" value="10000" required>
                    </div>
                    <div class="form-group" style="flex:1">
                        <label>Tamanho Máx (GB) *</label>
                        <input type="number" id="partition-max-gb" step="0.1" value="100.0" required>
                    </div>
                </div>
                <div class="form-group">
                    <label>Caminho Base (ex: STORAGE/APROVEITAMENTO) *</label>
                    <input type="text" id="partition-base-path" required>
                </div>
                <button class="btn-primary w-100" onclick="savePartition()">Salvar Partição</button>
            </div>
        </div>

        ''' + view_target

if view_target in content:
    content = content.replace(view_target, view_insert)
else:
    print("view target not found")

with open(r'frontend\index.html', 'w', encoding='utf-8') as f:
    f.write(content)
