# Runbook de Operação em Produção

## Objetivo

Este runbook define como operar o EduGED Libre em produção, com foco em saúde do sistema, backup/restauração, integração ERP, resposta a incidentes e recuperação em caso de falhas de infraestrutura ou dados.

## Escopo e responsabilidades

- Responsável técnico: mantenedor/aplicação e administrador de infraestrutura;
- Responsável de segurança: aprovação do uso de segredos e certificados;
- Responsável operacional: acompanhamento de filas, health checks e backup;
- Responsável de negócio/instituição: aprovação de procedimentos e comunicação de indisponibilidade.

## Critérios de disponibilidade

- RTO (Recovery Time Objective): 4 horas para serviços críticos, desde a detecção até a recuperação funcional.
- RPO (Recovery Point Objective): 24 horas para dados transacionais, com backups diários e validação do manifest.
- Monitoramento: health checks do banco, storage e fila com alertas por falha de disponibilidade ou corrupção de artefatos.

## Health checks e observabilidade

A aplicação deve verificar continuamente:

- disponibilidade do banco PostgreSQL;
- disponibilidade do storage compartilhado;
- fila de processamento e worker;
- integridade de manifestos e backups;
- latência de integração ERP.

Alertas mínimos:

- falha de conexão ao banco;
- storage indisponível ou sem espaço;
- worker sem processamento por mais de N minutos;
- tempo de resposta da API acima do limite operacional;
- rejeição/timeout repetido em integração externa.

## Procedimentos operacionais diários

### 1. Verificação matinal

- validar health checks;
- conferir filas e discrepâncias de reconciliação;
- revisar alertas de retry e rejeição do ERP;
- confirmar que backups do dia foram gerados corretamente;
- verificar existência de manifest JSON e checksum válido.

### 2. Verificação de backup

Comando operacional padrão:

- gerar backup com `backend/app/backup.py`;
- confirmar que o diretório de backup contém `manifest.json`, `database.dump` e `storage.tar.gz`;
- validar integridade do archive e hash do manifest;
- armazenar em mídia externa com retenção mínima conforme política institucional.

### 3. Procedimento de restauração

- confirmar o backup correto e a assinatura de integridade;
- suspender escritas em produção antes da restauração;
- restaurar arquivo do banco e storage em ambiente isolado;
- validar dados e manifestos;
- difundir a decisão final e reabilitar o serviço.

## Política de incidentes

### Falha de banco

1. confirmar status e logs;
2. ativar fila de quarentena se houver dados inconsistentes;
3. manter o serviço em degrade controlado;
4. restaurar backup válido ou iniciar failover aprovado;
5. reprocessar apenas eventos idempotentes.

### Falha de storage

1. verificar conectividade e espaço em disco;
2. bloquear novas gravações se a integridade do armazenamento estiver comprometida;
3. confirmar backup recente;
4. restaurar storage do backup e validar hashes/manifests;
5. reprocessar arquivos pendentes sem duplicação.

### Falha de integração ERP

1. confirmar se a falha é de rede, timeout ou rejeição de payload;
2. rever a regra de idempotência e `correlation_id`;
3. rejeitar/registrar eventos fora do contrato sem perda de auditoria;
4. manter fila em retry controlado e expor alertas operacionais;
5. após estabilização, reprocessar somente itens sem duplicidade.

## Plano de reversão

Em qualquer migração ou ajuste operacional:

- manter a versão anterior em estado pronto para rollback;
- registrar o impacto previsto e o comando de reversão;
- validar que os dados históricos e o manifest de backup continuam íntegros;
- conceder aprovação do responsável técnico antes do retorno ao serviço.

## Arquivos de evidência

- backups completos com manifest e arquivos de storage;
- logs do worker, fila e API;
- relatórios de reconciliação ERP;
- registros de auditoria e eventos de segurança.

## Aprovação final

A alta disponibilidade e produção segura só podem ser declaradas com:

- [ ] health checks automatizados ativos;
- [ ] backup restaurável validado;
- [ ] política de segredos/KMS externa aprovada;
- [ ] runbook assinado pelo responsável técnico;
- [ ] aprovação da instituição para operação real e plano de reversão.
