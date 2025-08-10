# Arquivo: agents/agente_revisor.py (VERSÃO CORRIGIDA)

from typing import Optional, Dict, Any
from tools import github_reader 
from tools.requisicao_openai import executar_analise_llm

modelo_llm = 'gpt-4.1'
max_tokens_saida = 6000

analises_validas = ["design", "pentest", "seguranca", "terraform",
                    "refatoracao", "relatorio_teste_unitario", "escrever_testes",
                    "agrupamento_testes", "docstring", "agrupamento_design"]

def ler_codigo_do_repositorio(repositorio: str, tipo_analise: str, nome_branch: Optional[str] = None) -> Dict[str, str]:
    """
    Responsável unicamente por ler os arquivos do repositório e retorná-los.
    """
    print(f"Iniciando a leitura do repositório: {repositorio} para análise de {tipo_analise}")
    try:
        codigo_para_analise = github_reader.main(
            nome_repo=repositorio,
            tipo_de_analise=tipo_analise,
            nome_branch=nome_branch
        )
        return codigo_para_analise
    except Exception as e:
        raise RuntimeError(f"Falha ao ler o repositório '{repositorio}': {e}") from e

# [ALTERADO] Esta função agora trata o caso de 'instrucoes_extras' ser None.
def gerar_relatorio_analise(
    tipo_analise: str,
    codigo_para_analise: Dict[str, str],
    instrucoes_extras: Optional[str] = None  # Aceita explicitamente None
) -> Dict[str, Any]:
    """
    Recebe um dicionário de código e executa a análise do LLM. Não lê o repositório.
    """
    if tipo_analise not in analises_validas:
        raise ValueError(f"Tipo de análise '{tipo_analise}' é inválido. Válidos: {analises_validas}")

    if not codigo_para_analise:
        return {'reposta_final': 'Nenhum código foi fornecido para análise.'}

    # [CORREÇÃO] Garante que 'instrucoes_extras' seja uma string vazia se for None.
    # Isso evita o erro .strip() em um objeto None.
    instrucoes_seguras = instrucoes_extras if instrucoes_extras is not None else ""

    print(f"Iniciando análise de {tipo_analise} com o LLM...")
    resultado = executar_analise_llm(
        tipo_analise=tipo_analise,
        codigo=str(codigo_para_analise),
        analise_extra=instrucoes_seguras,  # Usa a variável segura
        model_name=modelo_llm,
        max_token_out=max_tokens_saida
    )
    return resultado

# A função 'main' permanece a mesma.
def main(tipo_analise: str,
         repositorio: Optional[str] = None,
         nome_branch: Optional[str] = None,
         codigo: Optional[str] = None,
         instrucoes_extras: str = "")-> Dict[str, Any]:
    codigo_final = codigo
    if repositorio and not codigo:
        codigo_final_dict = ler_codigo_do_repositorio(repositorio, tipo_analise, nome_branch)
        codigo_final = str(codigo_final_dict)

    if not codigo_final:
        return {"tipo_analise": tipo_analise, "resultado": {'reposta_final': 'Não foi fornecido nenhum código para análise'}}

    # Passa as instruções extras para a função de gerar relatório
    resultado = gerar_relatorio_analise(tipo_analise, codigo_final, instrucoes_extras)
    return {"tipo_analise": tipo_analise, "resultado": resultado}
