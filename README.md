# Multi-Agent Code Platform (MCP) - Revisão e Melhoria de Código

## Visão Geral
Este projeto é uma plataforma simplificada para análise, revisão e melhoria de código-fonte em repositórios GitHub, Azure DevOps e GitLab. O foco é permitir a execução de múltiplas análises de código de maneira incremental e segura, utilizando agentes especializados e recursos de IA.

## Funcionalidades Principais
- **Leitura e escrita em repositórios Git (GitHub, Azure DevOps, GitLab)**
- **Execução de agentes de análise e revisão de código**
- **Processamento incremental de simplificações e melhorias**
- **Consulta de relatórios de análise**

## Tipos de Análise Suportados
- Limpeza de código
- Detecção de problemas de qualidade
- Sugestão de melhorias
- Refatoração incremental

## Como Executar uma Análise
1. Configure o acesso ao repositório desejado (GitHub, Azure DevOps ou GitLab).
2. Inicie uma análise informando o tipo desejado e os parâmetros necessários.
3. O sistema irá ler o código diretamente do repositório e executar os agentes de análise.
4. Os resultados podem ser consultados via API ou interface, incluindo relatórios detalhados de cada rodada de análise.

## Configuração
- As credenciais de acesso aos repositórios devem ser configuradas via variáveis de ambiente ou serviço de segredos.
- Os tipos de análise disponíveis podem ser consultados via API.

## Consulta de Relatórios
- Para cada análise executada, é gerado um relatório que pode ser acessado por meio da API.
- Os relatórios trazem detalhes sobre os problemas encontrados, sugestões de melhoria e histórico das simplificações aplicadas.

## Dependências Essenciais
Veja o arquivo `requirements.txt` para a lista completa. Apenas bibliotecas essenciais para análise, IA e integração com repositórios são utilizadas.

## Observações
- Funcionalidades de commit, PR, build .NET, criação de épicos/features/tarefas e comparação de código foram removidas nesta versão simplificada.
- Recomenda-se executar as simplificações de forma incremental para garantir segurança e rastreabilidade.
