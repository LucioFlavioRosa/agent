# Revisão dos Modelos de Dados do Backend

## Contexto

De acordo com as novas responsabilidades do backend, as funções de auditoria, extração de texto, manipulação de arquivos e autenticação foram delegadas para outros componentes (frontend ou MCPs). O backend agora apenas repassa requisições e respostas, sem processamentos adicionais.

## Decisões por Arquivo

### `backend/app/models/audit_models.py`
- **Decisão:** Removido.
- **Justificativa:** O backend não realiza mais auditoria de comunicação entre frontend e MCP. Os modelos de auditoria não são necessários neste momento.

### `backend/app/models/mcp_config_models.py`
- **Decisão:** Mantido.
- **Justificativa:** Os modelos `MCPAgentConfig` e `MCPConfigRegistry` são essenciais para a configuração dinâmica e roteamento de requisições para múltiplos MCPs. Permitem flexibilidade e expansão futura.

## Resumo
- Modelos de auditoria removidos.
- Modelos de configuração de MCP mantidos.
- Outros modelos não avaliados nesta etapa.
