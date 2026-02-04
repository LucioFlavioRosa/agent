# Documentação de Secrets no Azure Key Vault

## Secrets de Infraestrutura (Blob Storage)

### Nome do Container do Blob Storage
- **Secret:** `azure-storage-container-name-{grupo}-{empresa}`
- **Vault:** Cofre de infraestrutura (`VaultType.AZURE_INFRASTRUCTURE`)
- **Valor esperado:** Nome real do container no Blob Storage (exemplo: `container-grupo-peers`)
- **Descrição:** O nome do container é recuperado dinamicamente do Key Vault de infraestrutura. Para cada grupo e empresa, deve existir um secret com este padrão, cujo valor é o nome do container.

**Exemplo de configuração:**
- Nome do secret: `azure-storage-container-name-grupo-peers`
- Valor do secret: `container-grupo-peers`

O serviço irá buscar este secret usando o grupo (do MongoDB) e a empresa (do e-mail ou MongoDB) para acessar o container correto no Blob Storage.

## Outros Secrets

- **Connection String do Blob Storage:**
  - Secret fixo: `azure-storage-connection-string`
  - Valor: String de conexão do Blob Storage
  - Vault: Cofre de infraestrutura (`VaultType.AZURE_INFRASTRUCTURE`)

- **Tokens de LLM, Repositórios, etc:**
  - Seguem padrão `nome-grupo-empresa` conforme documentação principal.

## Observações
- Não existe fallback: se o mapeamento de grupo não for encontrado no MongoDB, a operação falha.
- O nome do container nunca é montado como string literal, sempre recuperado do Key Vault.
