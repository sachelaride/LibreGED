# LibreGED — Portal modular de gestão universitária

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](./LICENSE)
[![Python 3.13](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-HTML%2FCSS%2FJS-005E7C)](https://developer.mozilla.org/)

O LibreGED começou como uma solução de gestão documental e acadêmica e evoluiu para uma plataforma modular de gestão universitária, estruturada por áreas de negócio, com integração entre secretaria, professores, alunos, GED, financeiro, coordenação e administração.

A abordagem atual do projeto é diferente de um sistema monolítico com um único dashboard. Em vez disso, a aplicação foi organizada como um portal institucional com um núcleo compartilhado e módulos independentes, cada um com sua própria lógica, dados e interface. O objetivo é manter uma base comum para a instituição, mas permitir que cada área opere com autonomia funcional.

A diferenciação entre SEAD e EAD também foi reforçada: a SEAD representa a Secretaria Acadêmica Digital, responsável pela vida acadêmica do aluno, matrículas, processos, históricos e documentos; o EAD representa a Educação a Distância, com polos, tutores, atividades, avaliações e acompanhamento virtual, funcionando como um domínio operacional paralelo e conectado à base acadêmica comum.

O cadastro de alunos e responsáveis mantém eventos de criação e alteração na trilha de auditoria. A Secretaria consulta esses eventos pela ação “Histórico” na lista de alunos; os campos modificados e o usuário responsável são registrados sem gravar ou exibir valores pessoais na linha do tempo. A API autenticada `GET /api/students/{student_id}/history` respeita o escopo institucional e de campus do usuário.

Essa mesma linha do tempo registra, para novas matrículas, snapshots do curso, versão da matriz curricular, disciplina, turma, período letivo e campus associados. Também registra a situação e o resultado quando a disciplina é concluída. Eventos de matrículas antigas que não possuam snapshot são identificados explicitamente como históricos incompletos.

Professores, tutores e coordenadores podem ser mantidos na tela de cadastros acadêmicos, incluindo situação e campus. Criação e alterações registram os campos modificados sem valores pessoais; a linha do tempo fica disponível pela ação “Histórico”. Profissionais inativos não podem ser alocados em novas turmas.

O módulo de Professores usa as turmas, matrículas e cadastros persistentes. A Secretaria vincula a conta ativa de perfil acadêmico ao registro do docente; assim, professores só consultam e alteram avaliações, notas e frequência das turmas atribuídas a eles, respeitando também o campus. Avaliações, notas e chamadas são persistidas e auditadas; as notas respeitam a pontuação máxima e a frequência é registrada por aluno e data.

A Secretaria também pode vincular uma conta acadêmica a um coordenador. No módulo Coordenação, solicitações persistidas de aproveitamento de estudos ficam disponíveis apenas ao responsável pelo curso e campus durante a vigência da atribuição (ou a gestores dentro do seu escopo institucional/campus). A aprovação ou rejeição exige decisão registrada, identifica o usuário revisor e entra na auditoria; pedidos já decididos não podem ser alterados por esse fluxo.

O formulário acadêmico da Secretaria registra matrículas de turma como `pending`, reservando a vaga até a decisão. O módulo Coordenação lista essas matrículas e permite aprová-las individualmente. O escopo segue a atribuição vigente de curso/campus do coordenador ou o escopo institucional/campus de gestores; matrículas sem turma acadêmica não podem ser aprovadas por esse fluxo. A aprovação altera a situação para `active` e registra situação anterior/nova e responsável na auditoria.

O histórico do aluno reúne eventos de cadastro e auditoria das matrículas. Cada evento novo de matrícula preserva o vínculo acadêmico capturado no momento da operação; mudanças de situação também registram estado anterior e novo. Para registros legados sem snapshot, a consulta os apresenta como legado e distingue dados básicos gravados na matrícula de dados reconstruídos a partir do catálogo atual, sem apresentá-los como snapshots históricos.

A Secretaria pode transferir uma matrícula ativa ou pendente para outra turma pelo endpoint `POST /secretaria/academico/matriculas/{enrollment_id}/transferir`, informando `target_class_id`. A operação valida escopo, disponibilidade, capacidade e matriz curricular, encerra o vínculo anterior como `transferred`, cria o destino como `pending` e audita ambos os lados com seus snapshots. Transferência entre campi também atualiza o campus acadêmico do aluno; é bloqueada se houver outras matrículas vigentes em campus incompatível.

Na visão de Coordenação, alunos aparecem vinculados às matrículas, curso, disciplina, turma, período e campus da base acadêmica, dentro do escopo de responsabilidades vigente. Pendências são persistidas com curso/campus, prioridade, prazo, responsável e estados de criação/conclusão; criação, consulta e resolução respeitam as atribuições vigentes e geram eventos de auditoria.

Coordenadores podem receber responsabilidades explícitas por curso e campus com datas inicial e final. A Secretaria permite criar e manter os vínculos; a API `GET/POST /secretaria/academico/responsabilidades-coordenacao` e `PATCH /secretaria/academico/responsabilidades-coordenacao/{assignment_id}` também os consulta e atualiza. Períodos sobrepostos para o mesmo curso/campus são rejeitados e as alterações entram na trilha de auditoria.

---

## Visão geral

O LibreGED hoje funciona como um protótipo funcional de sistema universitário modular, com foco em:

- seleção de módulo antes do login;
- autenticação e autorização por papel e contexto de módulo;
- dashboards dedicados para cada área funcional;
- páginas de módulo com ações rápidas e formulários específicos;
- organização do backend em módulos de negócio;
- dados de demonstração para simular cenários reais de uma instituição de ensino.

A arquitetura está preparada para crescer em direção a um sistema acadêmico completo, mas ainda não é uma solução de produção com persistência completa e regras de negócio totalmente formalizadas para todas as áreas.

---

## Objetivo do projeto

O objetivo principal do projeto é representar uma instituição de ensino como um conjunto de módulos interligados, em vez de um ERP acadêmico único e fragmentado. A ideia é que todos os módulos compartilhem a mesma base institucional, mas mantenham responsabilidades distintas.

Exemplos:

- Secretaria cuida de matrículas, alunos e cadastros;
- Professores lidam com turmas, disciplinas e avaliações;
- GED gerencia documentos, versões, status e arquivos;
- Financeiro controla cobranças, pagamentos e boletos;
- Coordenação acompanha pendências e ações acadêmicas;
- Aluno acessa informações pessoais, matrículas e desempenho;
- Administração centraliza governança e visão transversal.

Esse desenho favorece a clareza organizacional e cria um modelo que pode evoluir para um ambiente com múltiplos perfis, permissões e integrações.

---

## Arquitetura atual

### Estrutura conceitual

A aplicação segue um modelo de núcleo institucional + módulos de negócio.

```
Instituição
├── SEAD — Secretaria Acadêmica Digital
├── EAD — Educação a Distância
├── Professores
├── GED e Documentos
├── Financeiro
├── Coordenação
├── Aluno
├── Administração
└── Núcleo compartilhado (usuários, instituição, campus, documentos, dados acadêmicos)
```

### Princípios da arquitetura

- Separação funcional por domínio;
- reutilização de entidades compartilhadas;
- autenticação contextual por módulo;
- autorização por perfil e acesso ao módulo;
- páginas independentes por área;
- navegação integrada entre os módulos.

---

## Módulos implementados

### 1) SEAD — Secretaria Acadêmica Digital

Foca na vida acadêmica institucional e no atendimento acadêmico.

Inclui:

- matrículas e rematrículas;
- cadastros persistentes de departamentos e setores, organizados por instituição e campus;
- matrizes curriculares versionadas com pré-requisitos, grupos optativos por créditos mínimos e equivalências que podem satisfazer os pré-requisitos da matriz;
- consulta do progresso curricular do aluno, com créditos obrigatórios/optativos e indicação dos requisitos pendentes ou cumpridos;
- solicitação e análise de aproveitamento de estudos, com decisão da Secretaria registrada e aprovação refletida no progresso curricular;
- extrato acadêmico informativo por curso, reunindo resultados de turmas e aproveitamentos deferidos com identificação de origem e decisão; não substitui a emissão do histórico oficial;
- cadastro dos dados de identificação pessoal exigidos no histórico escolar (nome social, naturalidade, nacionalidade e RG), como preparação para emissão;
- cadastro persistido dos perfis regulatórios da IES/mantenedora e do curso (códigos e-MEC, endereços e atos autorizativos/publicações), com validação dos campos obrigatórios;
- pacote MEC v1.05 do histórico escolar no backend, resolução local dos XSD auxiliares e rota de validação `POST /api/xsd/validator/historico/v1.05`; o validador normaliza em memória os identificadores W3C incorretos no pacote publicado, sem alterar os XSD originais. A Secretaria permite registrar ingresso por aluno/curso e metadados dos docentes responsáveis em `GET`/`PUT /secretaria/academico/profissionais/{staff_id}/dados-historico`; o XSD exige titulação e permite CPF e Lattes opcionais. CPF/Lattes não são retornados nas respostas do perfil nem expostos na listagem geral. O extrato aponta docentes não vinculados ou sem titulação. A rota legada de geração de XML do histórico continua bloqueada até que o mapeamento completo dos demais dados acadêmicos e a assinatura XML sejam implementados. Validação XSD isolada não equivale à emissão oficial;
- alterações de ofertas, turmas, horários e alocação docente/coordenador são registradas na trilha de auditoria; horários podem ser editados com revalidação de sobreposição, sala, capacidade e conflito docente. A linha do tempo é consultável na interface da Secretaria pelos botões “Histórico” das listas e pela API `GET /secretaria/academico/historico-alteracoes/{entity_type}/{entity_id}` (`entity_type`: `oferta`, `turma` ou `horario`), respeitando os escopos de instituição/campus;
- processos acadêmicos e requerimentos;
- histórico escolar e documentos acadêmicos;
- acompanhamento de alunos, pendências e validações;
- integração com GED, financeiro e coordenação.

### 2) EAD — Educação a Distância

Foca na operação de ensino remoto e polos/tutoria.

Inclui:

- polos e tutores;
- calendário de aulas e atividades;
- avaliações, frequência e pendências;
- acompanhamento de ensino virtual e integração com a base acadêmica do SEAD.

### 3) Professores

Foca em atividades didáticas e acadêmicas.

Inclui:

- turmas e disciplinas;
- lançamento de notas;
- acompanhamento de frequência;
- visualização de avaliações e dados de turmas.

### 4) GED / Documentos

Foco em gestão documental e ciclo de vida de arquivos.

Inclui:

- documentos com status e categoria;
- versionamento e histórico de documento;
- informações de retenção e classificação;
- painel de gestão documental e ações de operação.

### 5) Financeiro

Foco em fluxo financeiro e cobrança.

Inclui:

- boletos e pagamentos;
- status de cobrança;
- visão geral financeira;
- dados demo para transações e pendências.

### 6) Coordenação

Foco em acompanhamento institucional e pendências acadêmicas.

Inclui:

- ações pendentes;
- responsáveis e prazos;
- classificação por categoria;
- acompanhamento operacional e estratégico.

### 7) Aluno

Foco no portal do estudante.

Inclui:

- painel do aluno;
- matrícula e processos acadêmicos;
- informações pessoais e acadêmicas;
- visão de desempenho e acompanhamento do curso.

### 8) Administração

Trata-se como módulo transversal de governança.

Inclui:

- visão geral administrativa;
- acesso a informações consolidadas;
- suporte a gestão de todos os módulos;
- modelo de administração institucional em conjunto.

---

## Segurança e autenticação

A camada de autenticação foi atualizada para refletir o novo modelo modular.

### Fluxo de login

O processo começa com a seleção do módulo antes do login.

1. Usuário escolhe o módulo no portal;
2. informa usuário e senha;
3. o backend valida as credenciais;
4. o JWT recebe contexto de módulo e papel;
5. rotas protegidas validam o módulo e a permissão do usuário.

### Estratégia atual

Cada token inclui dados como:

- `sub` (identidade do usuário);
- `role` (papel do usuário);
- `module` (módulo ativo);
- `institution_id`;
- `campus_id`.

Isso permite que o sistema aplique regras de acesso, evitando que um usuário accesse um módulo que não pertença ao seu contexto de autenticação.

### Mapeamento de acesso atual

Os papéis operacionais `secretaria`, `coordenador`, `professor`, `tutor` e `aluno` têm acesso apenas aos módulos de sua função: Secretaria/SEAD, Coordenação, Professores, EAD e Portal do Aluno, respectivamente. Professores também podem acessar o módulo EAD. Usuários administrativos (`admin_global` e `admin_instituicao`) mantêm acesso a todos os módulos; os papéis legados `operador`, `academico`, `leitor` e `auditor` continuam aceitos segundo a matriz de compatibilidade centralizada em `backend/app/auth.py`.

O login e as dependências das rotas usam a mesma matriz. A criação e a alteração de usuários rejeitam papéis não reconhecidos. A autorização de módulo é uma primeira camada: as rotas acadêmicas também verificam instituição, campus e vínculos vigentes de professor ou coordenador antes de revelar registros.

---

## Backend

O backend principal está localizado em `backend/app` e usa FastAPI como núcleo da aplicação.

### Estrutura relevante

- `backend/app/main.py` — aplicação principal e registro dos routers;
- `backend/app/auth.py` — regras de autenticação e autorização;
- `backend/app/modules/` — módulos por área funcional;
- `backend/app/modules/data_store.py` — dados demo e contexto do protótipo.

### Routers por módulo

Os módulos foram organizados em arquivos separados:

- `backend/app/modules/secretaria/routes.py`
- `backend/app/modules/professores/routes.py`
- `backend/app/modules/ged/routes.py`
- `backend/app/modules/financeiro/routes.py`
- `backend/app/modules/coordenacao/routes.py`
- `backend/app/modules/aluno/routes.py`

Esses arquivos expõem endpoints para:

- dashboard do módulo;
- listagem de registros;
- criação de novos itens;
- consulta de detalhes;
- fluxo de ações por área.

---

## Frontend

O frontend está organizado em páginas HTML e scripts compartilhados.

### Arquivos centrais

- `frontend/login.html` — primeiro passo do fluxo; módulo + autenticação
- `frontend/app.html` — portal principal da instituição
- `frontend/admin.html` — administrador como módulo de gestão geral
- `frontend/modules/*.html` — páginas por domínio
- `frontend/modules/module-page.js` — comportamento compartilhado das telas
- `frontend/css/style.css` — identidade visual do portal

### Fluxo do usuário

O fluxo principal é:

1. abrir `login.html`;
2. escolher o módulo;
3. autenticar;
4. ser redirecionado para a área correspondente;
5. navegar pelo dashboard e telas do módulo;
6. usar ações, detalhes e formulários específicos.

---

## Dados do protótipo

A versão atual usa dados em memória para simular a operação real da instituição.

### Dados simulados incluídos

- alunos e matrículas;
- estudantes e históricos básicos;
- requisitos acadêmicos e pendências;
- documentos com versões e status;
- fichas de turmas e notas;
- boletos e movimentação financeira;
- ações de coordenação;
- catálogo de módulos e usuários de exemplo.

Esse conjunto permite validar arquitetura, fluxos de navegação, permissões e interfaces, sem exigir que o sistema esteja totalmente conectado a um banco de produção.

---

## Como executar localmente

### 1) Backend

No diretório raiz do projeto:

```bash
cd backend
python -m venv .venv
```

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

No Linux/macOS:

```bash
source .venv/bin/activate
```

Em seguida:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

O backend ficará disponível em:

- http://localhost:8000
- documentação automática: http://localhost:8000/docs

### 2) Frontend

Você pode abrir os arquivos diretamente em um navegador ou servir a pasta com um pequeno servidor local.

```bash
cd frontend
python -m http.server 5500
```

Depois acesse:

- http://localhost:5500/login.html

### 3) Usuários demo

O projeto inclui exemplos de autenticação para facilitar testes locais.

Exemplos comuns:

- `admin` / `admin123`
- `secretaria` / `secretaria123`
- `professor` / `professor123`
- `ged` / `ged123`
- `financeiro` / `financeiro123`
- `coordenacao` / `coordenacao123`
- `aluno` / `aluno123`

---

## Estrutura principal do repositório

```text
LibreGED/
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── main.py
│   │   ├── modules/
│   │   │   ├── aluno/
│   │   │   ├── coordenacao/
│   │   │   ├── financeiro/
│   │   │   ├── ged/
│   │   │   ├── professores/
│   │   │   ├── secretaria/
│   │   │   └── data_store.py
│   │   └── ...
│   ├── requirements.txt
│   └── ...
├── frontend/
│   ├── app.html
│   ├── login.html
│   ├── admin.html
│   ├── css/
│   ├── js/
│   └── modules/
├── LICENSE
├── README.md
├── run_html.py
└── ...
```

---

## Status atual do projeto

O sistema já se encontra em um estado de protótipo funcional e modular, com os seguintes avanços concretos:

- portal institucional com múltiplos módulos;
- autenticação contextual por módulo;
- autorização por papel e área funcional;
- backend organizado por domínio;
- páginas dedicadas para cada módulo;
- dashboards com indicadores e ações;
- dados demo para validação de comportamento;
- expansão da experiência de administração como módulo institucional.

### O que ainda precisa evoluir

Embora a arquitetura seja coerente e funcional como protótipo, ainda há pontos importantes para amadurecimento:

- persistência real em banco de dados;
- modelagem completa de cursos, disciplinas, matrículas e documentos;
- regras mais refinadas de acesso e papéis;
- CRUD completo por domínio;
- integrações com ERP acadêmico real;
- auditoria e rastreabilidade mais robustas;
- gestão documental e retenção com regras operacionais mais profundas;
- evolução para um ambiente de produção institucional.

---

## Roadmap recomendado

### Fase 1 — consolidação da base modular

- manter a separação por módulo;
- ampliar CRUD dos principais processos;
- conectar frontend com backend real;
- melhorar consistência de dados e autenticação.

### Fase 2 — operação acadêmica

- criar modelos sólidos de alunos, turmas e disciplinas;
- expandir fluxo de matrículas e avaliações;
- operacionalizar financeiro e coordenação com regras reais.

### Fase 3 — governança e conformidade

- uma auditoria mais completa;
- regras de retenção e arquivamento;
- versionamento documental e rastreabilidade;
- controle de histórico por ação e usuário.

### Fase 4 — integração e produção

- conexão com ERP acadêmico;
- autenticação avançada e SSO;
- observabilidade e acompanhamento de operação;
- expansão para ambiente institucional real.

---

## Contribuição

Contribuições são bem-vindas. O projeto está em uma fase de evolução arquitetural e funcional, e a estrutura modular facilita a expansão por domínio.

Ao colaborar, é importante:

- preservar a separação por módulo;
- manter o núcleo institucional compartilhado;
- respeitar as regras de autorização por contexto;
- garantir que cada área e endpoint acompanhe o domínio de negócio correto.

---

## Resumo executivo

O LibreGED já avançou de uma visão conceitual de GED acadêmico para uma proposta funcional de portal universitário modular. A base atual oferece uma arquitetura consistente, navegação por módulos, autenticação contextual, lógica de papéis e experiências dedicadas para diferentes áreas da instituição.

Esse estado é suficiente para demonstrar o modelo de negócios e a direção estratégica do sistema, e também oferece uma base sólida para a próxima etapa: transformar o protótipo em um software acadêmico completo, persistente, integrado e pronto para operação institucional.
