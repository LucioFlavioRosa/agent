import json
from typing import Optional, Dict, Any
from tools import github_reader
from tools import requisicao_openai 

# Valores padrão
modelo_llm = 'gpt-4.1'
max_tokens_saida = 10000

def _get_code(
    repositorio: str,
    nome_branch: Optional[str],
    tipo_analise: str
) -> Dict[str, str]:
    """Função interna e focada apenas em ler o código de um repositório."""
    try:
        print(f"Iniciando a leitura do repositório: {repositorio}, branch: {nome_branch}")
        # [CORREÇÃO] Garante que o nome do parâmetro 'tipo_analise' esteja correto
        codigo_para_analise = github_reader.main(
            nome_repo=repositorio,
            tipo_analise=tipo_analise,
            nome_branch=nome_branch
        )
        return codigo_para_analise
    except Exception as e:
        # Propaga o erro de forma clara
        raise RuntimeError(f"Falha ao ler o repositório: {e}") from e

def main(
    tipo_analise: str,
    repositorio: Optional[str] = None,
    nome_branch: Optional[str] = None,
    codigo: Optional[Any] = None,
    instrucoes_extras: str = "",
    usar_rag: bool = False,
    model_name: str = modelo_llm,
    max_token_out: int = max_tokens_saida
) -> Dict[str, Any]:
    """
    Função principal e única do agente. Orquestra a obtenção do código e a chamada para a IA.
    """
    codigo_para_analise = None
    
    # Passo 1: Determinar a fonte do código (repositório ou input direto)
    if codigo is None:
        if repositorio:
            codigo_para_analise = _get_code(
                repositorio=repositorio,
                nome_branch=nome_branch,
                tipo_analise=tipo_analise
            )
        else:
            raise ValueError("Erro: É obrigatório fornecer 'repositorio' ou 'codigo'.")
    else:
        codigo_para_analise = codigo
                                   
    if not codigo_para_analise:
        print(f"AVISO: Nenhum código encontrado ou fornecido para a análise '{tipo_analise}'.")
        # Retorna uma estrutura compatível indicando que não há nada a fazer
        return {"resultado": {"reposta_final": {"reposta_final": "{}"}}}
    
    # Passo 2: Serializar o código para a IA
    if isinstance(codigo_para_analise, dict):
        codigo_str = json.dumps(codigo_para_analise, indent=2, ensure_ascii=False)
    else:
        codigo_str = str(codigo_para_analise)

    # Passo 3: Chamar a IA com os dados corretos
    resultado_da_ia = requisicao_openai.executar_analise_llm(
        tipo_analise=tipo_analise,
        codigo=codigo_str,
        analise_extra=instrucoes_extras,
        usar_rag=usar_rag,
        model_name=model_name,
        max_token_out=max_token_out
    )
        
    # Passo 4: Retornar no formato esperado pelo backend
    return {
        "resultado": {
            "reposta_final": resultado_da_ia
        }
    }
