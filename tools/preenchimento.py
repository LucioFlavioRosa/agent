# Arquivo: tools/preenchimento.py (VERSÃO FINAL COM LÓGICA DE MERGE)

import json
from domain.interfaces.changeset_filler_interface import IChangesetFiller

class ChangesetFiller(IChangesetFiller):
    """
    Implementação que preenche os dados mesclando as informações do
    JSON agrupado com os detalhes completos do JSON inicial.
    """
    def main(self, json_agrupado: dict, json_inicial: dict) -> dict:
        print("\n" + "="*50)
        print("INICIANDO PROCESSO DE PREENCHIMENTO (ChangesetFiller)")
        print("="*50)

        if not isinstance(json_inicial, dict) or not json_inicial.get('conjunto_de_mudancas'):
            print("AVISO CRÍTICO: O JSON inicial (resultado_refatoracao) está vazio ou não contém 'conjunto_de_mudancas'.")
            return {}

        if not isinstance(json_agrupado, dict):
            print(f"AVISO CRÍTICO: O JSON agrupado não é um dicionário válido. Tipo recebido: {type(json_agrupado)}.")
            return {}

        mapa_de_mudancas_originais = {
            mudanca['caminho_do_arquivo']: mudanca
            for mudanca in json_inicial.get('conjunto_de_mudancas', [])
        }
        print(f"Mapa de dados originais criado com {len(mapa_de_mudancas_originais)} arquivos.")

        resultado_preenchido = {}
        
        for nome_do_grupo, dados_do_grupo in json_agrupado.items():
            if not isinstance(dados_do_grupo, dict) or 'conjunto_de_mudancas' not in dados_do_grupo:
                if nome_do_grupo == "resumo_geral":
                    resultado_preenchido[nome_do_grupo] = dados_do_grupo
                continue

            print(f"\n--- Processando grupo: '{nome_do_grupo}' ---")
            conjunto_do_grupo_leve = dados_do_grupo.get('conjunto_de_mudancas', [])
            conjunto_preenchido = []
            
            for mudanca_leve in conjunto_do_grupo_leve:
                caminho_do_arquivo = mudanca_leve.get('caminho_do_arquivo')
                if not caminho_do_arquivo:
                    continue
                
                if caminho_do_arquivo in mapa_de_mudancas_originais:
                    # 1. Começa com a mudança completa e detalhada do JSON inicial
                    mudanca_final = mapa_de_mudancas_originais[caminho_do_arquivo].copy()
                    
                    # 2. MUDANÇA CRÍTICA: Atualiza/mescla com os dados do JSON agrupado.
                    #    Isso garante que justificativas ou status do agrupamento sejam mantidos.
                    mudanca_final.update(mudanca_leve)

                    # 3. Garante que a chave "conteudo" exista (fallback para "codigo_novo")
                    if "conteudo" not in mudanca_final and "codigo_novo" in mudanca_final:
                        mudanca_final["conteudo"] = mudanca_final["codigo_novo"]

                    if mudanca_final.get("conteudo") is not None:
                        print(f"  [SUCESSO] Detalhes de '{caminho_do_arquivo}' mesclados e preenchidos.")
                        conjunto_preenchido.append(mudanca_final)
                    else:
                        print(f"  [AVISO] Detalhes de '{caminho_do_arquivo}' encontrados, mas sem conteúdo. Ignorando.")
                else:
                    print(f"  [ERRO] Detalhes para '{caminho_do_arquivo}' NÃO encontrados no JSON inicial. Ignorando.")

            if conjunto_preenchido:
                resultado_preenchido[nome_do_grupo] = {
                    **dados_do_grupo,
                    'conjunto_de_mudancas': conjunto_preenchido
                }
        
        print("\n" + "="*50)
        print("PROCESSO DE PREENCHIMENTO CONCLUÍDO")
        print("="*50)
        return resultado_preenchido
