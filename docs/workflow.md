# Workflow Simplificado de Análise de Código

## Objetivo
Descrever o fluxo de trabalho para análise, revisão e melhoria de código utilizando agentes especializados.

## Etapas do Workflow
1. **Configuração da Análise**
   - Defina o tipo de análise desejada (ex: limpeza de código, refatoração, sugestão de melhorias).
   - Informe o repositório alvo (GitHub, Azure DevOps ou GitLab).

2. **Leitura do Código**
   - O sistema acessa o repositório e lê os arquivos necessários para análise.

3. **Execução dos Agentes de Análise**
   - Agentes especializados processam o código, identificando problemas e sugerindo melhorias.
   - O processamento pode ser incremental, permitindo rodadas seguras e rastreáveis de simplificação.

4. **Geração de Relatórios**
   - Para cada rodada de análise, é gerado um relatório detalhado.
   - Os relatórios podem ser consultados via API ou interface.

## Como Consultar Relatórios
- Utilize o endpoint de consulta para obter o relatório da análise desejada.
- Os relatórios incluem histórico das mudanças, problemas encontrados e sugestões aplicadas.

## Observações Importantes
- Funcionalidades de commit, PR, build .NET, Azure Boards e comparação de código foram removidas.
- O foco está em análise e melhoria incremental do código.
- Recomenda-se executar múltiplas rodadas de análise para simplificação segura.

## Exemplos de Tipos de Análise
- Limpeza de código
- Detecção de duplicidade
- Refatoração incremental
- Sugestão de boas práticas

## Dependências
Consulte o arquivo `requirements.txt` para as dependências mínimas necessárias.
