# MCP Server - Multi-Agent Code Platform

## 🚀 Visão Geral

O **MCP Server** é uma plataforma robusta para orquestração de agentes de IA especializados em análise e refatoração de código. O sistema utiliza arquitetura baseada em princípios SOLID, com injeção de dependências e interfaces bem definidas.

### Principais Funcionalidades

- **Análise Inteligente de Código**: Agentes especializados para diferentes tipos de análise
- **Refatoração Automatizada**: Geração de Pull Requests com mudanças estruturadas
- **Integração com GitHub**: Leitura de repositórios e criação automática de PRs
- **Sistema RAG**: Busca contextual em políticas de desenvolvimento
- **Arquitetura Modular**: Componentes intercambiáveis via interfaces

## 🏗️ Arquitetura

### Componentes Principais


┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Redis         │    │   GitHub        │
│   (API Layer)   │◄──►│   (Job Store)   │    │   (Repository)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              ▲
         ▼                                              │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Agentes       │    │   LLM Providers │    │   Tools         │
│   - Revisor     │◄──►│   - OpenAI      │    │   - Connectors  │
│   - Processador │    │   - Claude      │    │   - Fillers     │
└─────────────────┘    └─────────────────┘    └─────────────────┘


### Agentes Disponíveis

- **AgenteRevisor**: Lê repositórios GitHub e inicia análises de código
- **AgenteProcessador**: Processa dados estruturados e aplica transformações

## 🛠️ Configuração e Instalação

### Pré-requisitos

- Python 3.8+
- Redis Server
- Azure Key Vault (para gerenciamento de segredos)
- Conta GitHub com token de acesso

### Instalação

1. **Clone o repositório:**
   bash
   git clone https://github.com/org/mcp-server.git
   cd mcp-server
   

2. **Crie um ambiente virtual:**
   bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   

3. **Instale as dependências:**
   bash
   pip install -r requirements.txt
   

4. **Configure as variáveis de ambiente:**
   bash
   cp .env.example .env
   # Edite o arquivo .env com suas configurações
   

5. **Inicie o Redis:**
   bash
   redis-server
   

6. **Execute o servidor:**
   bash
   uvicorn mcp_server_fastapi:app --reload --port 8000
   

## 🧪 Como Rodar os Testes

### Executar Todos os Testes
bash
pytest -v


### Executar Testes Específicos
bash
# Testes de nomeação de análises
pytest backend/tests/test_analysis_naming.py -v

# Testes com padrão específico
pytest -k "test_create_analysis" -v


### Executar com Cobertura
bash
pytest --cov=. --cov-report=html --cov-report=term


### Executar Testes de Integração
bash
# Certifique-se de que o Redis está rodando
pytest backend/tests/ -k "integration" -v


### Configuração para Testes

Para executar os testes, certifique-se de:
1. Redis está rodando na porta padrão (6379)
2. Variáveis de ambiente de teste estão configuradas
3. Azure Key Vault está acessível (ou use mocks para testes unitários)

## 📚 Uso da API

### Iniciar uma Análise

bash
curl -X POST "http://localhost:8000/start-analysis" \
     -H "Content-Type: application/json" \
     -d '{
       "repo_name": "org/repositorio",
       "analysis_type": "refatoracao_completa",
       "branch_name": "main",
       "instrucoes_extras": "Foque em melhorias de performance",
       "usar_rag": true,
       "gerar_relatorio_apenas": false
     }'


### Verificar Status

bash
curl "http://localhost:8000/status/{job_id}"


### Aprovar/Rejeitar Análise

bash
curl -X POST "http://localhost:8000/update-job-status" \
     -H "Content-Type: application/json" \
     -d '{
       "job_id": "uuid-do-job",
       "action": "approve",
       "observacoes": "Aprovado para produção"
     }'


## 🔧 Workflows Disponíveis

Os workflows são definidos no arquivo `workflows.yaml`:

- **refatoracao_completa**: Análise completa com refatoração e agrupamento
- **analise_seguranca**: Foco em vulnerabilidades de segurança
- **otimizacao_performance**: Melhorias de performance
- **documentacao**: Geração de documentação automática

## 🏛️ Princípios Arquiteturais

### SOLID
- **Single Responsibility**: Cada classe tem uma única responsabilidade
- **Open/Closed**: Extensível via interfaces, fechado para modificação
- **Liskov Substitution**: Implementações podem ser substituídas
- **Interface Segregation**: Interfaces específicas e focadas
- **Dependency Inversion**: Dependências injetadas via interfaces

### Padrões Utilizados
- **Dependency Injection**: Todas as dependências são injetadas
- **Strategy Pattern**: Diferentes provedores de LLM
- **Factory Pattern**: Criação de provedores baseada em configuração
- **Repository Pattern**: Abstração de acesso a dados

## 🔐 Segurança

### Gerenciamento de Segredos
- Todos os segredos são armazenados no Azure Key Vault
- Autenticação via Azure Default Credential
- Tokens GitHub com escopo mínimo necessário

### Segredos Necessários
- `github-token`: Token de acesso ao GitHub
- `openaiapi`: Chave da API OpenAI
- `azure-openai-modelos`: Chave do Azure OpenAI
- `aisearchapi`: Chave do Azure AI Search
- `ANTHROPICAPIKEY`: Chave da API Anthropic (opcional)

## 🤝 Contribuindo

Por favor, leia o [CONTRIBUTING.md](CONTRIBUTING.md) para detalhes sobre:
- Configuração do ambiente de desenvolvimento
- Padrões de código
- Processo de Pull Request
- Execução de testes

## 📋 Roadmap

- [ ] Suporte a mais provedores de LLM
- [ ] Interface web para monitoramento
- [ ] Métricas e observabilidade
- [ ] Suporte a GitLab e Bitbucket
- [ ] Análise de múltiplos repositórios
- [ ] Integração com CI/CD

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🆘 Suporte

Para suporte e dúvidas:
- Abra uma issue no GitHub
- Consulte a documentação em `/docs`
- Revise os exemplos em `/examples`

---

**Desenvolvido com ❤️ pela equipe de Engenharia de Software**