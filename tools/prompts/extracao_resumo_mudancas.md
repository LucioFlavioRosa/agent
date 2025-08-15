# PROMPT: Extração da tabela com as mudanças

## O PAPEL E O OBJETIVO

- Você é vai extratir somente a tabela com as ações necessárias para melhorar o código
- Você receberá um relatório em formato markdown(.md)
- busque por algo parecido com ## Plano de Refatoração e extraia a tabela que tenha nessa seção
- a tabela irá conter nomes de arquivos e orientaçòes de mudanças.

## exemplo de busca que será a saída

## Plano de Refatoração
| Arquivo(s) a Modificar | Ação de Refatoração Recomendada |
|---|---|
| agents/agente_revisor.py | Expor função pública com nome alinhado ao cliente (executar_analise) ou atualizar chamadas; padronizar idioma e corrigir “conection”/“validation”/“main”; adicionar docstrings; substituir prints por logging; unificar tipo de entrada/retorno (padronizar para um objeto estruturado em vez de str(dict)). |
| agents/agente_revisor.py; tools/revisor_geral.py | Introduzir controle de orçamento de tokens: chunking do código por arquivo, sumarização incremental, limite de tamanho por arquivo e por total; rejeitar arquivos acima de um limiar configurável. |
| tools/github_reader.py | Remover dependência de google.colab.userdata; ler credenciais via variáveis de ambiente ou injeção de dependência; renomear “conection” para “connect”/“conectar”; remover import “re”; adicionar exclusões de diretórios (node_modules, .git, dist, vendor, build), filtro de binários e limite de tamanho por arquivo; implementar backoff/retries e tratamento específico de exceções da GitHub API; retornar iterador/gerador opcional para reduzir memória. |
| tools/revisor_geral.py | Substituir google.colab.userdata por configuração central (env/config file); alinhar mensagem de erro com a fonte real da chave; adicionar timeouts e retries na chamada à OpenAI; validar existência de prompts antes da execução; permitir modo fallback quando prompt não encontrado; parametrizar temperatura/modelo via config. |
| tools/prompts/* (novo) | Adicionar os arquivos de prompt exigidos por “carregar_prompt”; cobrir todos os tipos aceitos em analises_validas. |
