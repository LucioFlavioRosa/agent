# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e este projeto adere ao [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documentação inicial do projeto (README.md, CONTRIBUTING.md, CHANGELOG.md)
- Arquivo de exemplo de variáveis de ambiente (.env.example)
- Arquivo de configuração de workflows (workflows.yaml)
- Templates para Issues e Pull Requests

## [9.0.0] - 2023-12-15

### Added
- Suporte para múltiplos modelos de LLM (OpenAI e Anthropic Claude)
- Implementação de RAG (Retrieval-Augmented Generation) com Azure AI Search
- Sistema de agrupamento de mudanças para PRs empilhados

### Changed
- Refatoração completa da arquitetura para usar interfaces e injeção de dependência
- Migração para Azure Key Vault para gerenciamento de segredos
- Melhoria no sistema de armazenamento de jobs com Redis

### Fixed
- Correção de problemas de concorrência no processamento de jobs
- Tratamento robusto de erros na API do GitHub
- Melhorias na estabilidade da conexão com serviços externos

## [8.0.0] - 2023-10-01

### Added
- Implementação inicial do servidor FastAPI
- Sistema de jobs assíncronos com background tasks
- Integração com GitHub para leitura e escrita de repositórios
- Suporte para análise de código com OpenAI GPT-4

[Unreleased]: https://github.com/seu-usuario/mcp-server/compare/v9.0.0...HEAD
[9.0.0]: https://github.com/seu-usuario/mcp-server/compare/v8.0.0...v9.0.0
[8.0.0]: https://github.com/seu-usuario/mcp-server/releases/tag/v8.0.0