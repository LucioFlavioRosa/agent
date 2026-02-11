# Documentação Geral da Solução CodeAI Backend

Bem-vindo à documentação da solução CodeAI Backend. Este índice apresenta a estrutura documental, links para cada seção e uma breve descrição de cada documento.

---

## Índice

- [Documentação de Startup e Configuração](deployment/startup_and_configuration.md)
- [Documentação por Rotas](rotas/)
    - [Autenticação (`/auth`)](rotas/auth.md)
    - [Análise Multiagente (`/analysis`)](rotas/analysis.md)
    - [Projetos (`/projects`)](rotas/projects.md)
    - [Sessão e Relatórios (`/session`)](rotas/session.md)
    - [Webhooks (`/webhooks`)](rotas/webhooks.md)
    - [Projetos do Usuário (`/user`)](rotas/user_projects.md)
- [Variáveis de Ambiente e Segredos](deployment/startup_and_configuration.md#variáveis-de-ambiente-obrigatórias)

---

## Descrição das Seções

### 1. Documentação de Startup e Configuração

Explica o fluxo de inicialização da aplicação, carregamento de variáveis de ambiente, segredos do Key Vault, inicialização de serviços e middlewares.

### 2. Documentação por Rotas

Cada rota exposta pela API possui um documento dedicado, detalhando endpoints, parâmetros, respostas e exemplos de uso.

- **/auth**: Rotas de autenticação e login.
- **/analysis**: Rotas para iniciar análises multiagente.
- **/projects**: Rotas para verificação, listagem e gerenciamento de projetos e membros.
- **/session**: Rotas para consulta de sessões e relatórios.
- **/webhooks**: Rotas para integração via webhooks (MCP).
- **/user**: Rotas para consulta de projetos acessíveis pelo usuário.

### 3. Variáveis de Ambiente e Segredos

Lista todas as variáveis de ambiente obrigatórias e segredos buscados no Key Vault, com orientações para configuração.

---

## Como navegar

- Use os links acima para acessar cada documento.
- Consulte a documentação de cada rota para detalhes de integração.
- Para configuração e deployment, consulte a seção de startup e variáveis de ambiente.

---

## Observações

- Esta documentação não inclui testes automatizados.
- Para dúvidas técnicas, consulte os documentos específicos de cada rota ou configuração.

