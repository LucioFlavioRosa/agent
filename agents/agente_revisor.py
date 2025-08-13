# Arquivo: agents/agente_revisor.py (VERSÃO FINAL AJUSTADA PARA DEPLOY)

import json # [NOVO] Importa a biblioteca JSON
from typing import Optional, Dict, Any
from tools import github_reader
from tools.requisicao_openai import executar_analise_llm 

modelo_llm = 'gpt-4.1'
max_tokens_saida = 6000

analises_validas = ["relatorio_padrao_desenvolvimento_codigo", "pentest", "seguranca", "terraform",
                     "refatoracao", "relatorio_teste_unitario", "escrever_testes",
                     "agrupamento_testes", "docstring", "agrupamento_design"]

def code_from_repo(repositorio: str,
                   tipo_analise: str,
                   nome_branch:  Optional[str] = None) -> Dict[str, str]:
    try:
        print('Iniciando a leitura do repositório: '+ repositorio)
        codigo_para_analise = github_reader.main(nome_repo=repositorio,
                                                 tipo_de_analise=tipo_analise,
                                                 nome_branch = nome_branch)
        return codigo_para_analise
    except Exception as e:
        raise RuntimeError(f"Falha ao ler o repositório: {e}") from e

def validation(tipo_analise: str,
               repositorio: Optional[str] = None,
               nome_branch: Optional[str] = None,
               codigo: Optional[str] = None) -> Any:
    if tipo_analise not in analises_validas:
        raise ValueError(f"Tipo de análise '{tipo_analise}' é inválido. Válidos: {analises_validas}")

    if repositorio is None and codigo is None:
        raise ValueError("Erro: É obrigatório fornecer 'repositorio' ou 'codigo'.")

    if codigo is None:
        codigo_para_analise = code_from_repo(tipo_analise=tipo_analise,
                                             repositorio=repositorio,
                                             nome_branch = nome_branch)
    else:
        codigo_para_analise = codigo
    
    return codigo_para_analise

def main(tipo_analise: str,
         repositorio: Optional[str] = None,
         nome_branch: Optional[str] = None,
         codigo: Optional[str] = None,
         instrucoes_extras: str = "",
         model_name: str = modelo_llm,
         max_token_out: int = max_tokens_saida) -> Dict[str, Any]:

    codigo_para_analise = validation(tipo_analise=tipo_analise,
                                     repositorio=repositorio,
                                     nome_branch=nome_branch,
                                     codigo=codigo)
                                     
    if not codigo_para_analise:
        # Se não houver código, retorna uma estrutura vazia, mas compatível
        return {"resultado": {"reposta_final": "{}"}}
    
    # [AJUSTE 1] Usa json.dumps para serializar o código de forma consistente se for um dicionário.
    # Se já for uma string, não faz nada.
    if isinstance(codigo_para_analise, dict):
        codigo_str = json.dumps(codigo_para_analise, indent=2)
    else:
        codigo_str = str(codigo_para_analise)

    resultado_da_ia = executar_analise_llm(
        tipo_analise=tipo_analise,
        codigo=codigo_str,
        analise_extra=instrucoes_extras,
        model_name=model_name,
        max_token_out=max_token_out
    )
    
    # [AJUSTE 2] A estrutura do retorno agora corresponde exatamente ao que o backend espera.
    return {
        "resultado": {
            "reposta_final": resultado_da_ia
        }
    }

