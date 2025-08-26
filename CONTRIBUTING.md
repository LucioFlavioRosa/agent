# Guia de Contribuição

## Como Contribuir para o MCP Server - Multi-Agent Code Platform

Obrigado por seu interesse em contribuir! Este documento fornece diretrizes para contribuir com o projeto.

## 🚀 Configuração do Ambiente de Desenvolvimento

### Pré-requisitos
- Python 3.8+
- Redis (para armazenamento de jobs)
- Azure Key Vault (para gerenciamento de segredos)
- Conta GitHub com token de acesso

### Configuração Inicial

1. **Clone o repositório:**
   bash
   git clone https://github.com/org/mcp-server.git
   cd mcp-server
   

2. **Crie um ambiente virtual:**
   bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # ou
   venv\Scripts\activate     # Windows
   

3. **Instale as dependências:**
   bash
   pip install -r requirements.txt
   

4. **Configure as variáveis de ambiente:**
   - Copie o arquivo `.env.example` para `.env`
   - Preencha todas as variáveis necessárias

5. **Execute os testes para verificar a configuração:**
   bash
   pytest -v
   

## 📋 Padrões de Código

### Estrutura do Projeto
- `agents/`: Implementações dos agentes de IA
- `domain/interfaces/`: Interfaces e contratos
- `tools/`: Utilitários e implementações concretas
- `backend/tests/`: Testes automatizados

### Princípios SOLID
O projeto segue rigorosamente os princípios SOLID:
- **Single Responsibility**: Cada classe tem uma única responsabilidade
- **Open/Closed**: Extensível via interfaces, fechado para modificação
- **Liskov Substitution**: Implementações podem ser substituídas
- **Interface Segregation**: Interfaces específicas e focadas
- **Dependency Inversion**: Dependências injetadas via interfaces

### Convenções de Código
- **Nomenclatura**: Use nomes descritivos em português para classes e métodos
- **Documentação**: Docstrings obrigatórias para todas as classes e métodos públicos
- **Type Hints**: Sempre use type hints em Python
- **Imports**: Organize imports em grupos (stdlib, third-party, local)

### Exemplo de Classe Bem Estruturada
python
from abc import ABC, abstractmethod
from typing import Dict, Optional

class MinhaInterface(ABC):
    """Interface para demonstrar padrões do projeto."""
    
    @abstractmethod
    def processar_dados(self, dados: Dict[str, str]) -> Optional[str]:
        """Processa dados de entrada e retorna resultado."""
        pass

class MinhaImplementacao(MinhaInterface):
    """Implementação concreta seguindo os padrões do projeto."""
    
    def __init__(self, dependencia: MinhaInterface):
        self.dependencia = dependencia
    
    def processar_dados(self, dados: Dict[str, str]) -> Optional[str]:
        """Implementa o processamento de dados."""
        if not dados:
            return None
        return f"Processado: {dados}"


## 🔄 Fluxo de Trabalho para Pull Requests

### 1. Criação da Branch
bash
git checkout -b feature/nome-da-funcionalidade
# ou
git checkout -b fix/nome-do-bug


### 2. Desenvolvimento
- Faça commits pequenos e focados
- Use mensagens de commit descritivas:
  
  feat: adiciona nova interface para processamento de dados
  fix: corrige erro de validação no AgenteRevisor
  refactor: melhora estrutura do GitHubConnector
  docs: atualiza documentação da API
  test: adiciona testes para ChangesetFiller
  

### 3. Testes
Antes de abrir o PR, certifique-se de que:
- [ ] Todos os testes passam: `pytest -v`
- [ ] Novos testes foram adicionados para novas funcionalidades
- [ ] Cobertura de código não diminuiu

### 4. Pull Request
- **Título**: Seja claro e descritivo
- **Descrição**: Explique o que foi alterado e por quê
- **Checklist**: Use o template de PR (será criado automaticamente)

### Template de PR
markdown
## Descrição
Descreva brevemente as mudanças realizadas.

## Tipo de Mudança
- [ ] Bug fix
- [ ] Nova funcionalidade
- [ ] Refatoração
- [ ] Documentação
- [ ] Testes

## Checklist
- [ ] Código segue os padrões do projeto
- [ ] Testes foram adicionados/atualizados
- [ ] Documentação foi atualizada
- [ ] Todos os testes passam


## 🧪 Executando Testes

### Testes Unitários
bash
# Todos os testes
pytest -v

# Testes específicos
pytest backend/tests/test_analysis_naming.py -v

# Com cobertura
pytest --cov=. --cov-report=html


### Testes de Integração
bash
# Certifique-se de que o Redis está rodando
pytest backend/tests/ -k "integration" -v


## 🏗️ Arquitetura do Sistema

### Agentes
- **AgenteRevisor**: Lê repositórios e inicia análises
- **AgenteProcessador**: Processa dados estruturados

### Interfaces Principais
- `ILLMProvider`: Abstração para provedores de IA
- `IRepositoryReader`: Leitura de repositórios
- `ISecretManager`: Gerenciamento de segredos

### Fluxo de Dados
1. Requisição via API FastAPI
2. Job armazenado no Redis
3. Agente processa via LLM
4. Resultado commitado no GitHub

## 🐛 Reportando Bugs

Ao reportar bugs, inclua:
- Versão do Python
- Passos para reproduzir
- Comportamento esperado vs atual
- Logs de erro (se aplicável)

## 💡 Sugerindo Funcionalidades

Para novas funcionalidades:
- Descreva o problema que resolve
- Proponha uma solução
- Considere o impacto na arquitetura existente

## 📞 Suporte

Para dúvidas sobre contribuição:
- Abra uma issue com a tag `question`
- Consulte a documentação existente
- Revise PRs anteriores similares

---

**Obrigado por contribuir para tornar este projeto melhor! 🚀**