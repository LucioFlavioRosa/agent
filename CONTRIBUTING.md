# Guia de Contribuição

Obrigado pelo interesse em contribuir com o MCP Server! Este documento fornece diretrizes e instruções para contribuir efetivamente com o projeto.

## Fluxo de Trabalho

1. **Fork do Repositório**
   - Faça um fork do repositório para sua conta GitHub
   - Clone o fork para sua máquina local

2. **Configuração do Ambiente de Desenvolvimento**
   - Siga as instruções no [README.md](README.md) para configurar o ambiente
   - Copie `.env.example` para `.env` e configure as variáveis necessárias
   - Copie `workflows.yaml.example` para `workflows.yaml`

3. **Criação de Branch**
   - Crie uma branch para sua contribuição seguindo a convenção:
     - `feature/nome-da-feature` para novas funcionalidades
     - `fix/descricao-do-bug` para correções de bugs
     - `docs/descricao-da-documentacao` para melhorias na documentação
     - `refactor/descricao-da-refatoracao` para refatorações de código

4. **Desenvolvimento**
   - Implemente suas mudanças seguindo o estilo de código do projeto
   - Adicione ou atualize testes conforme necessário
   - Atualize a documentação relevante

5. **Verificações Locais**
   - Execute os linters e formatadores:
     bash
     # Formatação com black
     black .
     
     # Verificação de estilo com flake8
     flake8 .
     
     # Verificação de tipos com mypy
     mypy .
     
   - Execute os testes:
     bash
     pytest tests/
     

6. **Commits**
   - Siga a convenção [Conventional Commits](https://www.conventionalcommits.org/):
     - `feat: descrição` para novas funcionalidades
     - `fix: descrição` para correções de bugs
     - `docs: descrição` para alterações na documentação
     - `refactor: descrição` para refatorações de código
     - `test: descrição` para adição ou modificação de testes
     - `chore: descrição` para tarefas de manutenção

7. **Pull Request**
   - Envie um Pull Request (PR) para a branch `main` do repositório original
   - Preencha o template do PR com todas as informações necessárias
   - Vincule o PR a issues relacionadas, se aplicável
   - Aguarde a revisão e feedback da equipe

## Padrões de Código

- **Python**: Siga o [PEP 8](https://www.python.org/dev/peps/pep-0008/) e use type hints
- **Docstrings**: Use o formato [Google Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- **Imports**: Organize os imports em grupos (stdlib, third-party, local) e em ordem alfabética
- **Testes**: Escreva testes unitários para novas funcionalidades e correções

## Revisão de Código

- Todos os PRs devem ser revisados por pelo menos um membro da equipe
- Os revisores verificarão:
  - Funcionalidade: O código faz o que se propõe a fazer?
  - Qualidade: O código segue as boas práticas e padrões do projeto?
  - Testes: Existem testes adequados para as mudanças?
  - Documentação: A documentação foi atualizada conforme necessário?

## Critérios de Aceitação

- O código deve passar em todos os testes automatizados
- O código deve seguir os padrões de estilo do projeto
- A documentação deve ser atualizada conforme necessário
- O PR deve abordar uma única preocupação (feature, bug, refatoração, etc.)

## Comunicação

- Use issues do GitHub para discutir bugs, features e melhorias
- Use discussões do GitHub para perguntas gerais e conversas sobre o projeto
- Seja respeitoso e construtivo em todas as comunicações

## Licença

Ao contribuir com o projeto, você concorda que suas contribuições serão licenciadas sob a mesma licença do projeto.
