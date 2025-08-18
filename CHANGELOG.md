# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/spec/v2.0.0.html).

## [Não Lançado]

### Adicionado
- Documentação completa do projeto incluindo README.md, CONTRIBUTING.md, CHANGELOG.md
- Templates para issues e pull requests
- Arquivo .env.example para facilitar a configuração do ambiente
- Arquivo workflows.yaml.example como referência para configuração de workflows

## [9.0.0] - 2023-XX-XX

### Adicionado
- Versão inicial do MCP Server com FastAPI
- Integração com Redis para armazenamento de jobs
- Integração com Azure Key Vault para gerenciamento de segredos
- Suporte a múltiplos provedores de LLM (OpenAI e Anthropic Claude)
- Sistema de RAG (Retrieval-Augmented Generation) usando Azure AI Search
- Integração com GitHub para leitura de repositórios e criação de PRs
- Workflows configuráveis via arquivo YAML
- Agentes especializados para diferentes tarefas de análise
- Mecanismo de aprovação manual de análises antes da implementação
- Suporte a criação de múltiplos PRs organizados logicamente
