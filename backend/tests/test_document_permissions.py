"""Aceite do CRUD administrativo e concessão de privilégios documentais."""
from datetime import timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_active_user
from app.database import SessionLocal
from app.models import Institution, User, AuditEvent, utc_now
from app.models_ged import DocumentCategory, GEDDocument, GEDDocumentStatus
from app.models_ged_config import DocumentType, UserDocumentType

cliente = TestClient(app)


@pytest.fixture
def cenario():
    with SessionLocal() as db:
        instituicao = Institution(id=str(uuid4()), name="Teste", cnpj="123", legal_name="Teste")
        db.add(instituicao)
        db.flush()
        usuario = User(id=str(uuid4()), username="operador", hashed_password="teste",
                       institution_id=instituicao.id, role="operador")
        tipo = DocumentType(name="Histórico", retention_years=0)
        db.add_all([usuario, tipo])
        db.flush()
        db.add(DocumentCategory(id=tipo.id, name=tipo.name))
        db.flush()
        documento = GEDDocument(title="Histórico de teste", category_id=tipo.id,
            institution_id=instituicao.id, file_path="teste.pdf", status=GEDDocumentStatus.VALIDO,
            created_at=utc_now() - timedelta(days=1))
        db.add(documento)
        db.commit()
        dados = {"usuario": usuario.id, "tipo": tipo.id, "documento": documento.id,
                 "instituicao": instituicao.id}
    yield dados


@pytest.fixture
def autenticar():
    anterior = app.dependency_overrides.get(get_current_active_user)
    def trocar(usuario_id):
        with SessionLocal() as db:
            usuario = db.get(User, usuario_id)
            db.expunge(usuario)
        app.dependency_overrides[get_current_active_user] = lambda: usuario
    yield trocar
    if anterior:
        app.dependency_overrides[get_current_active_user] = anterior
    else:
        app.dependency_overrides.pop(get_current_active_user, None)


def conceder(cenario, acoes):
    return cliente.put(f"/api/users/{cenario['usuario']}/document-permissions", json={
        "vinculos": [{"document_type_id": cenario['tipo'], "permissions": acoes}]})


def test_conceder_revogar_e_auditar(cenario, autenticar):
    assert conceder(cenario, ["consultar", "editar"]).status_code == 200
    dados = cliente.get(f"/api/users/{cenario['usuario']}/document-permissions").json()
    assert dados['vinculos'][0]['permissions'] == ['consultar', 'editar']
    autenticar(cenario['usuario'])
    url = f"/api/documents/{cenario['documento']}"
    assert cliente.get(url + '/details').status_code == 200
    assert cliente.put(url, json={"title": "Título atualizado"}).status_code == 200
    assert cliente.post(url + '/archive').status_code == 403
    with SessionLocal() as db:
        vinculo = db.query(UserDocumentType).filter_by(user_id=cenario['usuario']).one()
        vinculo.permissions = []
        db.commit()
    assert cliente.get(url + '/details').status_code == 403
    assert cliente.put(url, json={"title": "Bloqueado"}).status_code == 403
    with SessionLocal() as db:
        assert db.query(AuditEvent).filter_by(action='permissoes_documentais_alteradas').count() == 1
        assert db.get(GEDDocument, cenario['documento']).title == 'Título atualizado'


@pytest.mark.parametrize('acao', ['consultar', 'cadastrar', 'editar', 'arquivar', 'excluir', 'download'])
def test_concessao_individual(cenario, acao):
    assert conceder(cenario, [acao]).status_code == 200
    with SessionLocal() as db:
        from app.document_permissions import tem_permissao, ACOES
        usuario = db.get(User, cenario['usuario'])
        for candidata in ACOES:
            assert tem_permissao(db, usuario, cenario['tipo'], candidata) == (candidata == acao)


def test_acoes_desconhecidas_e_tipos_duplicados(cenario):
    assert conceder(cenario, ['superpoder']).status_code == 422
    vinculo = {'document_type_id': cenario['tipo'], 'permissions': ['consultar']}
    assert cliente.put(f"/api/users/{cenario['usuario']}/document-permissions",
                      json={'vinculos': [vinculo, vinculo]}).status_code == 422


def test_isolamento_institucional_e_escalada(cenario, autenticar):
    with SessionLocal() as db:
        outra = Institution(id=str(uuid4()), name='Outra', cnpj='456', legal_name='Outra')
        db.add(outra); db.flush()
        gestor = User(id=str(uuid4()), username='gestor', hashed_password='teste',
                      institution_id=outra.id, role='admin_instituicao')
        db.add(gestor); db.commit(); gestor_id = gestor.id
    autenticar(gestor_id)
    assert conceder(cenario, ['excluir']).status_code == 403
    assert cliente.get(f"/api/users/{cenario['usuario']}/document-permissions").status_code == 403
    assert cliente.get(f"/api/documents/{cenario['documento']}/details").status_code == 403
    with SessionLocal() as db:
        db.get(User, gestor_id).institution_id = cenario['instituicao']; db.commit()
    autenticar(gestor_id)
    assert conceder(cenario, ['excluir']).status_code == 403


def test_arquivamento_exige_privilegio_e_estado(cenario, autenticar):
    assert conceder(cenario, ['arquivar']).status_code == 200
    autenticar(cenario['usuario'])
    url = f"/api/documents/{cenario['documento']}/archive"
    assert cliente.post(url).status_code == 200
    assert cliente.post(url).status_code == 409


def test_upload_e_busca_respeitam_privilegios(cenario, autenticar):
    assert conceder(cenario, ['editar']).status_code == 200
    autenticar(cenario['usuario'])
    assert cliente.get('/api/documents/search?q=Histórico').json()['total'] == 0
    resposta = cliente.post('/api/documents/upload', data={'title': 'Teste', 'document_type_id': cenario['tipo']},
                           files={'file': ('teste.pdf', b'%PDF-1.4 teste', 'application/pdf')})
    assert resposta.status_code == 403
    with SessionLocal() as db:
        db.query(UserDocumentType).filter_by(user_id=cenario['usuario']).one().permissions = ['consultar']
        db.commit()
    assert cliente.get('/api/documents/search?q=Histórico').json()['total'] == 1


def test_crud_indices_tipos_e_vinculos():
    indice = cliente.post('/api/indices', json={'name': 'CPF', 'type': 'Texto'}).json()
    tipo = cliente.post('/api/document-types', json={'name': 'Documentos pessoais'}).json()
    assert cliente.put('/api/indices/' + indice['id'], json={'name': 'CPF do aluno', 'type': 'Texto'}).status_code == 200
    url = '/api/document-types/' + tipo['id']
    assert cliente.put(url, json={'name': 'Pessoais', 'is_active': False}).status_code == 200
    assert len(cliente.get(url + '/versions').json()) == 2
    vinculo = cliente.post(url + '/indices', json={'index_id': indice['id'], 'is_required': True}).json()
    assert cliente.post(url + '/indices', json={'index_id': indice['id']}).status_code == 409
    assert len(cliente.get(url + '/indices').json()) == 1
    assert cliente.delete('/api/indices/' + indice['id']).status_code == 409
    assert cliente.put(url + '/indices/' + vinculo['id'], json={'index_id': indice['id'], 'is_unique': True}).status_code == 200
    assert cliente.delete(url + '/indices/' + vinculo['id']).status_code == 204
    assert cliente.delete('/api/indices/' + indice['id']).status_code == 204
    assert cliente.delete(url).status_code == 204


def test_exclusao_bloqueada_por_vinculo(cenario):
    assert cliente.delete('/api/document-types/' + cenario['tipo']).status_code == 409


def test_exclusao_e_download(cenario, autenticar, tmp_path, monkeypatch):
    from app import api_document_operations
    monkeypatch.setattr(api_document_operations, 'STORAGE_ROOT', tmp_path)
    arquivo = tmp_path / 'documento.pdf'; arquivo.write_bytes(b'%PDF-1.4 teste')
    with SessionLocal() as db:
        documento = db.get(GEDDocument, cenario['documento'])
        documento.file_path = str(arquivo); documento.status = GEDDocumentStatus.RASCUNHO
        db.get(DocumentType, cenario['tipo']).legal_hold = True
        db.commit()
    assert conceder(cenario, ['excluir', 'download']).status_code == 200
    autenticar(cenario['usuario'])
    url = f"/api/documents/{cenario['documento']}"
    assert cliente.get(url + '/download').content == b'%PDF-1.4 teste'
    assert cliente.delete(url).status_code == 409
    assert arquivo.exists()
    with SessionLocal() as db:
        db.get(DocumentType, cenario['tipo']).legal_hold = False; db.commit()
    assert cliente.delete(url).status_code == 204
    assert not arquivo.exists()
    with SessionLocal() as db:
        assert db.get(GEDDocument, cenario['documento']) is None


@pytest.mark.parametrize('rota,metodo,dados', [
    ('/api/quarantine/{documento}/release', 'post', None),
    ('/api/quarantine/{documento}', 'delete', None),
    ('/api/documents/{documento}/sign', 'post', {'signer_id': 'inexistente', 'password': 'teste'}),
    ('/api/workflows/instances', 'post', {'document_id': '{documento}', 'workflow_id': 'inexistente', 'current_state_id': 'inexistente'}),
])
def test_rotas_alternativas_exigem_privilegio(cenario, autenticar, rota, metodo, dados):
    with SessionLocal() as db:
        db.get(User, cenario['usuario']).role = 'admin_instituicao'
        db.get(GEDDocument, cenario['documento']).status = GEDDocumentStatus.QUARENTENA
        db.commit()
    assert conceder(cenario, ['consultar']).status_code == 200
    autenticar(cenario['usuario'])
    rota = rota.format(documento=cenario['documento'])
    if dados:
        dados = {k: v.format(documento=cenario['documento']) for k, v in dados.items()}
    resposta = cliente.request(metodo, rota, json=dados)
    assert resposta.status_code == 403, resposta.text


def test_indices_duplicados_e_nomes_vazios():
    dados = {'name': 'CPF', 'type': 'Texto'}
    assert cliente.post('/api/indices', json=dados).status_code == 200
    assert cliente.post('/api/indices', json=dados).status_code == 409
    assert cliente.post('/api/indices', json={'name': ' ', 'type': 'Texto'}).status_code == 422


def test_api_exige_autenticacao(cenario):
    anterior = app.dependency_overrides.pop(get_current_active_user, None)
    try:
        assert cliente.get(f"/api/documents/{cenario['documento']}/details").status_code == 401
        assert cliente.get(f"/api/users/{cenario['usuario']}/document-permissions").status_code == 401
        assert cliente.post(f"/api/documents/{cenario['documento']}/sign", json={'signer_id':'teste', 'password':'teste'}).status_code == 401
    finally:
        if anterior:
            app.dependency_overrides[get_current_active_user] = anterior


def test_edicao_tipo_recusa_nome_duplicado():
    primeiro = cliente.post('/api/document-types', json={'name': 'Primeiro'}).json()
    segundo = cliente.post('/api/document-types', json={'name': 'Segundo'}).json()
    resposta = cliente.put('/api/document-types/' + segundo['id'], json={'name': primeiro['name']})
    assert resposta.status_code == 409
    tipos = cliente.get('/api/document-types').json()['items']
    assert next(t for t in tipos if t['id'] == segundo['id'])['name'] == 'Segundo'


def test_upload_valida_indices_obrigatorios_tipos_mascara_e_unicidade(cenario, autenticar):
    configuracoes = [
        ({'name': 'RGM', 'type': 'Texto', 'mask': r'^RGM-[0-9]{3}$'}, True, True),
        ({'name': 'Modalidade', 'type': 'Lista', 'options': ['Presencial', 'EAD']}, True, False),
        ({'name': 'Data de emissão', 'type': 'Data'}, True, False),
        ({'name': 'Ativo', 'type': 'Booleano'}, False, False),
        ({'name': 'Protocolo', 'type': 'Número', 'auto_increment': True}, True, True),
    ]
    ids = {}
    for dados, obrigatorio, unico in configuracoes:
        indice = cliente.post('/api/indices', json=dados).json()
        ids[dados['name']] = indice['id']
        resposta = cliente.post(f"/api/document-types/{cenario['tipo']}/indices", json={
            'index_id': indice['id'], 'is_required': obrigatorio, 'is_unique': unico})
        assert resposta.status_code == 200, resposta.text
    assert conceder(cenario, ['cadastrar']).status_code == 200
    autenticar(cenario['usuario'])

    def enviar(valores):
        return cliente.post('/api/documents/upload', data={
            'title': 'Histórico indexado', 'document_type_id': cenario['tipo'],
            'indices_json': __import__('json').dumps(valores)},
            files={'file': ('historico.pdf', b'%PDF-1.4 teste', 'application/pdf')})

    assert enviar([]).status_code == 422
    base = [
        {'index_id': ids['RGM'], 'value': 'RGM-001'},
        {'index_id': ids['Modalidade'], 'value': 'Presencial'},
        {'index_id': ids['Data de emissão'], 'value': '2026-09-12'},
        {'index_id': ids['Ativo'], 'value': 'Sim'},
    ]
    assert enviar([*base[:1], {'index_id': ids['Modalidade'], 'value': 'Híbrido'}, *base[2:]]).status_code == 422
    assert enviar([{'index_id': ids['RGM'], 'value': 'inválido'}, *base[1:]]).status_code == 422
    primeira = enviar(base)
    assert primeira.status_code == 200, primeira.text
    assert enviar(base).status_code == 409
    segunda = enviar([{**base[0], 'value': 'RGM-002'}, *base[1:]])
    assert segunda.status_code == 200, segunda.text
    with SessionLocal() as db:
        valores = db.query(__import__('app.models_ged', fromlist=['GEDDocumentIndexValue']).GEDDocumentIndexValue).filter_by(
            index_id=ids['Protocolo']).order_by(
            __import__('app.models_ged', fromlist=['GEDDocumentIndexValue']).GEDDocumentIndexValue.value).all()
        assert [item.value for item in valores] == ['1', '2']


@pytest.mark.parametrize('dados', [
    {'name': 'Lista sem opções', 'type': 'Lista'},
    {'name': 'Texto com opções', 'type': 'Texto', 'options': ['A']},
    {'name': 'Máscara inválida', 'type': 'Texto', 'mask': '['},
    {'name': 'Autonumeração inválida', 'type': 'Data', 'auto_increment': True},
    {'name': 'Tipo desconhecido', 'type': 'Objeto'},
])
def test_configuracao_invalida_de_indice_e_recusada(dados):
    assert cliente.post('/api/indices', json=dados).status_code == 422
