# Governança de Segredos e Certificados

## Objetivo

Definir a política operacional para segredos, certificados e chaves usadas pelo EduGED Libre em ambientes de desenvolvimento, homologação e produção. A regra de produção é simples: segredos nunca devem viver em código-fonte, arquivos de configuração versionados, dumps de banco, logs ou artefatos de build.

## Política obrigatória

### 1. Cofre/KMS externo em produção

Toda instalação em produção deve usar um cofre externo ou serviço KMS, por exemplo:

- AWS KMS + Secrets Manager
- Azure Key Vault
- GCP Secret Manager / KMS
- HashiCorp Vault
- equivalente aprovado pela instituição

Regras:

- a chave de criptografia mestre nunca fica no repositório;
- a aplicação recebe os segredos por variáveis de ambiente ou integração com o cofre;
- a rotação de segredos é executada pelo provedor do cofre e não por scripts locais;
- certificados digitais e chaves privadas ficam protegidos em hardware/serviço dedicado;
- a política de acesso usa RBAC e auditoria de leitura/escrita.

### 2. Segmentação por ambiente

| Ambiente | Regras |
| --- | --- |
| Desenvolvimento | Segredos locais, não compartilhados, permitidos apenas em `.env` local e ignorados pelo Git. |
| Teste | Segredos de teste isolados por banco e por pipeline, sem uso em produção. |
| Homologação | Segredos reais, mas isolados do ambiente de produção, com acesso restrito. |
| Produção | Cofre/KMS externo obrigatório; credenciais e certificados em nível de serviço. |

### 3. Chaves e criptografia

- O serviço usa Fernet ou equivalente para dados sensíveis armazenados no banco, com suporte a chaves históricas para rotação compatível.
- Chaves antigas continuam aceitas apenas para leitura/decodificação durante janela de migração.
- Chaves novas devem ser emitidas somente via cofre externo e nunca via algoritmo local ou script de bootstrap.
- Logs e exceptions devem mascarar valores sensíveis antes de persisti-los.

### 4. Certificados digitais e assinatura

- certificados privados e cadeia ficam em armazenamento seguro controlado;
- o material sensível deve ser exposto ao processo somente em memória durante execução;
- repositório e artefatos de build devem conter apenas metadados públicos e hashes;
- reinicialização do serviço não pode recriar chaves privadas de produção.

### 5. Rotação e recuperação

- rotação mínima: 90 dias para segredos de serviço e certificados sensíveis;
- processo de rotação deve manter compatibilidade de leitura por duas janelas de validade;
- fallback de recuperação exige validação por auditoria e aprovação de responsável técnico;
- eventos de rotação e falha devem ser registrados em log centralizado e rastreáveis.

## Checklist de aprovação

Antes de considerar produção pronta, a instituição deve confirmar:

- [ ] cofre/KMS externo documentado e aprovado;
- [ ] acesso por RBAC, não por usuários compartilhados;
- [ ] secret rotation documentada e automatizada;
- [ ] certificados protegidos fora do repositório;
- [ ] backup e restauração validados com manifest e checksum;
- [ ] runbook operacional aprovado com RTO/RPO e plano de reversão;
- [ ] alertas e auditoria de segredos habilitados.

## Evidência no código

O projeto já possui mecanismos que atendem ao objetivo de segurança operacional:

- `backend/app/security_utils.py` para criptografia e fallback de chaves históricas;
- `backend/app/models_storage.py` para armazenamento de senhas em repouso;
- `backend/app/privacy_utils.py` para mascaramento centralizado;
- `backend/app/backup.py` para backup/restore com manifest;
- `backend/tests/test_storage_security.py` e `backend/tests/test_backup_utility.py` como evidência funcional.

A implementação local satisfaz a política de código; a adoção do cofre/KMS externo é a etapa final de governança de infraestrutura para produção.
