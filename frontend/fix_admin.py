import re

path = 'c:/Users/SACHELARIDE/Desktop/LibreGED/frontend/admin.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to find the specific area and replace it.
pattern = r'(<input type="text" id="dt-workflow">\s*</div>)(.*?)<h2>Vincular Índice</h2>'

replacement = r'''\1
                            <div class="form-group" style="display: flex; align-items: center; gap: 10px;">
                                <input type="checkbox" id="dt-legal-hold" style="width: auto;">
                                <label for="dt-legal-hold" style="margin-bottom: 0;">Legal Hold (Congelamento Jurídico)</label>
                            </div>
                            <div class="form-group mt-20">
                                <label>Área de Armazenamento (Regra de Storage)</label>
                                <select id="dt-area" onchange="loadPartitionsForArea(this.value)">
                                    <option value="">-- Selecione (Opcional) --</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label>Partição Lógica</label>
                                <select id="dt-partition">
                                    <option value="">-- Selecione uma Área Primeiro --</option>
                                </select>
                            </div>
                            <button type="submit" class="btn-primary w-100 mt-20">Salvar Tipo</button>
                        </form>
                    </div>
                </div>
                
                <!-- Modal Ligar Indice ao Tipo Documental -->
                <div class="modal-overlay" id="modal-doctype-index">
                    <div class="modal-content glass-panel" style="width: 400px; padding: 30px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                            <h2>Vincular Índice</h2>'''

new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Fix applied successfully")
