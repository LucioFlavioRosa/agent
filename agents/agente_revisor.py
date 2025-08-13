import json
from typing import Optional, Dict, Any
from tools import github_reader
from tools.requisicao_openai import executar_analise_llm 

modelo_llm = 'gpt-4.1'
max_tokens_saida = 10000

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

def validation(repositorio: Optional[str] = None,
               nome_branch: Optional[str] = None,
               codigo: Optional[str] = None,
               tipo_analise: Optional[str] = None) -> Any:
    
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
         usar_rag: bool = False,
         model_name: str = modelo_llm,
         max_token_out: int = max_tokens_saida) -> Dict[str, Any]:

    # A validação de tipo_analise não é mais necessária aqui.
    codigo_para_analise = validation(
        repositorio=repositorio,
        nome_branch=nome_branch,
        codigo=codigo,
        tipo_analise=tipo_analise
    )
                                   
    if not codigo_para_analise:
        return {"resultado": {"reposta_final": { "reposta_final": "{}" }}}
    
    if isinstance(codigo_para_analise, dict):
        codigo_str = json.dumps(codigo_para_analise, indent=2)
    else:
        codigo_str = str(codigo_para_analise)

    resultado_da_ia = executar_analise_llm(
        tipo_analise=tipo_analise,
        codigo=codigo_str,
        analise_extra=instrucoes_extras,
        usar_rag=usar_rag,
        model_name=model_name,
        max_token_out=max_token_out
    )
        
    return {
        "resultado": {
            "reposta_final": resultado_da_ia
        }
    }



