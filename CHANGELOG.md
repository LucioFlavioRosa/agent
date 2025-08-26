# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [Não Lançado]

### Adicionado
- Documentação completa do projeto (README.md, CONTRIBUTING.md)
- Arquivo de exemplo de variáveis de ambiente (.env.example)
- Este arquivo de changelog

## [9.0.0] - 2024-01-XX

### Adicionado
- Sistema de nomeação de análises para facilitar recuperação
- Endpoint `/analyses/by-name/{analysis_name}` para busca por nome
- Endpoint `/start-code-generation-from-report/{analysis_name}` para geração de código a partir de relatórios existentes
- Suporte a análises nomeadas no payload de criação
- Política de sobrescrita para nomes duplicados de análises
- Testes automatizados para funcionalidades de nomeação

### Alterado
- Refatoração completa seguindo princípios SOLID
- Implementação de injeção de dependências em todos os componentes
- Melhoria na arquitetura de interfaces e abstrações
- Otimização do sistema de leitura de repositórios GitHub
- Aprimoramento do sistema de processamento de workflows

### Corrigido
- Correção na lógica de preenchimento de conjuntos de mudanças
- Melhoria no tratamento de erros em operações do Redis
- Correção de bugs na criação de Pull Requests empilhados
- Estabilização do fluxo de dados entre etapas do workflow

## [8.0.0] - 2023-12-XX

### Adicionado
- Sistema RAG (Retrieval-Augmented Generation) com Azure AI Search
- Suporte a múltiplos provedores de LLM (OpenAI, Anthropic Claude)
- Integração com Azure Key Vault para gerenciamento de segredos
- Sistema de jobs assíncronos com Redis
- API FastAPI com endpoints RESTful

### Alterado
- Migração de arquitetura monolítica para microserviços
- Implementação de padrões de design (Strategy, Factory, Repository)
- Melhoria significativa na performance de leitura de repositórios

## [7.0.0] - 2023-11-XX

### Adicionado
- Agente Revisor para análise de repositórios GitHub
- Agente Processador para transformação de dados estruturados
- Sistema de workflows configuráveis via YAML
- Suporte a diferentes tipos de análise de código

### Alterado
- Refatoração da arquitetura de agentes
- Melhoria na modularidade do sistema

## [6.0.0] - 2023-10-XX

### Adicionado
- Integração inicial com GitHub API
- Sistema básico de análise de código
- Geração automática de Pull Requests

### Alterado
- Migração para Python 3.8+
- Adoção de type hints em todo o código

## [5.0.0] - 2023-09-XX

### Adicionado
- Primeira versão do sistema de agentes de IA
- Integração básica com OpenAI GPT
- Sistema de processamento de código-fonte

---

## Tipos de Mudanças

- **Adicionado** para novas funcionalidades
- **Alterado** para mudanças em funcionalidades existentes
- **Descontinuado** para funcionalidades que serão removidas em breve
- **Removido** para funcionalidades removidas
- **Corrigido** para correções de bugs
- **Segurança** para vulnerabilidades corrigidas

## Versionamento

Este projeto usa [Semantic Versioning](https://semver.org/lang/pt-BR/):

- **MAJOR**: Mudanças incompatíveis na API
- **MINOR**: Funcionalidades adicionadas de forma compatível
- **PATCH**: Correções de bugs compatíveis

## Como Contribuir com o Changelog

Ao fazer alterações no projeto:

1. Adicione suas mudanças na seção `[Não Lançado]`
2. Use as categorias apropriadas (Adicionado, Alterado, etc.)
3. Seja descritivo mas conciso
4. Inclua referências a issues/PRs quando relevante
5. Mantenha a ordem cronológica (mais recente primeiro)

## Links Úteis

- [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/)
- [Semantic Versioning](https://semver.org/lang/pt-BR/)
- [Conventional Commits](https://www.conventionalcommits.org/pt-br/v1.0.0/)