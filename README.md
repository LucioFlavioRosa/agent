# Multi-Agent Code Platform (MCP)

## Visão Geral
Este repositório contém o MCP original, responsável por orquestrar agentes de IA para análise, modernização e implementação de código em múltiplos repositórios.

## Separação de Responsabilidades
A partir desta versão, o MCP original foi dividido em dois sistemas MCP distintos para facilitar manutenção, escalabilidade e otimização:

- **MCP Principal (este repositório):**
  - Foca em análise, modernização e implementação de código.
  - Não realiza operações diretas no Azure Board.
  - Suporta os analysis types tradicionais (exceto Azure Board).

- **MCP Azure Board (novo repositório):**
  - Responsável exclusivamente pelas operações relacionadas ao Azure Board, incluindo:
    - `criacao_epicos_azure_devops`
    - `criacao_tarefas_azure_devops`
    - `revisor_tarefas`
    - `criacao_features_azure_devops`
  - Contém agentes e executores dedicados para integração com Azure DevOps Boards.

## Como funciona a separação?
- O MCP original não possui mais agentes ou executores para os analysis types do Azure Board.
- Toda a lógica referente a Azure Board foi movida para o MCP dedicado.
- Para operações Azure Board, utilize o MCP Azure Board.

## Próximos passos
- Refino contínuo da separação de responsabilidades.
- Documentação detalhada sobre integração entre MCPs.

## Observação
Se você precisa executar workflows relacionados ao Azure Board, acesse o MCP Azure Board. Este MCP permanece focado em análise e implementação de código fora do escopo Azure Board.
