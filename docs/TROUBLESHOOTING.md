# Guia de Troubleshooting: Configuração de Ambiente e Secrets

Este guia cobre os problemas mais comuns relacionados à configuração de variáveis de ambiente, Key Vaults, MongoDB e Redis.

## 1. Erro: 'Secret não encontrado'

**Causa provável:**
- O nome do secret está incorreto (não segue o padrão `nome-grupo-empresa`).
- O grupo do usuário não existe no mapeamento do MongoDB.
- O secret não foi criado no Key Vault correto.

**Solução:**
- Verifique o nome do secret (exemplo: `github-token-grupo-peers`).
- Confirme que o grupo do usuário existe na collection do MongoDB (`user_group_mapping`).
- Crie o secret no Key Vault correto (`AZURE_KEY_VAULT_LLM_URL`, `AZURE_KEY_VAULT_REPOSITORY_URL`, etc).

## 2. Erro: Falha de conexão com Key Vault

**Causa provável:**
- URL do Key Vault está incorreta ou ausente.
- Permissões insuficientes para acessar o Key Vault.
- Problemas de rede ou credenciais Azure.

**Solução:**
- Verifique se as variáveis de ambiente `AZURE_KEY_VAULT_LLM_URL`, `AZURE_KEY_VAULT_REPOSITORY_URL`, `AZURE_KEY_VAULT_BLOB_STORAGE_URL` estão corretas e começam com `https://`.
- Confirme que o serviço possui permissões de acesso (Managed Identity ou Service Principal).
- Teste a conectividade usando o script `scripts/validate_keyvault_secrets.py`.

## 3. Erro: Falha de conexão com MongoDB

**Causa provável:**
- Connection string ausente ou inválida.
- Secret do MongoDB não existe no Key Vault.
- Problemas de rede ou firewall.

**Solução:**
- Verifique se a variável `MONGODB_CONNECTION_STRING_SECRET_NAME` está definida e aponta para o secret correto (exemplo: `azure-mongodb-connection-string`).
- Confirme que o secret existe no Key Vault.
- Teste a conexão manualmente usando a connection string recuperada.

## 4. Erro: Falha de conexão com Redis

**Causa provável:**
- URL do Redis ausente ou inválida.
- Redis não está disponível na rede.

**Solução:**
- Verifique se a variável de ambiente `REDIS_URL` está definida e segue o padrão (exemplo: `redis://peers-redis:6379`).
- Confirme que o serviço Redis está rodando e acessível na rede.

---

## Exemplos de nomes de variáveis e secrets

- Variáveis de ambiente:
    - `AZURE_KEY_VAULT_LLM_URL`: `https://kv-llm-peers.vault.azure.net/`
    - `MONGODB_CONNECTION_STRING_SECRET_NAME`: `azure-mongodb-connection-string`
    - `REDIS_URL`: `redis://peers-redis:6379`
- Secrets nos cofres:
    - `AWS-ACCESS-KEY-ID-grupo-peers`
    - `github-token-grupo-peers`
    - `azure-storage-connection-string-grupo-peers`

---

## Checklist de configuração

1. Todas as variáveis de ambiente obrigatórias estão presentes e válidas? (Use `scripts/validate_environment.py`)
2. Todos os secrets essenciais existem nos Key Vaults? (Use `scripts/validate_keyvault_secrets.py`)
3. Os nomes seguem o padrão `nome-grupo-empresa`?
4. O grupo do usuário está corretamente mapeado no MongoDB?

---

Para dúvidas adicionais, consulte a documentação oficial do projeto ou entre em contato com o time de infraestrutura.