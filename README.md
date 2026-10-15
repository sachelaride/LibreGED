# EduGED Libre (LibreGED) — Gestão Eletrônica de Documentos, Acervo Acadêmico e Diploma Digital

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./LICENSE)
[![Python: 3.13](https://img.shields.io/badge/Python-3.13-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)](https://www.postgresql.org/)
[![MEC Compliance](https://img.shields.io/badge/Compliance-Portarias%20MEC%20315%20%7C%20330%20%7C%20554-success.svg)](https://www.gov.br/mec)

O **EduGED Libre** (também identificado como **LibreGED**) é uma plataforma completa e integrada de Gestão Eletrônica de Documentos (**GED**), Gestão de Conteúdo Empresarial (**ECM**), Motor de Workflows (**BPMN**) e Conformidade com o Acervo Acadêmico e Diploma Digital para Instituições de Ensino Superior (IES) brasileiras.

O sistema foi arquitetado desde as suas fundações para garantir integridade probatória, temporalidade documental (TTD), rastreabilidade criptográfica de ponta a ponta e aderência rigorosa às normas regulamentadoras do Ministério da Educação (**MEC**) e à Lei Geral de Proteção de Dados (**LGPD**).

---

## 📑 Sumário

1. [Visão Geral e Arquitetura](#-visão-geral-e-arquitetura)
2. [Conformidade Regulatória (MEC & LGPD)](#-conformidade-regulatória-mec--lgpd)
3. [Funções do Sistema (Módulos Implementados)](#-funções-do-sistema-módulos-implementados)
   - [GED & Gestão de Documentos](#1-ged--gestão-de-documentos-e-temporalidade)
   - [ECM & Repositório Colaborativo](#2-ecm--repositório-colaborativo-estilo-share)
   - [Motor Visual de Workflows & Trânsito Documental](#3-motor-visual-de-workflows--trânsito-documental)
   - [Diploma Digital e Histórico Escolar](#4-diploma-digital-histórico-e-currículo-mec)
   - [Dossiê Acadêmico e Consistência](#5-dossiê-acadêmico-e-validação-preventiva)
   - [OCR Multi-Engine & Busca Avançada](#6-ocr-multi-engine--pesquisa-avançada)
   - [Assinatura Digital ICP-Brasil & Auditoria Imutável](#7-assinatura-digital-icp-brasil--auditoria-imutável)
   - [Operações Documentais Avançadas](#8-operações-documentais-avançadas-legal-hold-2ª-via)
   - [Ingestão ERP & FileWatch](#9-ingestão-automatizada-erp--filewatch)
   - [Multi-Tenancy & Controle de Acesso (RBAC)](#10-multi-tenancy-segregação-institucional-e-rbac)
4. [Previsões e Roadmap de Evolução](#-previsões-e-roadmap-de-evolução)
5. [Melhorias Recomendadas para o Sistema](#-melhorias-recomendadas-para-o-sistema)
6. [Guia de Instalação e Execução Local](#-guia-de-instalação-e-execução-local)
7. [Operação e Governança em Produção](#-operação-e-governança-em-produção)
8. [Apoio e Contribuição ao Projeto](#-apoio-e-contribuição-ao-projeto)

---

## 🏛 Visão Geral e Arquitetura

O LibreGED atua como o **motor central de conformidade e custódia documental** de uma IES, posicionando-se entre os sistemas transacionais acadêmicos (ERPs como TOTVS RM, Lyceum, Sophia, Mentor Web) e os órgãos reguladores e registradores (MEC, Conector RNP, ICP-Brasil).

```
                      ┌────────────────────────────────────────┐
                      │        Sistemas ERP Acadêmicos         │
                      │   (Alunos, Matrículas, Notas, Cargas)  │
                      └───────────────────┬────────────────────┘
                                          │ FileWatch / Webhooks / REST API
                                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 LIBREGED / EDUGED LIBRE                                │
│                                                                                        │
│  ┌─────────────────────────┐  ┌─────────────────────────┐  ┌────────────────────────┐  │
│  │   Dossiê Acadêmico      │  │  Motor de Workflows     │  │   ECM & Repositório    │  │
│  │   (Trava de Colação &   │  │  (BPMN, Swimlanes,      │  │   (Espaços, Pastas,    │  │
│  │    Dossiê Completo)     │  │   Tarefas & Trânsitos)  │  │    Tags, Versões)      │  │
│  └────────────┬────────────┘  └────────────┬────────────┘  └───────────┬────────────┘  │
│               │                            │                           │               │
│               ▼                            ▼                           ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                      Núcleo GED & Validação Fail-Closed                          │  │
│  │      TTD • Hash SHA-256 • OCR Multi-Engine • Schemas XSD • Quarentena            │  │
│  └─────────────────────────────────────────┬────────────────────────────────────────┘  │
│                                            │                                           │
│  ┌─────────────────────────┐  ┌────────────┴────────────┐  ┌────────────────────────┐  │
│  │  Geração XML MEC        │  │  Cadeia de Auditoria    │  │  Cofre de Assinaturas  │  │
│  │  (Diploma, Histórico,   │  │  (Hash Encadeado SHA256 │  │  (ICP-Brasil, PAdES,   │  │
│  │   Currículo, RVDD)      │  │   LGPD / Compliance)    │  │   Timestamp Carimbo)   │  │
│  └────────────┬────────────┘  └─────────────────────────┘  └───────────┬────────────┘  │
└───────────────┼────────────────────────────────────────────────────────┼───────────────┘
                │                                                        │
                ▼                                                        ▼
┌───────────────────────────────┐                        ┌───────────────────────────────┐
│     Conector RNP / MEC        │                        │    Consulta Pública / QR      │
│  (Registro e Preservação)     │                        │  (Validação de Autenticidade) │
└───────────────────────────────┘                        └───────────────────────────────┘
```

---

## 📜 Conformidade Regulatória (MEC & LGPD)

O LibreGED cobre nativamente todas as exigências das seguintes legislações e portarias federais:

1. **Portaria MEC nº 315/2018 (Acervo Acadêmico Digital):**
   - Digitalização certificada e guarda segura de toda a documentação comprobatória da vida acadêmica do aluno (desde o ingresso e matrícula até a conclusão).
   - Gestão estrita da Tabela de Temporalidade Documental (TTD).
   - Metadados obrigatórios e resolução de guarda permanente contra perdas físicas ou digitais.

2. **Portarias MEC nº 330/2018, nº 554/2019 e nº 1.095/2018 (Diploma Digital & Histórico Escolar):**
   - Geração dos quatro arquivos XML padronizados e validados pelos esquemas XSD vigentes do MEC:
     - **XML do Diploma Digital**
     - **XML do Histórico Escolar**
     - **XML do Currículo Escolar**
     - **XML da Documentação Acadêmica para Registro**
   - Assinatura digital no padrão ICP-Brasil com suporte a carimbo do tempo (timestamping).
   - Representação Visual do Diploma Digital (**RVDD**) em PDF/A com código de validação e QR Code legível.

3. **Portaria MEC nº 1.001/2021 e Notas Técnicas:**
   - Padronização de procedimentos para emissão de 2ª via, revogação e suspensão fundamentadas em atos administrativos legais.

4. **LGPD (Lei nº 13.709/2018):**
   - Minimização de dados expostos em logs e consultas públicas.
   - Mascaramento e redação automática de dados sensíveis (`privacy_utils`).
   - Trilha de auditoria criptograficamente blindada para fins de compliance e prestação de contas.

---

## ⚙️ Funções do Sistema (Módulos Implementados)

### 1. GED — Gestão de Documentos e Temporalidade
- **Catálogo de Tipos Documentais:** Cadastro estruturado de tipos (ex.: RG, CPF, Certidão de Nascimento, Histórico do Ensino Médio, Contrato Educacional, Ata de Colação).
- **Metadados e Índices Personalizados:** Criação de campos customizados por tipo documental com máscaras (CPF, Data, Matrícula) e validação por expressões regulares (regex).
- **Tabela de Temporalidade Documental (TTD):**
  - Definição de prazos de guarda na fase corrente e fase intermediária.
  - Destinação final automatizada: expurgo controlado ou recolhimento para guarda permanente.
  - Verificação de violações de retenção (`/api/documents/retention/check`) e rotinas de expurgo/arquivamento com modo *dry-run* simulado.
- **Validação Rigorosa de Uploads:** Análise em tempo real de extensão, tipo MIME e assinatura binária (*magic bytes*), impedindo a renomeação maliciosa de arquivos.
- **Cálculo de Integridade:** Hash SHA-256 gerado automaticamente no upload e armazenado de forma imutável para conferência de autenticidade.

### 2. ECM — Repositório Colaborativo (Estilo Share)
- **Espaços Colaborativos (Sites):** Criação de áreas departamentais (ex.: Secretaria Geral, Financeiro, Coordenação de Curso, Auditoria).
  - Níveis de visibilidade: *Público* (toda a IES), *Moderado* (solicitação de acesso) ou *Privado* (apenas convidados).
  - Gestão de membros com perfis de Administrador do Site, Colaborador ou Consumidor.
- **Biblioteca de Documentos Hierárquica:** Navegação em árvore de pastas e subpastas com contadores dinâmicos de arquivos.
- **Controle de Versão Estrito:** Versionamento contínuo com geração de novas versões a cada substituição de arquivo, mantendo o histórico de revisões acessível.
- **Tags e Categorização:** Sistema de rotulagem transversal para agrupamento ágil de documentos independente da estrutura de pastas.

### 3. Motor Visual de Workflows & Trânsito Documental
- **Designer Visual Baseado em Drawflow:** Canvas interativo estilo BPMN para modelagem visual de processos com suporte a *Swimlanes* (raias organizadas por setor ou papel).
- **Tipos de Nós:** Nós de Início (*Start*), Tarefas Operacionais (*Task*), Portais de Decisão/Aprovação (*Review*) e Nós de Conclusão (*End*).
- **Transições Condicionais e Rotas Inteligentes:** Configuração de regras de transição com base em variáveis, código de ação e restrição de permissão por papel (RBAC).
- **Tarefas Dinâmicas:** Atribuição de tarefas para usuários específicos, grupos de permissão ou papéis, com suporte a formulários personalizados (`task_form_key`) e prazos de vencimento (`due_date`).
- **Monitor de Trânsito em Tempo Real:** Painel operacional no frontend para acompanhamento de fluxos em andamento, documentos vinculados, histórico de pareceres e finalização de tarefas.
- **Versionamento de Workflows:** Suporte a versões de trânsito (Rascunho `DRAFT`, Publicado `PUBLISHED`, Arquivado `ARCHIVED`) com gravação de *snapshots* JSON para garantir que processos em andamento não sejam corrompidos por alterações na definição do fluxo.

### 4. Diploma Digital, Histórico e Currículo (MEC)
- **Geração de XMLs Estruturados:** Motor automatizado que constrói os arquivos XML conforme os esquemas XSD oficiais do MEC.
- **Mecanismo Fail-Closed em Schemas XSD:** Sistema de proteção preventiva que bloqueia a geração ou validação de qualquer XML caso o arquivo XSD correspondente não esteja aprovado, vigente ou devidamente cadastrado no cofre de schemas.
- **Templates RVDD (Representação Visual do Diploma Digital):** Editor e motor de renderização de modelos HTML/Jinja2 para transformar o XML assinado em PDF/A oficial pronto para impressão ou download, acompanhado de código de validação e QR Code.
- **Consulta Pública:** Endpoint aberto (`/api/public/verify/{validation_code}`) permitindo que terceiros ou empregadores validem a autenticidade e o estado do diploma em tempo real.

### 5. Dossiê Acadêmico e Validação Preventiva
- **Dossiê Completo do Aluno:** Agrupamento de toda a documentação da vida universitária vinculada à matrícula.
- **Bloqueio Prévio de Diplomação:** Algoritmo que audita a completude do dossiê e impede o avanço de fluxos de colação de grau ou emissão de diploma caso documentos essenciais e obrigatórios (RG, histórico escolar anterior, certificado de conclusão) estejam ausentes ou pendentes de validação.
- **Validação Cruzada de Metadados:** Verificação de consistência entre dados cadastrais do aluno e o conteúdo dos documentos anexados.

### 6. OCR Multi-Engine & Pesquisa Avançada
- **Seleção Inteligente de OCR:** Motor unificado com seleção automática e estratégia de fallback entre múltiplos engines:
  - **PaddleOCR:** Alta precisão para documentos densos e tabelas.
  - **RapidOCR:** Velocidade superior para uploads volumosos.
  - **Tesseract:** OCR tradicional amplamente compatível.
- **Extração de Texto e Metadados:** O texto extraído alimenta diretamente os índices de busca full-text.
- **Pesquisa Avançada (Elasticsearch / Memória):**
  - Busca facetada combinando termos de texto completo, metadados dinâmicos JSONB, filtros por aluno, grupo documental, datas e status.
  - Resposta ultrarrápida (<100ms) com fallback transparente para mecanismo in-memory quando o Elasticsearch não estiver configurado.

### 7. Assinatura Digital ICP-Brasil & Auditoria Imutável
- **Cofre de Assinaturas & Signatários:** Gestão de certificados digitais (A1/A3), configuração de signatários múltiplos (Reitor, Diretor, Secretário Acadêmico) e controle de ordem de assinatura.
- **Carimbo do Tempo (Timestamp):** Suporte à aposição de carimbo temporal ICP-Brasil para comprovação irrefutável do momento da assinatura.
- **Cadeia de Auditoria Criptografada (Blockchain-like):**
  - Cada evento do sistema (criação, edição, visualização, download, transição de workflow, assinatura) é registrado com um hash SHA-256 encadeado no evento anterior:
    $$\text{Hash}_n = \text{SHA256}(\text{ID}_n + \text{Entidade}_n + \text{Ação}_n + \text{Detalhes}_n + \text{Usuário}_n + \text{Hash}_{n-1})$$
  - Qualquer tentativa de adulteração de registros passados corrompe a assinatura da cadeia e é detectada imediatamente pelo verificador `/api/audit/verify`.
  - Exportação oficial de relatórios de auditoria em CSV para atender fiscalizações e auditorias externas.

### 8. Operações Documentais Avançadas (Legal Hold, 2ª Via)
- **Legal Hold (Bloqueio Cautelar):** Aplicação de trava jurídica sobre documentos envolvidos em sindicâncias, processos administrativos ou judiciais, impedindo que sejam alterados ou eliminados mesmo que atinjam o prazo de expurgo da TTD.
- **Suspensão e Revogação Fundamentada:** Rotinas para suspender temporariamente ou revogar em definitivo documentos acadêmicos, com obrigatoriedade de registrar o motivo legal, data, autoridade responsável e ato formal.
- **Emissão Rastreada de 2ª Via:** Conexão permanente entre a segunda via emitida e a via original, preservando o histórico de alterações e anulando a validade da via anterior.

### 9. Ingestão Automatizada ERP & FileWatch
- **Serviço FileWatch de Monitoramento:** Varredura em segundo plano de diretórios de entrada para processamento automático de arquivos enviados por ERPs externos.
- **Contrato de Ingestão via Manifesto JSON:** Validação estrita de manifestos estruturados contendo `ingestion_id`, `correlation_id`, `document_id`, `institution_id`, `sha256` e tipo documental.
- **Idempotência Garantida:** Reenvios do mesmo pacote não geram duplicidades de documentos.
- **Área de Quarentena Segura:** Pacotes com hash divergente, arquivos corrompidos, extensões proibidas ou ausência de metadados obrigatórios são movidos automaticamente para quarentena para análise administrativa.

### 10. Multi-Tenancy, Segregação Institucional e RBAC
- **Isolamento de Dados Multi-Tenant:** Segregação estrita por Instituição de Ensino Superior (IES) e por Unidade/Campus.
- **Papéis de Usuários (RBAC):**
  - **`admin_global`:** Controle total sobre todo o sistema, cadastro de instituições, configuração de backends de armazenamento, criação de tipos documentais e modelagem de workflows globais.
  - **`admin_instituicao` / `gestor_clinica`:** Gestão exclusiva da sua instituição e seus campi (gestão de colaboradores, acompanhamento de auditoria local, consulta à quarentena e fila de ingestão). Não podem acessar outras IES nem criar administradores globais.
  - **Perfis Operacionais (`secretaria`, `recepcao`, `academico`, `orientador`, `auditor`):** Acesso estritamente delimitado pelas permissões concedidas por tipo documental (Criar, Consultar, Editar, Excluir, Assinar).

---

## 🚀 Previsões e Roadmap de Evolução

O plano de evolução do LibreGED está estruturado em portões de maturidade:

```
┌──────────────────────────┐    ┌──────────────────────────┐    ┌──────────────────────────┐
│  Fase Curto Prazo (G1)   │───▶│  Fase Médio Prazo (G2)   │───▶│  Fase Longo Prazo (G3)   │
│ Conectores & Assinaturas │    │ IA, Portal & Digitaliz.  │    │  BI, SaaS & Interoperab. │
└──────────────────────────┘    └──────────────────────────┘    └──────────────────────────┘
```

### 1. Curto Prazo (Portão G1 — Integrações e Produção)
- **Integração com o Conector RNP:** Automatização do envio dos XMLs de Diploma Digital e Documentação Acadêmica para o ecossistema do Ministério da Educação via RNP.
- **Conectores Prontos para ERPs do Mercado:** Módulos de conexão pré-construídos para TOTVS RM Educacional, Lyceum, Sophia e Mentor Web via Webhooks e mensageria.
- **Assinatura em Nuvem e HSM:** Integração direta com certificados em nuvem (BirdID, SAFE ID, VIDaaS) e módulos de segurança física (HSM) para assinatura massiva em lote.
- **Reconciliação Automática com MEC/RNP:** Verificação diária e atualização de recibos de entrega, protocolos e status de registro no órgão emissor.

### 2. Médio Prazo (Portão G2 — Automação e Experiência)
- **Portal de Autoatendimento do Aluno:** Interface exclusiva onde o aluno acompanha o status do seu diploma, solicita certidões e envia documentos pendentes diretamente para o dossiê.
- **Classificação e Autoclassificação com IA:** Utilização de modelos de linguagem e visão computacional (ex.: Gemini Vision) para identificar automaticamente o tipo do documento digitalizado e extrair campos cruciais (RG, CPF, notas) sem intervenção manual.
- **Digitalização por Lote (Batch Scanning):** Suporte a separadores por código de barras / QR Code para digitalização massiva do acervo físico remanescente.
- **Storage Distribuído S3 / MinIO:** Habilitação nativa de provedores de armazenamento em nuvem S3 compatíveis com criptografia de dados em repouso (SSE-KMS).

### 3. Longo Prazo (Portão G3 — Escala e Inovação)
- **BI Acadêmico & Indicadores de Eficiência:** Painéis com métricas preditivas de tempo médio de expedição de diploma, gargalos em etapas de validação e taxa de pendências documentais por curso.
- **Interoperabilidade Federada entre IES:** Protocolo seguro para transferência eletrônica direta de prontuários acadêmicos entre instituições conveniadas.
- **Conformidade Normativa Contínua:** Mecanismo de atualização automatizada de schemas XSD e regras de validação conforme publicação de novas notas técnicas do MEC.

---

## 💡 Melhorias Recomendadas para o Sistema

A análise da arquitetura atual identifica oportunidades para elevar o projeto ao patamar empresarial de alta disponibilidade:

| Categoria | Oportunidade de Melhoria | Benefício Esperado |
| :--- | :--- | :--- |
| **Arquitetura & Escalabilidade** | **Fila Distribuída (Redis / Celery ou RabbitMQ):** Substituir o worker em memória e `repeat_every` por um gerenciador de tarefas distribuído. | Permite balanceamento de carga horizontal e garante que falhas de servidor não interrompam filas de ingestão. |
| **Banco de Dados** | **Índices GIN nos campos JSONB:** Criar índices especializados nas colunas `config_json`, `metadata` e `indices`. | Acelera consultas sobre metadados dinâmicos e filtros de workflows em bases com milhões de registros. |
| **Segurança** | **Cofre de Chaves e Segredos Externo:** Integração com HashiCorp Vault ou AWS Secrets Manager para isolar senhas e chaves privadas. | Protege credenciais do banco e chaves de certificados ICP-Brasil fora de arquivos `.env`. |
| **Autenticação** | **Suporte a SSO Institucional (SAML 2.0 / OpenID Connect / Gov.br):** Permitir login corporativo via Microsoft Entra ID (Azure AD), Google Workspace ou conta Gov.br. | Facilita a adoção pelas universidades e reforça a governança corporativa sem duplicar gestão de senhas. |
| **Frontend & UX** | **Visualizador e Editor de PDF Integrado:** Incluir componente de visualização in-app com marcação de texto e conferência lado a lado com os metadados. | Aumenta a produtividade da secretaria acadêmica ao dispensar o download prévio para conferência. |
| **Auditoria & LGPD** | **Data Loss Prevention (DLP) no Upload:** Varredura adicional durante o upload para identificar e alertar sobre arquivos que contenham dados ultrassensíveis desnecessários. | Reforça a aderência à LGPD e mitiga riscos de vazamento. |
| **Observabilidade** | **Dashboards de Métricas (Prometheus + Grafana):** Integração dos coletores já existentes (`observability.py`) em painéis visuais prontos. | Monitoramento proativo de saturação de disco, latência de OCR e tempo de resposta da API. |

---

## 🛠 Guia de Instalação e Execução Local

### Requisitos Mínimos
- **Sistema Operacional:** Windows 10/11 ou Linux
- **Python:** 3.13 instalado e configurado no PATH
- **Banco de Dados:** PostgreSQL 15+ (Recomendado)
- **Tesseract OCR / Motores de OCR:** (Opcional, com fallback automático)

> [!NOTE]
> Conforme as diretrizes de governança do projeto, o ambiente utiliza execução nativa local (sem obrigatoriedade de contêineres Docker).

### 1. Clonar e Preparar o Ambiente Virtual

```powershell
# Clonar o repositório
git clone https://github.com/sachelaride/LibreGED.git
Set-Location LibreGED

# Criar e ativar o ambiente virtual Python
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalar dependências do backend
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

### 2. Configurar o Banco de Dados PostgreSQL
Crie um banco de dados no PostgreSQL (ex.: `eduged_libre`):
```sql
CREATE DATABASE eduged_libre ENCODING 'UTF8';
```

Crie o arquivo `backend/.env` ou configure as variáveis de ambiente:
```env
DATABASE_URL=postgresql://postgres:suasenha@localhost:5432/eduged_libre
SECRET_KEY=sua_chave_secreta_jwt_super_segura_32_bytes_minimo
ALGORITHM=HS256
MAX_UPLOAD_SIZE_BYTES=10485760
ELASTICSEARCH_ENABLED=false
```

### 3. Executar as Migrações do Banco de Dados (Alembic)
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

*(Opcional)* Carregar dados de demonstração (catálogo documental e workflow de diplomas):
```powershell
..\.venv\Scripts\python.exe scripts/seed_document_catalog.py
..\.venv\Scripts\python.exe scripts/seed_diploma_workflow.py
```

### 4. Inicialização dos Serviços

> [!IMPORTANT]
> O backend e o frontend devem ser iniciados manualmente pelo usuário conforme suas preferências operacionais.

**Terminal 1 — Backend (FastAPI):**
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
- Documentação Interativa (Swagger/OpenAPI): `http://localhost:8000/docs`
- Verificação de Integridade (Health Check): `http://localhost:8000/api/health`

**Terminal 2 — Frontend (Aplicação Web):**
Você pode utilizar qualquer servidor estático ou a extensão *Live Server* do VS Code apontando para a pasta `frontend`:
```powershell
Set-Location frontend
py -m http.server 5500
```
- Interface de Login: `http://localhost:5500/login.html`
- Painel Administrativo: `http://localhost:5500/admin.html`
- Painel Operacional: `http://localhost:5500/app.html`

**Credenciais Padrão de Primeiro Acesso:**
- **Usuário:** `admin`
- **Senha:** `admin123` *(Altere imediatamente no primeiro login em Usuários -> Alterar Senha)*

### 5. Executar a Suíte de Testes Automatizados
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

---

## 🔒 Operação e Governança em Produção

Para implantações corporativas em ambiente real, consulte os manuais específicos disponíveis em:
- [Runbook de Produção (docs/PRODUCTION_RUNBOOK.md)](./docs/PRODUCTION_RUNBOOK.md)
- [Governança de Segurança e Acessos (docs/SECURITY_GOVERNANCE.md)](./docs/SECURITY_GOVERNANCE.md)
- [Documentações Técnicas Adicionais (projeto - manual e dicas/)](./projeto%20-%20manual%20e%20dicas/)

---

## 🤝 Apoio e Contribuição ao Projeto

O **EduGED Libre** é uma iniciativa desenvolvida e disponibilizada abertamente para democratizar o acesso à tecnologia e modernizar a gestão de acervos acadêmicos no Brasil.

Para suporte institucional, consultoria de implantação, personalizações ou parcerias acadêmicas:
- **Mantenedor Principal:** German Sachelaride
- **E-mail de Contato:** [sachelaride@gmail.com](mailto:sachelaride@gmail.com)

Caso você queira apoiar voluntariamente a manutenção contínua, testes com novos esquemas do MEC e desenvolvimento de novos módulos:

- **Chave PIX (Telefone/Aleatória):** `558252491-68`
- **Favorecido:** German Sachelaride
- **E-mail:** [sachelaride@gmail.com](mailto:sachelaride@gmail.com)

Agradecemos imensamente a todos os educadores, arquivistas e desenvolvedores que tornam este projeto cada vez mais forte!

---

*Licenciado sob os termos da GNU General Public License v3.0 or later ([LICENSE](./LICENSE)).*
