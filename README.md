# EduGED Libre: Solução Definitiva para Gestão de Acervo Acadêmico e Diplomas Digitais

O **EduGED Libre** é um sistema de Gestão Eletrônica de Documentos (GED) e ECM (Enterprise Content Management) de código aberto, projetado especificamente para atender de forma estrita às regulamentações do Ministério da Educação (MEC). Seu objetivo central é modernizar e assegurar a conformidade legal das Instituições de Ensino Superior (IES) na digitalização e tramitação de documentos acadêmicos.

## Conformidade com as Portarias do MEC

O sistema foi arquitetado desde o princípio focado em garantir a segurança, integridade, temporalidade e rastreabilidade dos documentos acadêmicos. O EduGED Libre cobre nativamente as exigências das seguintes legislações:

1. **Acervo Acadêmico Digital (Portaria MEC nº 315/2018):**
   - Digitalização e armazenamento seguro de toda a documentação dos alunos (matrícula, RG, CPF, históricos, contratos).
   - Tabela de Temporalidade Documental (TTD) integrada, gerenciando os ciclos de vida de documentos, com expirações programadas e retenções (ex: retenção de 5 anos após conclusão ou transferência).
   - Proteção estrita de dados (RESTRICT) contra deleções de documentos vinculados.

2. **Diploma Digital e Histórico Escolar (Portaria MEC nº 330/2018, 554/2019 e 1.095/2018):**
   - Geração e estruturação nativa de documentos XML exigidos pelo MEC, baseados nos esquemas (XSD) padronizados. Suportamos a geração e validação de:
     - **XML do Diploma Digital**
     - **XML do Histórico Escolar**
     - **XML do Currículo Escolar**
   - Assinatura digital ICP-Brasil e gestão de múltiplos signatários (reitor, secretário acadêmico, etc.).

3. **Auditoria e Segurança (LGPD e Compliance):**
   - Trilha de auditoria criptografada e imutável (hash encadeado).
   - Políticas de controle de acesso (RBAC) para Admin Global, Admin de Instituição, Secretário Acadêmico, Acadêmico e Auditor.
   - Controle de versões (maior e menor) e quarentena para arquivos suspeitos (verificação antimalware).

O EduGED Libre é mais do que um simples repositório; é o motor de consistência acadêmica que impede a diplomação de alunos com pendências documentais (Dossiê Acadêmico) e simplifica vistorias do MEC, entregando dados estruturados, confiáveis e seguros.

---

## 🛠 Guia Técnico e Inicialização

**Estado atual:** Em desenvolvimento ativo. O projeto possui autenticação, autorização e controle de versão, e utiliza infraestrutura de banco de dados robusta.

### Requisitos
- **Python 3.13**
- **PostgreSQL** (Obrigatório: substituiu o SQLite para suportar campos nativos JSONB e integridade referencial avançada)
- Elasticsearch (opcional)

### Preparação
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### Executar a API
Certifique-se de ter um banco PostgreSQL rodando (ex: `eduged_libre` e `eduged_libre_test` para testes).
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
A documentação interativa fica em http://localhost:8000/docs e a verificação de saúde em http://localhost:8000/api/health.

### Executar os testes
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```
A suíte cobre o fluxo acadêmico principal, integridade dos vínculos, uploads versionados, checksum SHA-256, auditoria, busca avançada, retenção e bloqueio de XML sem XSD aprovado.

### Política de upload
O backend aceita apenas os formatos abaixo e confere extensão, MIME e conteúdo:

| Extensão | MIME aceito | Verificação |
| :--- | :--- | :--- |
| `.pdf` | `application/pdf` | Assinatura `%PDF-`. |
| `.xml` | `application/xml`, `text/xml` | XML bem formado, sem DTD ou entidades. |
| `.json` | `application/json` | JSON válido em UTF-8. |
| `.txt` | `text/plain` | Texto UTF-8 sem bytes nulos. |

Arquivos vazios são recusados. O limite padrão é 10 MiB e pode ser alterado por `MAX_UPLOAD_SIZE_BYTES`. Essa variável é temporária para bootstrap: a política deverá ser administrada de forma versionada pela futura Plataforma do Administrador. Essa validação não substitui um serviço antimalware.

### Migrações do banco
Execute sempre a partir do diretório `backend`:

```powershell
# Aplicar todas as migrações
..\.venv\Scripts\python.exe -m alembic upgrade head

# Conferir a revisão atual
..\.venv\Scripts\python.exe -m alembic current

# Criar uma migração depois de alterar os modelos
..\.venv\Scripts\python.exe -m alembic revision --autogenerate -m "descricao"
```
A API não cria tabelas automaticamente. Isso impede que uma inicialização altere o banco por fora do histórico versionado do Alembic.

### Configuração
| Variável | Padrão | Finalidade |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://postgres:suasenha@localhost:5432/eduged_libre` | Conexão SQLAlchemy com PostgreSQL. |
| `ELASTICSEARCH_ENABLED` | `false` | Habilita Elasticsearch; sem ele, a busca usa memória. |
| `ELASTICSEARCH_HOST` | `localhost` | Host do Elasticsearch. |
| `ELASTICSEARCH_PORT` | `9200` | Porta do Elasticsearch. |
| `MAX_UPLOAD_SIZE_BYTES` | `10485760` | Limite máximo de cada upload em bytes. |

Arquivos enviados são gravados localmente em `backend/storage`. A documentação de requisitos e planejamento fica em `projeto - manual e dicas`, mantida fora do controle de versão conforme a regra do `.gitignore`.

---

## Contribuição para o Projeto

O **EduGED Libre** é uma iniciativa desenvolvida e disponibilizada gratuitamente para modernizar e democratizar a gestão da infraestrutura e acervos acadêmicos no Brasil.

Para suporte institucional, implementação, customizações ou qualquer outra colaboração, entre em contato com **German Sachelaride** pelo e-mail [sachelaride@gmail.com](mailto:sachelaride@gmail.com).

Se você utiliza o **EduGED Libre** em sua instituição de ensino e considera o projeto útil, você pode contribuir voluntariamente para o seu desenvolvimento.

Suas contribuições ajudam a apoiar diretamente:
- O desenvolvimento de novas funcionalidades (como IA para leitura de documentos e integração com novos ERPs acadêmicos);
- A manutenção, correção de bugs e evolução do projeto;
- A documentação técnica detalhada;
- Os testes, adequação às novas portarias do governo e a evolução da plataforma;
- A hospedagem e a disponibilidade do projeto aberto para toda a comunidade educacional.

### Como Contribuir

A sua contribuição é totalmente voluntária. O uso livre e gratuito do **EduGED Libre** não depende de nenhuma contribuição financeira. Caso queira apoiar o mantenedor original, utilize a chave abaixo:

**PIX - Brasil**
- **Chave PIX (Telefone/Aleatória):** `558252491-68`
- **E-mail de Contato:** [sachelaride@gmail.com](mailto:sachelaride@gmail.com)

Agradecemos o seu apoio por tornar a educação e a tecnologia mais acessíveis a todos!

### Manifestos do FileWatch

O worker exige o contrato JSON `manifest_version: 1`, com `ingestion_id`,
`correlation_id`, `document_id`, `institution_id`, `file_name`, `content_type`,
`sha256`, `document_type`, `source_system`, `created_at` e `environment`.
Os identificadores de ingest?o, documento e instituição devem ser UUIDs;
`created_at` deve incluir fuso hor?rio. O nome deve coincidir com o PDF do par,
o MIME deve ser `application/pdf` e o SHA-256 deve conter 64 caracteres
hexadecimais min?sculos. Ambientes aceitos: `development`, `test`,
`homologation` e `production`.

`source_event`, `source_user` e o objeto `metadata` s?o opcionais. Campos
extras e versões desconhecidas s?o recusados. Manifestos antigos com apenas
`hash_sha256` precisam ser adaptados; pacotes inválidos seguem para quarentena.
O worker também exige que o documento exista na instituição informada e que o
ambiente coincida com o servidor (`staging` corresponde a `homologation`).
A compatibilidade do tipo documental, a vinculação da nova versão ao documento
e a indexação durável permanecem pendentes. O `ingestion_id` é idempotente:
reentregas do mesmo pacote concluído não criam um novo `IngestionJob`; cargas
com o mesmo identificador e conteúdo divergente seguem para quarentena.

### CRUD e privilégios documentais no administrador

Em **Usuários → Tipos e privilégios**, vincule cada tipo e marque as operações
permitidas. Sem concessão explícita, a API bloqueia a ação. O administrador de
instituição só pode administrar usuários da própria instituição e conceder ações
que possui. Tipos e índices são compartilhados no modelo atual; sua alteração
exige administrador global.

A migração `a17c91b2d430` adiciona os privilégios e preserva somente consulta nos
vínculos antigos. Execute `alembic upgrade head` antes de iniciar a API atualizada.
Edição/exclusão de cadastros em uso é limitada para preservar vínculos; operações
documentais continuam sujeitas ao estado, à retenção e ao legal hold.

A cobertura atual inclui GED, busca, upload e verificações nas rotas de assinatura,
quarentena e workflow. A interface ECM, as permissões funcionais e o CRUD dos
outros módulos ainda precisam de integração. Documentos enviados por usuários
preservam o `campus_id`; ingestões ERP sem campus continuam bloqueadas para
usuários com escopo restrito, até que o campus seja informado pelo conector.
O roteiro de continuidade e exemplos fictícios estão em
`projeto - manual e dicas/PLANO_CRUD_E_PERMISSOES.md`.
