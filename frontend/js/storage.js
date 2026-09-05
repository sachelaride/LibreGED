let currentStorageAreaId = null;

async function loadStorageAreas() {
    const tbody = document.getElementById('table-areas-body');
    tbody.innerHTML = '<tr><td colspan="2" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(${API_URL}/storage/areas, {
            headers: getAuthHeaders()
        });
        if(!response.ok) throw new Error("Erro ao carregar áreas");
        
        const areas = await response.json();
        tbody.innerHTML = '';
        
        if(areas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="2" style="text-align:center">Nenhuma área cadastrada</td></tr>';
            return;
        }

        areas.forEach(area => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            if(area.id === currentStorageAreaId) tr.style.backgroundColor = 'rgba(255,255,255,0.1)';
            
            tr.innerHTML = 
                <td><strong></strong></td>
                <td>
                    <button class="btn-small" onclick="selectArea('', '')">Selecionar</button>
                </td>
            ;
            tbody.appendChild(tr);
        });
    } catch (error) {
        tbody.innerHTML = <tr><td colspan="2" style="color:#fbbf24"></td></tr>;
    }
}

async function selectArea(id, name) {
    currentStorageAreaId = id;
    document.getElementById('btn-new-partition').disabled = false;
    document.getElementById('partition-area-id').innerHTML = <option value=""></option>;
    loadStorageAreas(); // refresh selection highlight
    loadStoragePartitions();
}

async function loadStoragePartitions() {
    if(!currentStorageAreaId) return;
    
    const tbody = document.getElementById('table-partitions-body');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Carregando...</td></tr>';
    
    try {
        const response = await fetch(${API_URL}/storage/partitions?area_id=, {
            headers: getAuthHeaders()
        });
        if(!response.ok) throw new Error("Erro ao carregar partições");
        
        const partitions = await response.json();
        tbody.innerHTML = '';
        
        if(partitions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center">Nenhuma partição encontrada</td></tr>';
            return;
        }

        partitions.forEach(p => {
            const tr = document.createElement('tr');
            const isActive = p.is_active ? '<span class="badge success">ATIVA</span>' : '<span class="badge warning">CHEIA</span>';
            tr.innerHTML = 
                <td><strong></strong></td>
                <td></td>
                <td> / </td>
                <td> /  GB</td>
                <td></td>
            ;
            tbody.appendChild(tr);
        });
    } catch (error) {
        tbody.innerHTML = <tr><td colspan="5" style="color:#fbbf24"></td></tr>;
    }
}

function openAreaModal() {
    document.getElementById('area-name').value = '';
    document.getElementById('modal-area').classList.add('active');
}

async function saveArea() {
    const name = document.getElementById('area-name').value;
    if(!name) return alert("Preencha o nome");
    
    try {
        const response = await fetch(${API_URL}/storage/areas, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, is_active: true })
        });
        
        if(response.ok) {
            document.getElementById('modal-area').classList.remove('active');
            loadStorageAreas();
        } else {
            alert("Erro ao salvar área");
        }
    } catch(e) {
        alert(e.message);
    }
}

function openPartitionModal() {
    if(!currentStorageAreaId) return alert("Selecione uma área primeiro");
    document.getElementById('partition-name').value = '';
    document.getElementById('partition-max-files').value = '10000';
    document.getElementById('partition-max-gb').value = '100.0';
    document.getElementById('partition-base-path').value = '';
    document.getElementById('modal-partition').classList.add('active');
}

async function savePartition() {
    const name = document.getElementById('partition-name').value;
    const max_files = parseInt(document.getElementById('partition-max-files').value);
    const max_size_gb = parseFloat(document.getElementById('partition-max-gb').value);
    const base_path = document.getElementById('partition-base-path').value;
    
    if(!name || !base_path || !max_files || !max_size_gb) return alert("Preencha todos os campos");
    
    try {
        const response = await fetch(${API_URL}/storage/partitions, {
            method: 'POST',
            headers: {
                ...getAuthHeaders(),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name,
                area_id: currentStorageAreaId,
                max_files,
                max_size_gb,
                base_path
            })
        });
        
        if(response.ok) {
            document.getElementById('modal-partition').classList.remove('active');
            loadStoragePartitions();
        } else {
            alert("Erro ao salvar partição");
        }
    } catch(e) {
        alert(e.message);
    }
}
