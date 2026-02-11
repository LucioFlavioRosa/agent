# Documentação da Solução Peers CodeAI Backend

Bem-vindo à documentação da solução Peers CodeAI Backend. Este índice apresenta a estrutura da documentação, links para cada documento e uma breve descrição de cada seção.

## Índice

- [Startup e Configuração](deployment/startup_and_configuration.md):
  - Detalha o processo de inicialização da aplicação, carregamento de variáveis de ambiente, segredos, serviços e middlewares.
- [Documentação por Rota](#documentacao-por-rota):
  - Documentação específica de cada rota registrada no backend.
- [Variáveis de Ambiente e Segredos](#variaveis-de-ambiente-e-segredos):
  - Lista e explica todas as variáveis de ambiente e segredos utilizados.

## Documentação por Rota

A aplicação registra as seguintes rotas (ver documentação específica em cada arquivo):

- **/auth**: Rotas de autenticação (login).
- **/analysis**: Rotas de análise multiagente.
- **/projects**: Rotas de verificação, listagem e gerenciamento de projetos.
- **/session**: Rotas de sessão e relatórios.
- **/webhooks**: Rotas para recebimento de webhooks do MCP.
- **/user**: Rotas para consulta de projetos do usuário.

Cada rota possui documentação dedicada, detalhando endpoints, parâmetros, exemplos de uso e respostas.

## Variáveis de Ambiente e Segredos

- **Variáveis de Ambiente**:
  - `AZURE_STORAGE_CONNECTION_STRING`
  - `AZURE_STORAGE_CONTAINER_NAME`
  - `MONGODB_URI`
  - `MONGODB_DATABASE_NAME`
  - `ALLOWED_IPS`
  - `LOG_LEVEL`

- **Segredos do Key Vault**:
  - `redis-host`
  - `redis-port`
  - `redis-password`
  - `redis-db`
  - `redis-use-ssl`
  - `redis-ssl-cert-reqs`

Para detalhes sobre o carregamento e fallback de segredos, consulte [Startup e Configuração](deployment/startup_and_configuration.md).

---

Para dúvidas, sugestões ou contribuições, consulte os documentos específicos ou entre em contato com o time de desenvolvimento.
