# Arquivo: agents/agente_revisor.py (VERSÃO REATORADA)

from typing import Optional, Dict, Any
from tools import github_reader # Importa o leitor de código
from tools.requisicao_openai import executar_analise_llm

modelo_llm = 'gpt-4.1'
max_tokens_saida = 6000

analises_validas = ["design", "pentest", "seguranca", "terraform",
                    "refatoracao", "relatorio_teste_unitario", "escrever_testes",
                    "agrupamento_testes", "docstring", "agrupamento_design"]

# [NOVO] Função 1: Apenas para ler o código do repositório.
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
        # Re-levanta a exceção para que o orquestrador (FastAPI) possa tratá-la.
        raise RuntimeError(f"Falha ao ler o repositório '{repositorio}': {e}") from e

# [NOVO] Função 2: Apenas para gerar a análise, recebendo o código como parâmetro.
def gerar_relatorio_analise(
    tipo_analise: str,
    codigo_para_analise: Dict[str, str],
    instrucoes_extras: str = ""
) -> Dict[str, Any]:
    """
    Recebe um dicionário de código e executa a análise do LLM. Não lê o repositório.
    """
    if tipo_analise not in analises_validas:
        raise ValueError(f"Tipo de análise '{tipo_analise}' é inválido. Válidos: {analises_validas}")

    if not codigo_para_analise:
        return {'reposta_final': 'Nenhum código foi fornecido para análise.'}

    print(f"Iniciando análise de {tipo_analise} com o LLM...")
    resultado = executar_analise_llm(
        tipo_analise=tipo_analise,
        codigo=str(codigo_para_analise),  # Converte o dict de arquivos para uma string
        analise_extra=instrucoes_extras,
        model_name=modelo_llm,
        max_token_out=max_tokens_saida
    )
    return resultado

# [ALTERADO] A função 'main' original agora é usada principalmente pelo workflow pós-aprovação.
def main(tipo_analise: str,
         repositorio: Optional[str] = None,
         nome_branch: Optional[str] = None,
         codigo: Optional[str] = None,
         instrucoes_extras: str = "")-> Dict[str, Any]:
    """
    Função "tudo-em-um" que pode ser usada para análises diretas ou pelo workflow.
    """
    codigo_final = codigo
    if repositorio and not codigo:
        # Se um repositório for fornecido sem código, ele lê o repo.
        codigo_final_dict = ler_codigo_do_repositorio(repositorio, tipo_analise, nome_branch)
        codigo_final = str(codigo_final_dict)

    if not codigo_final:
        return {"tipo_analise": tipo_analise, "resultado": {'reposta_final': 'Não foi fornecido nenhum código para análise'}}

    resultado = gerar_relatorio_analise(tipo_analise, codigo_final, instrucoes_extras)
    return {"tipo_analise": tipo_analise, "resultado": resultado}
