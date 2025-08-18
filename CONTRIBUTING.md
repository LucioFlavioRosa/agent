# Guia de Contribuição

Obrigado pelo interesse em contribuir com o MCP Server! Este documento fornece diretrizes para contribuir com o projeto de forma eficaz.

## Fluxo de Contribuição

1. **Fork do Repositório**
   - Crie um fork do repositório para sua conta

2. **Clone do Fork**
   bash
   git clone https://github.com/seu-usuario/mcp-server.git
   cd mcp-server
   

3. **Crie uma Branch**
   - Use o padrão de nomenclatura adequado (veja abaixo)
   bash
   git checkout -b feature/nova-funcionalidade
   

4. **Desenvolva e Teste**
   - Implemente suas mudanças
   - Adicione/atualize testes
   - Verifique se os testes passam

5. **Commit das Mudanças**
   - Use mensagens de commit significativas (veja abaixo)
   bash
   git commit -m "feat: adiciona nova funcionalidade X"
   

6. **Push para o Fork**
   bash
   git push origin feature/nova-funcionalidade
   

7. **Abra um Pull Request**
   - Use o template fornecido
   - Descreva claramente suas mudanças

## Padrões de Nomenclatura

### Branches

- `feature/nome-da-feature`: Para novas funcionalidades
- `fix/nome-do-bug`: Para correções de bugs
- `docs/nome-da-documentacao`: Para atualizações de documentação
- `refactor/nome-da-refatoracao`: Para refatorações de código
- `test/nome-do-teste`: Para adições ou modificações de testes

### Mensagens de Commit

Seguimos o padrão [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - Nova funcionalidade
- `fix:` - Correção de bug
- `docs:` - Alterações na documentação
- `style:` - Formatação, ponto-e-vírgula faltando, etc; sem alteração de código
- `refactor:` - Refatoração de código
- `test:` - Adição ou correção de testes
- `chore:` - Atualizações de tarefas de build, configurações, etc; sem alteração de código

Exemplo: `feat: adiciona autenticação via OAuth2`

## Preparação do Ambiente Local

1. **Instale as Dependências**
   bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Dependências de desenvolvimento
   

2. **Configure o Ambiente**
   - Copie `.env.example` para `.env`
   - Preencha as variáveis necessárias

3. **Autentique no Azure**
   bash
   az login
   
   Isso é necessário para que `DefaultAzureCredential` funcione localmente

4. **Verifique a Configuração**
   - Certifique-se de que `workflows.yaml` está presente na raiz
   - Verifique se os arquivos de prompt necessários existem em `tools/prompts/`

## Linters e Testes

bash
# Execute o linter
flake8 .

# Execute o formatador de código
black .

# Execute os testes
pytest

# Execute os testes com cobertura
pytest --cov=. --cov-report=term-missing


## Critérios de Revisão

Seu PR será avaliado com base nos seguintes critérios:

1. **Funcionalidade**: A mudança funciona conforme esperado?
2. **Qualidade do Código**: O código segue as boas práticas e padrões do projeto?
3. **Testes**: Existem testes adequados para as mudanças?
4. **Documentação**: A documentação foi atualizada adequadamente?
5. **Compatibilidade**: A mudança mantém compatibilidade com versões anteriores (quando aplicável)?

## Checklist do Pull Request

- [ ] O código segue o estilo e diretrizes do projeto
- [ ] Todos os testes passam
- [ ] Foram adicionados testes para as novas funcionalidades
- [ ] A documentação foi atualizada (README, docstrings, etc.)
- [ ] O `CHANGELOG.md` foi atualizado (para mudanças relevantes)
- [ ] O código foi revisado localmente antes do envio

## Atualização do CHANGELOG

Para cada mudança relevante, atualize o arquivo `CHANGELOG.md` na seção `[Unreleased]`. Siga o formato:

markdown
## [Unreleased]
### Added
- Nova funcionalidade X

### Changed
- Comportamento Y modificado

### Fixed
- Correção do bug Z


## Dúvidas?

Se você tiver dúvidas sobre o processo de contribuição, abra uma issue com o label "question".