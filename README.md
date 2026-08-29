# LibreGED

API experimental para gestao de documentos educacionais, com cadastro academico,
versionamento de arquivos, auditoria, busca, validacao de versoes XSD e politicas
de retencao.

> Estado atual: MVP em desenvolvimento. O projeto ainda nao deve ser tratado como
> pronto para producao sem autenticacao, autorizacao, migracoes e infraestrutura
> de armazenamento definitiva.

## Requisitos

- Python 3.13
- SQLite para desenvolvimento local (padrao)
- PostgreSQL e Elasticsearch opcionais

## Preparacao

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

## Executar a API

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

A documentacao interativa fica em `http://localhost:8000/docs` e a verificacao
de saude em `http://localhost:8000/api/health`.

## Executar os testes

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

A suite possui 33 testes e cobre o fluxo academico principal, integridade dos
vinculos, uploads versionados, checksum SHA-256,
auditoria, busca avancada, retencao e bloqueio de XML sem XSD aprovado.

## Politica de upload

O backend aceita apenas os formatos abaixo e confere extensao, MIME e conteudo:

| Extensao | MIME aceito | Verificacao |
|---|---|---|
| `.pdf` | `application/pdf` | Assinatura `%PDF-`. |
| `.xml` | `application/xml`, `text/xml` | XML bem formado, sem DTD ou entidades. |
| `.json` | `application/json` | JSON valido em UTF-8. |
| `.txt` | `text/plain` | Texto UTF-8 sem bytes nulos. |

Arquivos vazios sao recusados. O limite padrao e 10 MiB e pode ser alterado por
`MAX_UPLOAD_SIZE_BYTES`. Essa variavel e temporaria para bootstrap: a politica
devera ser administrada de forma versionada pela futura Plataforma do Administrador.
Essa validacao nao substitui um servico antimalware.

## Migracoes do banco

Execute sempre a partir de `backend`:

```powershell
# Aplicar todas as migracoes
..\.venv\Scripts\python.exe -m alembic upgrade head

# Conferir a revisao atual
..\.venv\Scripts\python.exe -m alembic current

# Criar uma migracao depois de alterar os modelos
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "descricao"
```

A API nao cria tabelas automaticamente. Isso impede que uma inicializacao altere
o banco por fora do historico versionado do Alembic.

## Configuracao

| Variavel | Padrao | Finalidade |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./test.db` | Conexao SQLAlchemy; aceita PostgreSQL. |
| `ELASTICSEARCH_ENABLED` | `false` | Habilita Elasticsearch; sem ele, a busca usa memoria. |
| `ELASTICSEARCH_HOST` | `localhost` | Host do Elasticsearch. |
| `ELASTICSEARCH_PORT` | `9200` | Porta do Elasticsearch. |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | Limite maximo de cada upload em bytes. |

Arquivos enviados sao gravados localmente em `backend/storage`. A documentacao
de requisitos e planejamento fica em `projeto - manual e dicas`, mantida fora do
controle de versao conforme a regra do `.gitignore`.
