# EduGED Libre (LibreGED) — Portal Modular de Gestão Universitária, Acervo Acadêmico e Diploma Digital

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./LICENSE)
[![Python: 3.13](https://img.shields.io/badge/Python-3.13-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Framework-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL-336791.svg)](https://www.postgresql.org/)
[![Frontend](https://img.shields.io/badge/Frontend-HTML%2FCSS%2FJS-005E7C.svg)](https://developer.mozilla.org/)
[![MEC Compliance](https://img.shields.io/badge/Compliance-Portarias%20MEC%20315%20%7C%20330%20%7C%20554-success.svg)](https://www.gov.br/mec)

O **EduGED Libre** (também identificado como **LibreGED**) é uma plataforma modular integrada de Gestão Eletrônica de Documentos (**GED**), Gestão de Conteúdo Empresarial (**ECM**), Motor de Workflows (**BPMN**), Acervo Acadêmico Digital, Conformidade Regulatória (MEC/LGPD) e Portal de Gestão Universitária por Domínios Funcionais para Instituições de Ensino Superior (IES) e redes educacionais.

O sistema une a **rigidez probatória e regulatória do acervo acadêmico e diploma digital** à **flexibilidade operacional de um portal universitário moderno**, estruturado em módulos independentes com login contextual e governança centralizada.

---

## 📑 Sumário

1. [Visão Geral e Arquitetura](#-visão-geral-e-arquitetura)
2. [Conformidade Regulatória (MEC & LGPD)](#-conformidade-regulatória-mec--lgpd)
3. [Arquitetura Modular do Portal Universitário](#-arquitetura-modular-do-portal-universitário)
4. [Módulos Implementados e Funcionalidades](#-módulos-implementados-e-funcionalidades)
   - [1. SEAD — Secretaria Acadêmica Digital](#1-sead--secretaria-acadêmica-digital)
   - [2. Coordenação de Cursos](#2-coordenação-de-cursos)
   - [3. Professores e Corpo Docente](#3-professores-e-corpo-docente)
   - [4. EAD — Educação a Distância e Polos](#4-ead--educação-a-distância-e-polos)
   - [5. GED, ECM e Acervo Digital](#5-ged-ecm-e-acervo-digital)
   - [6. Motor Visual de Workflows & Trânsito Documental](#6-motor-visual-de-workflows--trânsito-documental)
   - [7. Dossiê Acadêmico e Trava Preventiva de Colação](#7-dossiê-acadêmico-e-trava-preventiva-de-colação)
   - [8. Diploma Digital, Histórico Escolar e Validador XSD MEC](#8-diploma-digital-histórico-escolar-e-validador-xsd-mec)
   - [9. Financeiro e Cobrança Integrada](#9-financeiro-e-cobrança-integrada)
   - [10. Portal do Aluno](#10-portal-do-aluno)
   - [11. Administração Institucional e Governança Global](#11-administração-institucional-e-governança-global)
   - [12. OCR Multi-Engine e Pesquisa Avançada](#12-ocr-multi-engine-e-pesquisa-avançada)
   - [13. Assinatura Digital ICP-Brasil e Auditoria Imutável](#13-assinatura-digital-icp-brasil-e-auditoria-imutável)
   - [14. Ingestão Automatizada ERP & FileWatch](#14-ingestão-automatizada-erp--filewatch)
5. [Segurança, Autenticação Contextual e RBAC](#-segurança-autenticação-contextual-e-rbac)
6. [Roadmap de Evolução e Ideias Futuras](#-roadmap-de-evolução-e-ideias-futuras)
7. [Guia de Instalação e Execução Local](#-guia-de-instalação-e-execução-local)
8. [Estrutura do Repositório](#-estrutura-do-repositório)
9. [Operação e Governança em Produção](#-operação-e-governança-em-produção)
10. [Apoio e Contribuição ao Projeto](#-apoio-e-contribuição-ao-projeto)

---

## 🏛 Visão Geral e Arquitetura

O LibreGED atua como o **motor central de conformidade, custódia documental e gestão operacional** de uma IES, posicionando-se tanto como portal modular de autosserviço (Secretaria, Coordenação, Docentes, Alunos, Financeiro) quanto middleware probatório integrado a sistemas ERP acadêmicos transacionais (TOTVS RM, Lyceum, Sophia, Mentor Web) e órgãos reguladores federais (MEC, Conector RNP, ICP-Brasil).

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
│  │                    Núcleo Institucional & Governança Multitenant                 │  │
│  │         (Instituições, Campi, Auditoria Imutável Hash-Chain, RBAC/Políticas)     │  │
│  └─────────────────────────────────────────┬────────────────────────────────────────┘  │
│                                            │                                           │
│         ┌──────────────────────────────────┴──────────────────────────────────┐        │
│         ▼                                                                     ▼        │
│  ┌──────────────────────────────┐                   ┌───────────────────────────────┐  │
│  │  Portal Modular de Negócio   │                   │  Motor Regulatório & Probatório│ │
│  │  • SEAD (Secretaria Digital) │                   │  • Validador XSD MEC v1.05    │  │
│  │  • Coordenação de Cursos     │                   │  • Diploma Digital XML / XSD  │  │
│  │  • Portal do Professor       │                   │  • Tabela Temporalidade (TTD) │  │
│  │  • EAD & Gestão de Polos     │                   │  • Assinatura ICP-Brasil      │  │
│  │  • Financeiro / Boletos      │                   │  • OCR Tesseract / AWS / Az.  │  │
│  │  • Portal do Aluno           │                   │  • Barramento RNP / XML MEC   │  │
│  └──────────────────────────────┘                   └───────────────────────────────┘  │
└────────────────────────────────────────┬───────────────────────────────────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
          ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
          │   MEC / SERES    │ │   ICP-Brasil     │ │   Conector RNP   │
          │ (Validação XSD)  │ │ (Carimbo/Certif) │ │ (Diploma Digital)│
          └──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## ⚖ Conformidade Regulatória (MEC & LGPD)

O LibreGED atende às exigências das principais portarias e normativas vigentes para o Ensino Superior Brasileiro:

- **Portaria MEC nº 315/2018:** Digitalização e gestão integral do acervo acadêmico em formato digital com integridade e autenticidade.
- **Portaria MEC nº 330/2018:** Emissão e registro de Diploma Digital em formato nativamente digital (XML padronizado).
- **Portaria MEC nº 554/2019:** Especificações técnicas da assinatura digital no padrão ICP-Brasil e carimbo do tempo para emissão do Diploma Digital.
- **Nota Técnica MEC nº 13/2022 (Histórico Escolar Digital v1.05):** Estrutura e validação de esquemas XSD MEC para histórico escolar digital com resolução local de esquemas e normalização de namespaces W3C.
- **LGPD (Lei nº 13.709/2018):** Trilhas de auditoria que registram metadados de modificação sem expor dados pessoais sensíveis, anonimização seletiva e segregação de acesso por contexto.

---

## 🌐 Arquitetura Modular do Portal Universitário

A aplicação foi organizada no modelo de **núcleo institucional compartilhado + módulos funcionais autônomos**, cada um com suas regras de negócio, APIs protegidas e interfaces dedicadas:

```
Instituição (IES)
├── SEAD — Secretaria Acadêmica Digital
├── Coordenação de Cursos
├── Professores
├── EAD — Educação a Distância e Polos
├── GED & Documentos (ECM)
├── Financeiro
├── Portal do Aluno
├── Administração (Transversal e Governança)
└── Núcleo Compartilhado (Autenticação, Instituições, Campi, Trilha de Auditoria, Documentos e Dados Acadêmicos)
```

### Princípios da Arquitetura:
- **Login com Seleção Prévia de Módulo:** O usuário escolhe o domínio operacional no login; o token JWT recebe o contexto de módulo, papel (`role`), `institution_id` e `campus_id`.
- **Autorização Contextual em Duas Camadas:** Acesso ao módulo no nível do gateway/rota, seguido de validação granular por instituição, campus e atribuição vigente do profissional.
- **Auditoria Transparente e Segura:** Registro de eventos estruturados com histórico de mudanças de situação e campos alterados, preservando a privacidade dos dados de identificação.

---

## 🧩 Módulos Implementados e Funcionalidades

### 1. SEAD — Secretaria Acadêmica Digital
Módulo responsável pela vida acadêmica do estudante, registros institucionais e conformidade curricular:
- **Gestão de Alunos e Responsáveis:** Cadastro completo com histórico de alterações auditado, dados exigidos pelo histórico MEC (nome social, naturalidade, nacionalidade e RG) e consulta de linha do tempo via `GET /api/students/{id}/history`.
- **Matrículas e Rematrículas:** Fluxo de matrícula com reserva de vaga em estado `pending` para aprovação da Coordenação, conclusão com registro de situação e snapshots históricos completos.
- **Transferência Acadêmica:** Endpoint `POST /secretaria/academico/matriculas/{id}/transferir` para transferência de turmas validando pré-requisitos, matriz curricular e capacidade de sala, com encerramento automático do vínculo de origem e auditoria completa.
- **Matrizes Curriculares Versionadas:** Gestão de matrizes com controle de pré-requisitos, grupos optativos por créditos mínimos e regras de equivalência de disciplinas.
- **Progresso Curricular do Aluno:** Painel de integralização curricular detalhando créditos obrigatórios e optativos cumpridos e pendentes.
- **Aproveitamento de Estudos (Dispensa/Equivalência):** Solicitação, documentação probatória e análise com reflexo automático na integralização curricular.
- **Extrato Acadêmico Informativo:** Reunião consolidada de notas, frequências e aproveitamentos deferidos com rastreabilidade de decisões e diagnóstico de inconsistências docentes.
- **Perfis Regulatórios IES e Curso:** Cadastro persistido com códigos e-MEC, dados da mantenedora, endereços de oferta e atos autorizativos com datas e veículos de publicação.
- **Atribuição de Responsabilidades:** Vínculo formal de coordenadores e docentes a cursos e campi com períodos de vigência, bloqueando sobreposições conflitantes.

### 2. Coordenação de Cursos
Focado na gestão pedagógica e operacional dos cursos sob responsabilidade do coordenador:
- **Aprovação de Matrículas Pendentes:** Fila de matrículas em estado `pending` com validação de escopo por curso/campus e transição auditada para `active`.
- **Deliberação de Aproveitamento de Estudos:** Painel de decisões para pedidos de dispensa e equivalência com registro formal de parecer, usuário revisor e trilha de auditoria imutável.
- **Gestão de Pendências Acadêmicas:** Criação, atribuição, prazos de prioridade e resolução de pendências operacionais vinculadas aos alunos do curso.
- **Acompanhamento Integrado do Aluno:** Visão integrada reunindo dados acadêmicos, matrículas vigentes, histórico de solicitações, pendências operacionais e status financeiro unificado (`matriculado` / `pendente`).

### 3. Professores e Corpo Docente
Ambiente didático com escopo estrito às turmas sob responsabilidade do docente:
- **Turmas e Frequência:** Chamada diária persistida por data e aluno, com registro de presença/ausência e auditoria.
- **Lançamento de Avaliações e Notas:** Criação de avaliações com controle de pontuação máxima, notas por estudante e cálculo automático de desempenho.
- **Segurança de Acesso Docente:** Bloqueio automático de turmas inativas ou fora do escopo de campus e alocação do docente autenticado.
- **Dados Histórico Docente:** Registro de metadados obrigatórios exigidos pelo XSD do MEC (titulação acadêmica, CPF e Lattes opcional com privacidade preservada).

### 4. EAD — Educação a Distância e Polos
Operação de ensino remoto e acompanhamento de polos de apoio presencial:
- **Polos e Tutores:** Alocação de tutores e coordenação de polos regionais conectados à base acadêmica comum da SEAD.
- **Calendário e Atividades Remotas:** Acompanhamento de entregas de atividades virtuais, avaliações a distância e monitoramento de participação.

### 5. GED, ECM e Acervo Digital
Gestão eletrônica de documentos e ciclo de vida probatório:
- **Tabela de Temporalidade Documental (TTD):** Destinação final (guarda permanente, eliminação, microfilmagem), prazos na fase corrente e intermediária conforme normas do CONARQ e MEC.
- **Estrutura ECM Colaborativa:** Organização em Espaços, Pastas, Tags e Metadados customizados por tipologia documental.
- **Versionamento Rigoroso de Arquivos:** Histórico de versões numeradas sequencialmente com hash SHA-256 por versão, bloqueio de sobreescrita destrutiva e trilha de autoria.
- **Legal Hold (Bloqueio Jurídico):** Congelamento preventivo de exclusão e expurgo para documentos vinculados a processos jurídicos ou auditorias.
- **Emissão e Controle de 2ª Via:** Emissão com carimbo automático de segunda via, cancelamento formal da via anterior e justificativa auditada.

### 6. Motor Visual de Workflows & Trânsito Documental
- **Modelador Visual no Frontend:** Editor interativo de workflows com nós, transições de estado, condições de roteamento e raias de responsabilidade (*swimlanes*).
- **Roteamento de Trânsito Documental:** Notificação automática, despacho entre setores acadêmicos, validação prévia de anexos e prazos de SLA.

### 7. Dossiê Acadêmico e Trava Preventiva de Colação
- **Validação Estrutural Completa:** Verificação automática de documentos obrigatórios do aluno (Identidade, CPF, Certidão de Nascimento/Casamento, Histórico Escolar do Ensino Médio, Título de Eleitor, Certificado Militar, Quitação Eleitoral).
- **Trava de Colação e Emissão:** Bloqueio sistêmico que impede a inclusão do formando em ata de colação de grau ou geração do diploma se o dossiê contiver pendências ou documentos não validados.

### 8. Diploma Digital, Histórico Escolar e Validador XSD MEC
- **Validador Local de Histórico v1.05 MEC:** Rota `POST /api/xsd/validator/historico/v1.05` com resolução local de esquemas auxiliares e normalização em memória de identificadores do W3C.
- **Diploma Digital XML:** Preparação estrutural para geração dos XMLs de Emissão e Registro com conformidade aos esquemas oficiais da Portaria MEC 554/2019.
- **Representação Visual do Diploma Digital (RVDD):** Geração e conferência de metadados para confecção da representação visual com QR Code e código de validação.

### 9. Financeiro e Cobrança Integrada
- **Boletos e Cobranças:** Gestão de faturas, contratos acadêmicos, status de pagamento e inadimplência.
- **Integração com a Matrícula:** Verificação cruzada entre financeiro, coordenação e secretaria na renovação de matrícula e rematrícula.

### 10. Portal do Aluno
- **Autoatendimento:** Consulta de notas, faltas, situação cadastral e progresso curricular.
- **Documentos e Requerimentos:** Envio de documentos comprobatórios para a Secretaria e solicitação de serviços acadêmicos.

### 11. Administração Institucional e Governança Global
- **Multi-Tenancy e Campi:** Gestão multi-instituição com segregação rígida por campus e mantenedora.
- **Governança de Usuários e Perfis:** Atribuição de permissões granulares respeitando a hierarquia institucional.
- **Configurações Gerais do Sistema:** Parâmetros de armazenamento, políticas de senha e limites de upload.

### 12. OCR Multi-Engine e Pesquisa Avançada
- **Multi-Engine OCR:** Suporte a Tesseract OCR (local/on-premise), AWS Textract e Azure Computer Vision para extração de texto em documentos digitalizados.
- **Busca Semântica e Indexação:** Pesquisa textual completa por metadados, termos no corpo dos documentos digitalizados e filtros por período letivo.

### 13. Assinatura Digital ICP-Brasil e Auditoria Imutável
- **Assinatura Padrão ICP-Brasil:** Preparado para assinaturas nos formatos CAdES, XAdES e PAdES com carimbo do tempo (*timestamping*).
- **Trilha de Auditoria Imutável (Hash-Chain):** Encadeamento criptográfico onde cada registro de auditoria contém o hash do evento anterior, impedindo alterações retroativas nos logs.

### 14. Ingestão Automatizada ERP & FileWatch
- **Daemon FileWatch:** Monitoramento de diretórios de rede para captura automática de documentos e relatórios gerados por ERPs acadêmicos legados.
- **Integração via REST API:** Webhooks e rotas autenticadas para alimentação de cadastros e importação de bases de estudantes.

---

## 🔐 Segurança, Autenticação Contextual e RBAC

O controle de acesso combina papéis do usuário com escopos de contexto institucional:

| Papel | Módulos Autorizados | Escopo de Acesso |
| :--- | :--- | :--- |
| `admin_global` | Todos os módulos | Transversal / Global em todas as IES |
| `admin_instituicao` | Todos os módulos | Restrito à sua Instituição e Campi |
| `secretaria` | SEAD, GED | Instituição e Campus vinculados |
| `coordenador` | Coordenação, SEAD (consulta) | Cursos e Campi sob sua responsabilidade vigente |
| `professor` | Professores, EAD | Turmas ativas atribuídas ao docente |
| `tutor` | EAD | Polos e atividades sob sua tutoria |
| `aluno` | Portal do Aluno | Exclusivo para seus dados e matrículas |

---

## 🚀 Roadmap de Evolução e Ideias Futuras

O LibreGED possui um plano contínuo de aprimoramentos para atender a cenários de grande escala e conformidade total:

```
[Fase Atual: Protótipo Funcional Modular & Validador MEC Local]
                                │
                                ▼
[Fase 1: Persistência Robusta & Migrações Completas]
  ├── Transição completa de dados em memória para PostgreSQL com Alembic
  ├── Expansão de modelos relacionais para Matrizes Curriculares, Dossiês e TTD
  └── Conexão total das páginas web aos endpoints REST persistidos
                                │
                                ▼
[Fase 2: Conector Oficial RNP & Diploma Digital ICP-Brasil]
  ├── Assinatura XML em lote com certificados ICP-Brasil (A1 / A3 / HSM)
  ├── Integração com barramento do Conector do Diploma Digital da RNP
  └── Emissão automática do XML de Registro e XML de Histórico validado
                                │
                                ▼
[Fase 3: Reconhecimento Inteligente por IA (Vision & NLP)]
  ├── OCR com classificação automática de tipologia documental via IA
  ├── Extração automática de dados de RGs, CPFs e Históricos Escolares
  └── Detecção preventiva de fraudes documentais em diplomas externos
                                │
                                ▼
[Fase 4: Portal Mobile & Experiência Omnichannel]
  ├── Aplicativo mobile PWA para o Portal do Aluno e Professor
  ├── Notificações via WhatsApp/Push de pendências acadêmicas e boletos
  └── Carteirinha Estudantil Digital com padrão nacional (ITIE/DNE)
```

---

## 💻 Guia de Instalação e Execução Local

### Pré-requisitos
- **Python 3.13+** instalado
- **PostgreSQL 14+** (opcional para persistência avançada)
- Navegador web atualizado (Chrome, Firefox, Edge)

### 1. Clonar o Repositório e Preparar o Ambiente
No terminal (PowerShell no Windows ou Bash no Linux):
```powershell
git clone https://github.com/sachelaride/LibreGED.git
cd LibreGED

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
```

### 2. Configurar Variáveis de Ambiente
Crie o arquivo `backend/.env` caso deseje conexão com banco relacional:
```env
DATABASE_URL=postgresql://postgres:suasenha@localhost:5432/eduged_libre
SECRET_KEY=sua_chave_secreta_jwt_super_segura_32_bytes_minimo
ALGORITHM=HS256
MAX_UPLOAD_SIZE_BYTES=10485760
```

### 3. Execução dos Serviços

> [!IMPORTANT]
> O backend e o frontend devem ser iniciados manualmente pelo usuário em terminais separados conforme sua conveniência.

**Terminal 1 — Backend (FastAPI):**
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```
- API Docs interativa (Swagger): `http://localhost:8000/docs`
- Validador XSD MEC: `http://localhost:8000/api/xsd/validator/historico/v1.05`

**Terminal 2 — Frontend:**
```powershell
Set-Location frontend
python -m http.server 5500
```
- Acesso ao Portal: `http://localhost:5500/login.html`
- Painel Administrativo: `http://localhost:5500/admin.html`
- Painel Operacional: `http://localhost:5500/app.html`

### 4. Credenciais de Demonstração
| Usuário | Senha | Módulo Recomendado |
| :--- | :--- | :--- |
| `admin` | `admin123` | Administração / Transversal |
| `secretaria` | `secretaria123` | SEAD (Secretaria Digital) |
| `coordenador` | `coordenacao123` | Coordenação de Cursos |
| `professor` | `professor123` | Portal do Professor |
| `ged` | `ged123` | GED & Documentos |
| `financeiro` | `financeiro123` | Financeiro |
| `aluno` | `aluno123` | Portal do Aluno |

### 5. Execução dos Testes Automatizados
```powershell
Set-Location backend
..\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
```

---

## 📂 Estrutura do Repositório

```text
LibreGED/
├── backend/
│   ├── app/
│   │   ├── main.py                     # Inicialização da aplicação e roteamento central
│   │   ├── auth.py                     # Regras de autenticação JWT, papéis e RBAC
│   │   ├── models.py                   # Modelos relacionais (Usuários, Instituições, etc.)
│   │   ├── models_academic.py          # Modelos de matrículas, turmas, alunos e históricos
│   │   ├── models_academic_catalog.py  # Modelos de matrizes curriculares e equivalências
│   │   ├── modules/                    # Routers e regras funcionais por domínio
│   │   │   ├── secretaria/             # Endpoints da Secretaria Acadêmica Digital (SEAD)
│   │   │   ├── coordenacao/            # Endpoints da Coordenação de Cursos
│   │   │   ├── professores/            # Endpoints de turmas, notas e chamadas
│   │   │   ├── ged/                    # Endpoints de gestão documental e TTD
│   │   │   ├── financeiro/             # Endpoints financeiros e boletos
│   │   │   ├── aluno/                  # Endpoints do portal do estudante
│   │   │   └── data_store.py           # Repositório de dados em memória e dados demo
│   │   ├── services/                   # Serviços de OCR, auditoria e diploma digital
│   │   └── schemas/                    # Validação de schemas Pydantic
│   ├── tests/                          # Suíte de testes automatizados unitários e integração
│   └── requirements.txt                # Dependências Python
├── frontend/
│   ├── login.html                      # Tela de seleção de módulo e autenticação
│   ├── app.html                        # Portal central da instituição
│   ├── admin.html                      # Painel administrativo transversal
│   ├── css/                            # Folhas de estilo do portal
│   ├── js/                             # Controladores JavaScript do frontend
│   └── modules/                        # Interfaces específicas por domínio funcional
├── docs/                               # Manuais de governança e guias operacionais
├── LICENSE                             # Licença GPL v3
└── README.md                           # Documentação central do projeto
```

---

## 🔒 Operação e Governança em Produção

Para orientações avançadas sobre sustentação e conformidade institucional:
- [Runbook de Produção (docs/PRODUCTION_RUNBOOK.md)](./docs/PRODUCTION_RUNBOOK.md)
- [Governança de Segurança e Acessos (docs/SECURITY_GOVERNANCE.md)](./docs/SECURITY_GOVERNANCE.md)
- [Checklist do Projeto e Manuais (projeto - manual e dicas/)](./projeto%20-%20manual%20e%20dicas/)

---

## 🤝 Apoio e Contribuição ao Projeto

O **EduGED Libre** é um projeto de código aberto disponibilizado para fortalecer a gestão universitária e facilitar o cumprimento das exigências do MEC pelas IES brasileiras.

- **Mantenedor Principal:** German Sachelaride
- **E-mail de Contato:** [sachelaride@gmail.com](mailto:sachelaride@gmail.com)

Contribuições voluntárias para manutenção contínua e expansão dos validadores MEC:
- **Chave PIX (Telefone/Aleatória):** `558252491-68`
- **Favorecido:** German Sachelaride

---

*Licenciado sob os termos da GNU General Public License v3.0 ([LICENSE](./LICENSE)).*
